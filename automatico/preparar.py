"""MaesTrials — B2: prepara las versiones del día (lo lanza GitHub Actions; también vale en el PC).

Uso (desde la raíz del proyecto):
  python -I -X utf8 automatico/preparar.py                 # prepara lo que falte hasta tener LISTAS versiones sin publicar
  python -I -X utf8 automatico/preparar.py --simular       # solo dice qué prepararía
  python -I -X utf8 automatico/preparar.py <media_id> ...  # prepara esos vídeos concretos

Elige ganadores por retención (la prioridad de Jose) que no tengan ya una versión esperando y que
cumplan la regla de 4 días antes del último hueco de publicación del día.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase3"))
import variar  # noqa: E402
import cuenta  # noqa: E402

GANADORES = cuenta.DATOS / "ganadores.json"
MANUALES = cuenta.DATOS / "manuales.json"     # ganadores que Jose añade a mano desde el panel
AJUSTES = json.loads((cuenta.DATOS / "ajustes.json").read_text(encoding="utf-8"))
LISTAS = AJUSTES["maximo_dia"]   # versiones preparadas y sin publicar que queremos tener (= trials al día)
HORA_PREPARAR_NY = 6             # cron-job.org lanza preparar a las 6:00 NY
# el vídeo tiene que poder salir antes del último hueco del día (Jose: 19 - 6 = 13 h)
HORIZONTE_H = max(AJUSTES["huecos_ny"]) - HORA_PREPARAR_NY


def videos_ganadores() -> list[dict]:
    """Ganadores automáticos (fase2/ganadores.py) + los añadidos a mano, sin repetir."""
    automaticos = [v for v in json.loads(GANADORES.read_text(encoding="utf-8"))["videos"] if v["ganador"]]
    vistos = {i for v in automaticos for i in v["ids"]}
    manuales = json.loads(MANUALES.read_text(encoding="utf-8")) if MANUALES.exists() else []
    return automaticos + [m for m in manuales if not set(m["ids"]) & vistos]


def pendientes() -> list[dict]:
    publicados = {p["archivo"] for p in variar.leer_registro()}
    return [f for f in variar.todas_las_fichas() if f["archivo"] not in publicados]


def ultima_publicacion(video: dict, registro: list[dict]) -> datetime:
    fechas = [datetime.fromisoformat(video["ultima_publicacion"])]
    fechas += [datetime.fromisoformat(p["publicado_en"]) for p in registro if p["origen"] in video["ids"]]
    return max(fechas)


def elegir(ahora: datetime) -> list[dict]:
    videos = videos_ganadores()
    registro = variar.leer_registro()
    en_cola = {f["origen"] for f in pendientes()}
    limite = ahora + timedelta(hours=HORIZONTE_H) - timedelta(days=variar.DIAS_MINIMOS)
    aptos = [v for v in videos
             if not set(v["ids"]) & en_cola and ultima_publicacion(v, registro) <= limite]
    return sorted(aptos, key=lambda v: v["retencion"] or 0, reverse=True)


def main() -> None:
    argumentos = sys.argv[1:]
    simular = "--simular" in argumentos
    pedidos = [a for a in argumentos if a != "--simular"]
    if any(not a.isdigit() for a in pedidos):
        raise SystemExit("Los ids de vídeo solo llevan números")
    if pedidos:
        objetivo = pedidos
    else:
        hueco = max(0, LISTAS - len(pendientes()))
        objetivo = [v["mejor_id"] for v in elegir(datetime.now(timezone.utc))[:hueco]]
    print(f"En cola sin publicar: {len(pendientes())} | a preparar: {objetivo or 'ninguno'}")
    if simular or not objetivo:
        return
    fallos = []
    for media_id in objetivo:
        try:
            variar.preparar(media_id)
        except (SystemExit, Exception) as e:  # noqa: BLE001 — un vídeo que falla no para a los demás
            print(f"ERROR preparando {media_id}: {e}")
            fallos.append(media_id)
    if fallos:
        raise SystemExit(f"Fallaron {len(fallos)} de {len(objetivo)}: {fallos}")


if __name__ == "__main__":
    main()
