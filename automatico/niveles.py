"""MaesTrials — vídeos por nivel (cualificado / relleno) y huecos con nivel. Solo si la cuenta tiene seleccion.json.

seleccion.json (lo decide Jose, a mano):
  {"cualificado": [ids], "relleno": [ids en orden de preferencia], "mismo_video": [[ids del mismo vídeo], ...]}
  En cada lista va UN id por vídeo: el que se monta (tiene vídeo en Instagram o archivo en originales/).
ajustes.json: "huecos": [{"hora": 9, "nivel": "cualificado"}, ...] y "cuotas": {"cualificado": 2, "relleno": 2}.
Sin seleccion.json (la cuenta de Jose) todo sigue como antes: hermanos(id) = {id} y ACTIVO = False.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import cuenta

ARCHIVO = cuenta.DATOS / "seleccion.json"
ACTIVO = ARCHIVO.exists()
_SELECCION = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ACTIVO else {}
NIVELES = ("cualificado", "relleno")
RETRASO_MAX_H = 2   # si el autopilot llega más tarde, el hueco no se recupera (fallo del 11-nov: 4 trials en 3 h)


@dataclass(frozen=True)
class Hueco:
    publicar: bool
    motivo: str
    nivel: str | None = None


def hermanos(media_id: str) -> set[str]:
    """Todos los ids que son el mismo vídeo (para la regla de 4 días)."""
    return next((set(g) for g in _SELECCION.get("mismo_video", []) if media_id in g), {media_id})


def nivel_de(media_id: str) -> str | None:
    grupo = hermanos(media_id)
    return next((n for n in NIVELES if grupo & set(_SELECCION.get(n, []))), None)


def orden_de(media_id: str) -> int:
    """Puesto del vídeo dentro de su lista en seleccion.json (0 = el primero); los que no están, al final."""
    grupo = hermanos(media_id)
    for nivel in NIVELES:
        for puesto, otro in enumerate(_SELECCION.get(nivel, [])):
            if otro in grupo:
                return puesto
    return 10**6


def videos_elegibles(todos: list[dict]) -> list[dict]:
    """Un vídeo por cada id de la selección, con los ids y la última publicación de todo su grupo."""
    elegibles = []
    for nivel in NIVELES:
        for orden, media_id in enumerate(_SELECCION.get(nivel, [])):
            grupo = hermanos(media_id)
            del_grupo = [v for v in todos if grupo & set(v["ids"])]
            base = next((v for v in del_grupo if media_id in v["ids"]), None)
            if base is None:
                print(f"  AVISO: {media_id} está en seleccion.json pero no en ganadores.json; se salta")
                continue
            ids = sorted(grupo.union(*(v["ids"] for v in del_grupo)))
            ultima = max(v["ultima_publicacion"] for v in del_grupo)
            elegibles.append({**base, "mejor_id": media_id, "ids": ids, "ultima_publicacion": ultima,
                              "nivel": nivel, "orden": orden})
    return elegibles


def hueco_actual(ahora: datetime, ajustes: dict, registro: list[dict]) -> Hueco:
    zona = ZoneInfo(ajustes["zona"])
    local = ahora.astimezone(zona)
    if not ajustes["autopilot"]:
        return Hueco(False, "autopilot apagado")
    pasados = [h for h in ajustes["huecos"] if h["hora"] <= local.hour]
    if not pasados:
        return Hueco(False, f"aún no toca ({local:%H:%M}; primer hueco a las {ajustes['huecos'][0]['hora']}:00)")
    hueco = pasados[-1]
    inicio = local.replace(hour=hueco["hora"], minute=0, second=0, microsecond=0)
    if local - inicio >= timedelta(hours=RETRASO_MAX_H):
        return Hueco(False, f"el hueco de las {hueco['hora']}:00 ya pasó hace más de {RETRASO_MAX_H} h; no se recupera")
    if any(datetime.fromisoformat(p["publicado_en"]).astimezone(zona) >= inicio for p in registro):
        return Hueco(False, f"hueco de las {hueco['hora']}:00 ({hueco['nivel']}) ya cubierto")
    return Hueco(True, f"toca: hueco de las {hueco['hora']}:00 ({hueco['nivel']}, {local:%H:%M} hora local)",
                 hueco["nivel"])
