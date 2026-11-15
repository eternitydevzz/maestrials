"""MaesTrials — B3: autopilot. Publica la siguiente versión de la cola en los huecos fijos (hora de NY).

Uso (desde la raíz del proyecto):
  python -I -X utf8 automatico/publicar.py                       # decide y, si toca, publica
  python -I -X utf8 automatico/publicar.py --simular             # solo dice qué haría
  python -I -X utf8 automatico/publicar.py --simular --ahora 2026-11-10T10:07-05:00

Reglas (decisiones de Jose): interruptor en datos/ajustes.json; solo entre 9:00 y 22:00 NY; un trial por hueco
(10, 14 y 19 NY), máx. 3 al día; 4 días entre publicaciones del mismo vídeo; 45 min entre subidas; primero
la versión cuyo vídeo tiene más retención. La regla "1 feed por cada 6 trials" solo avisa.
"""
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase3"))
sys.path.insert(0, str(RAIZ / "automatico"))
import preparar  # noqa: E402
import variar  # noqa: E402
import cuenta  # noqa: E402
import niveles  # noqa: E402

AJUSTES = cuenta.DATOS / "ajustes.json"
TRIALS_POR_FEED = 6
DIAS_AVISO_FEED = 7


@dataclass(frozen=True)
class Decision:
    publicar: bool
    motivo: str
    nivel: str | None = None   # solo en cuentas con niveles (Cristian)


def decidir(ahora: datetime, ajustes: dict, registro: list[dict]) -> Decision:
    if niveles.ACTIVO:   # huecos con nivel y hora local de la cuenta (Cristian: Madrid)
        hueco = niveles.hueco_actual(ahora, ajustes, registro)
        return Decision(hueco.publicar, hueco.motivo, hueco.nivel)
    zona = ZoneInfo(ajustes["zona"])
    ny = ahora.astimezone(zona)
    if not ajustes["autopilot"]:
        return Decision(False, "autopilot apagado")
    inicio, fin = ajustes["ventana_ny"]
    if not inicio <= ny.hour < fin:
        return Decision(False, f"fuera de la ventana ({ny:%H:%M} NY)")
    pasados = [h for h in ajustes["huecos_ny"] if h <= ny.hour]
    if not pasados:
        return Decision(False, f"aún no toca ({ny:%H:%M} NY; primer hueco a las {ajustes['huecos_ny'][0]}:00)")
    hoy = sum(1 for p in registro if datetime.fromisoformat(p["publicado_en"]).astimezone(zona).date() == ny.date())
    if hoy >= min(len(pasados), ajustes["maximo_dia"]):
        return Decision(False, f"hueco de las {pasados[-1]}:00 NY ya cubierto ({hoy} publicadas hoy)")
    return Decision(True, f"toca: hueco de las {pasados[-1]}:00 NY ({hoy} publicadas hoy, {ny:%H:%M} NY)")


def cola_por_retencion() -> list[dict]:
    if niveles.ACTIVO:   # con niveles: el orden de seleccion.json (Jose, 15-nov: primero los de más visitas)
        return sorted(preparar.pendientes(), key=lambda f: niveles.orden_de(f["origen"]))
    retencion = {i: v.get("retencion") or 0 for v in preparar.videos_ganadores() for i in v["ids"]}
    return sorted(preparar.pendientes(), key=lambda f: retencion.get(f["origen"], 0), reverse=True)


def avisar_feed(registro: list[dict], ahora: datetime) -> None:
    """Regla de TrialPilot (1 reel de feed por cada 6 trials en 7 días). Decisión de Jose: solo aviso."""
    desde = ahora - timedelta(days=DIAS_AVISO_FEED)
    trials = sum(1 for p in registro if datetime.fromisoformat(p["publicado_en"]) >= desde)
    try:
        env = variar.leer_env()
        media = variar.api("GET", f"{env['IG_USER_ID']}/media",
                           {"fields": "media_product_type,is_shared_to_feed,timestamp", "limit": "50"})["data"]
    except (SystemExit, Exception) as e:  # noqa: BLE001 — es solo un aviso
        print(f"  (no se pudo comprobar la regla del feed: {e})")
        return
    feed = sum(1 for m in media if m.get("media_product_type") == "REELS" and m.get("is_shared_to_feed")
               and datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z") >= desde)
    if trials + 1 > TRIALS_POR_FEED * feed:
        print(f"  AVISO feed: {feed} reels de feed y {trials} trials en {DIAS_AVISO_FEED} días "
              f"(la regla pide 1 de feed por cada {TRIALS_POR_FEED}). Se publica igual (decisión de Jose).")


def main() -> None:
    argumentos = sys.argv[1:]
    simular = "--simular" in argumentos
    ahora = datetime.now(timezone.utc)
    if "--ahora" in argumentos:
        ahora = datetime.fromisoformat(argumentos[argumentos.index("--ahora") + 1])
    ajustes = json.loads(AJUSTES.read_text(encoding="utf-8"))
    registro = variar.leer_registro()
    decision = decidir(ahora, ajustes, registro)
    print(decision.motivo)
    if not decision.publicar:
        return
    cola = cola_por_retencion()
    if decision.nivel:
        cola = [f for f in cola if niveles.nivel_de(f["origen"]) == decision.nivel]
        if not cola and decision.nivel == "relleno":   # el relleno es opcional: sin email de fallo
            print("No hay relleno en cola: este hueco se salta")
            return
    if not cola:   # falla a propósito: la ejecución sale en rojo y GitHub avisa por email
        raise SystemExit("FALLO: tocaba publicar y no hay versiones en cola (preparar las rellena cada día a las 6:00 NY)")
    for ficha in cola:
        try:   # comprobaciones previas: si fallan, se prueba la siguiente de la cola
            variar.comprobar_reglas(ficha["origen"])
            variar.comprobar_url(variar.URL_PUBLICA + ficha["archivo"])
        except SystemExit as e:
            print(f"  {ficha['archivo']}: ahora no ({e})")
            continue
        if simular:
            print(f"Publicaría: {ficha['archivo']} · gancho «{' '.join(ficha['gancho'])}»")
            return
        avisar_feed(registro, ahora)
        variar.publicar(ficha["origen"], ficha["archivo"])   # si falla aquí, se para (nada de reintentos a ciegas)
        return
    if decision.nivel == "relleno":
        print("Ningún relleno cumple ahora las reglas: este hueco se salta")
        return
    raise SystemExit("FALLO: tocaba publicar y ninguna versión de la cola cumple ahora las reglas")


if __name__ == "__main__":
    main()
