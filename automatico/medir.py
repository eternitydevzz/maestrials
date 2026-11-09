"""MaesTrials — B1: guarda las métricas de cada trial a las 24 h (lo lanza GitHub Actions; también vale en el PC).

Uso (desde la raíz del proyecto):
  python -I -X utf8 automatico/medir.py

- Si un trial tiene 24 h o más y aún no tiene foto de 24 h, la guarda en `metricas_24h` con las horas exactas.
- A los trials de los últimos DIAS_SEGUIMIENTO días les actualiza `metricas_ultimas`.
Solo escribe datos/publicaciones.json si algo cambió. Los tokens vienen del entorno y nunca se imprimen.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))
from _panel.config import entorno  # noqa: E402
from _panel.instagram import ErrorInstagram, en_paralelo, metricas  # noqa: E402

REGISTRO = RAIZ / "datos" / "publicaciones.json"
HORAS_FOTO = 24
DIAS_SEGUIMIENTO = 7


def horas_de_vida(publicacion: dict, ahora: datetime) -> float:
    return (ahora - datetime.fromisoformat(publicacion["publicado_en"])).total_seconds() / 3600


def actualizar(publicacion: dict, valores: dict | None, ahora: datetime) -> dict:
    """Devuelve una copia nueva de la publicación con las métricas puestas (no toca la original)."""
    if valores is None:
        return publicacion
    horas = round(horas_de_vida(publicacion, ahora), 1)
    nueva = {**publicacion, "metricas_ultimas": {**valores, "horas": horas, "en": ahora.isoformat()}}
    if horas >= HORAS_FOTO and "metricas_24h" not in publicacion:
        nueva["metricas_24h"] = {**valores, "horas": horas, "en": ahora.isoformat()}
    return nueva


def main() -> None:
    env = entorno()
    faltan = [k for k in ("IG_TOKEN", "GRAPH_BASE") if not env.get(k)]
    if faltan:
        raise SystemExit(f"Faltan variables: {', '.join(faltan)}")
    registro = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else []
    ahora = datetime.now(timezone.utc)
    a_medir = [p["publicacion"] for p in registro
               if horas_de_vida(p, ahora) <= DIAS_SEGUIMIENTO * 24 or "metricas_24h" not in p]

    def medir_una(media_id: str) -> dict | None:
        try:
            return metricas(env, media_id)
        except ErrorInstagram as e:
            print(f"  {media_id}: no se pudo medir ({e})")
            return None

    valores = en_paralelo(medir_una, a_medir) if a_medir else {}
    nuevo = [actualizar(p, valores.get(p["publicacion"]), ahora) for p in registro]
    for antes, despues in zip(registro, nuevo):
        if "metricas_24h" in despues and "metricas_24h" not in antes:
            m = despues["metricas_24h"]
            print(f"FOTO 24 h: {despues['publicacion']} ({despues['origen']}) → {m.get('views', 0):,} visitas a las {m['horas']} h")
    if nuevo != registro:
        REGISTRO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Medidos {len(valores)} de {len(registro)} trials · {ahora:%Y-%m-%d %H:%M} UTC")


if __name__ == "__main__":
    main()
