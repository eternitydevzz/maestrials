"""Datos de las pantallas Ganadores y Resultados.

De dónde salen: hoy, de los archivos de trabajo/ del PC (AlmacenLocal). En Vercel saldrán de Postgres
con la misma forma; las funciones `ganadores` y `resultados` no cambian.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import RAIZ
from .instagram import portadas

TRABAJO = RAIZ / "trabajo"
DIAS_MINIMOS = 4                                   # decisión de Jose
CAMBIOS_FASE1 = {"velocidad": 1.05, "inicio_s": 0.0}   # la versión de la bolsa (fase1/pasada.py)
HORAS_RESULTADO = 24


def _leer(ruta: Path, defecto: object) -> object:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def _fecha(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


class AlmacenLocal:
    def videos(self) -> tuple[float | None, list[dict]]:
        """Todos los vídeos de fase2/ganadores.py + los ganadores añadidos a mano (sin repetir)."""
        datos = _leer(RAIZ / "datos" / "ganadores.json", {"corte_percentil": None, "videos": []})
        manuales = _leer(RAIZ / "datos" / "manuales.json", [])
        ganadores_auto = {i for v in datos["videos"] if v["ganador"] for i in v["ids"]}
        return datos["corte_percentil"], datos["videos"] + [m for m in manuales if not set(m["ids"]) & ganadores_auto]

    def publicaciones(self) -> list[dict]:
        registro = list(_leer(RAIZ / "datos" / "publicaciones.json", []))   # registro único (Fase 1 incluida)
        return sorted(registro, key=lambda r: r["publicado_en"], reverse=True)

    def ficha(self, origen: str, archivo: str) -> dict | None:
        for ruta in (RAIZ / "datos" / "versiones").glob("*.json"):
            datos = _leer(ruta, {})
            if datos.get("origen") == origen and datos.get("archivo") == archivo:
                return datos
        return None


def almacen(env: dict[str, str]) -> AlmacenLocal:
    return AlmacenLocal()


def ganadores(env: dict[str, str], alm: AlmacenLocal) -> dict:
    corte, videos = alm.videos()
    propias = alm.publicaciones()
    ahora = datetime.now(timezone.utc)
    lista = []
    for v in (x for x in videos if x["ganador"]):
        fechas = [v["ultima_publicacion"]] + [p["publicado_en"] for p in propias if p["origen"] in v["ids"]]
        ultima = max(fechas, key=_fecha)
        vuelve = _fecha(ultima) + timedelta(days=DIAS_MINIMOS)
        lista.append({"id": v["mejor_id"], "titulo": v["pie"], "visitas": v["mejores_visitas"],
                      "retencion": v["retencion"], "duracion_s": v["duracion_s"],
                      "publicaciones": v["publicaciones"] + sum(1 for p in propias if p["origen"] in v["ids"]),
                      "ultima": ultima, "disponible_desde": vuelve.isoformat(), "disponible": vuelve <= ahora,
                      "manual": bool(v.get("manual"))})
    extra = portadas(env, [g["id"] for g in lista]) if lista else {}
    for g in lista:
        g.update(extra.get(g["id"], {}))
    return {"corte": corte, "dias_minimos": DIAS_MINIMOS, "ganadores": lista}


def resultados(env: dict[str, str], alm: AlmacenLocal) -> dict:
    _, videos = alm.videos()
    por_id = {i: v for v in videos for i in v["ids"]}
    ahora = datetime.now(timezone.utc)
    lista = []
    for p in alm.publicaciones():
        # Métricas que guarda GitHub Actions cada hora: la foto de 24 h si ya existe; si no, la última.
        m = p.get("metricas_24h") or p.get("metricas_ultimas") or {}
        video = por_id.get(p["origen"], {})
        ficha = alm.ficha(p["origen"], p["archivo"]) or {}
        cambios = ficha.get("cambios") or CAMBIOS_FASE1
        duracion = video.get("duracion_s")
        duracion_version = (duracion - cambios["inicio_s"]) / cambios["velocidad"] if duracion else None
        medio_s = (m.get("ig_reels_avg_watch_time") or 0) / 1000
        horas = (ahora - _fecha(p["publicado_en"])).total_seconds() / 3600
        lista.append({"id": p["publicacion"], "origen": p["origen"], "titulo": video.get("pie", ""),
                      "gancho": " ".join(ficha.get("gancho", [])), "publicado_en": p["publicado_en"],
                      "horas": round(horas, 1), "cumplio_24h": horas >= HORAS_RESULTADO,
                      "foto_24h": "metricas_24h" in p, "medido_en": m.get("en"), "horas_medida": m.get("horas"),
                      "visitas": m.get("views", 0), "alcance": m.get("reach", 0), "likes": m.get("likes", 0),
                      "comentarios": m.get("comments", 0), "compartidos": m.get("shares", 0),
                      "guardados": m.get("saved", 0), "tiempo_medio_s": round(medio_s, 1),
                      "retencion": round(medio_s / duracion_version, 3) if duracion_version and medio_s else None})
    extra = portadas(env, [r["id"] for r in lista]) if lista else {}
    for r in lista:
        r.update(extra.get(r["id"], {}))
    return {"horas_resultado": HORAS_RESULTADO, "publicaciones": lista}
