"""Lecturas de la API de Instagram (Graph). El token nunca sale en errores ni respuestas."""
import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

METRICAS = "views,reach,likes,comments,shares,saved,ig_reels_avg_watch_time"
LLAMADAS_A_LA_VEZ = 8
T = TypeVar("T")


class ErrorInstagram(Exception):
    pass


def pedir(env: dict[str, str], ruta: str, params: dict[str, str]) -> dict:
    consulta = urllib.parse.urlencode({**params, "access_token": env["IG_TOKEN"]})
    try:
        with urllib.request.urlopen(f"{env['GRAPH_BASE']}/{ruta}?{consulta}", timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error = json.loads(e.read().decode("utf-8") or "{}").get("error", {})
        raise ErrorInstagram(f"Instagram ({error.get('code')}): {error.get('message')}") from None
    except urllib.error.URLError as e:
        raise ErrorInstagram(f"Sin conexión con Instagram: {e.reason}") from None


def en_paralelo(funcion: Callable[[str], T], ids: list[str]) -> dict[str, T]:
    """Una llamada por reel, varias a la vez (la consulta `?ids=` está retirada desde la v26 de la API)."""
    with ThreadPoolExecutor(max_workers=LLAMADAS_A_LA_VEZ) as grupo:
        return dict(zip(ids, grupo.map(funcion, ids)))


def portadas(env: dict[str, str], ids: list[str]) -> dict[str, dict[str, str]]:
    """Miniatura y enlace de cada reel (las URLs de miniatura caducan: se piden cada vez)."""
    def una(media_id: str) -> dict[str, str]:
        d = pedir(env, media_id, {"fields": "thumbnail_url,permalink"})
        return {"miniatura": d.get("thumbnail_url", ""), "enlace": d.get("permalink", "")}
    return en_paralelo(una, ids)


def metricas(env: dict[str, str], media_id: str) -> dict[str, float]:
    datos = pedir(env, f"{media_id}/insights", {"metric": METRICAS}).get("data", [])
    return {d["name"]: (d.get("values") or [{}])[0].get("value") or 0 for d in datos}
