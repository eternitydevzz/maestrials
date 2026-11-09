"""MaesTrials — Fase 2: detector de reels ganadores.

Uso (desde la raíz del proyecto):
  python -I -X utf8 fase2/ganadores.py

Regla (PLAN.md): un VÍDEO gana si su mejor publicación (feed o trial) está en el
top 20 % por visitas (percentil 80) o supera UMBRAL_FIJO. Solo cuentan publicaciones
de los últimos DIAS_CANDIDATOS días y con al menos HORAS_MINIMAS de vida.
Las publicaciones del mismo vídeo se agrupan SOLO si sus fotogramas de los segundos 3 y 8
se parecen (huella dHash, distancia media <= UMBRAL_HUELLA).
- La portada NO sirve: Jose usa portadas distintas para el mismo vídeo (medido el 9-nov-2026).
- El pie NO sirve: pies genéricos ("Comenta CLASE…") juntaban vídeos distintos (corregido el 9-nov-2026).
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRABAJO = RAIZ / "trabajo"
SALIDA = RAIZ / "datos" / "ganadores.json"   # en el repo: lo usa GitHub Actions para preparar versiones

PERCENTIL = 80
UMBRAL_FIJO: int | None = None   # p. ej. 10_000 para activarlo
DIAS_CANDIDATOS = 180
HORAS_MINIMAS = 48
LETRAS_CLAVE = 45                # cuántas letras del pie forman la clave del vídeo
SEGUNDOS_HUELLA = (3, 8)         # fotogramas que forman la huella del vídeo
UMBRAL_HUELLA = 8                # distancia media (0-64) para decir "mismo vídeo"


@dataclass(frozen=True)
class Publicacion:
    id: str
    fecha: str
    momento: str                  # fecha y hora completas (ISO, UTC) de Instagram
    en_feed: bool
    visitas: int
    comentarios: int
    pie: str
    enlace: str
    huella: tuple[int, ...] | None
    tiempo_medio_s: float | None  # tiempo medio visto (ig_reels_avg_watch_time)
    duracion_s: float | None


@dataclass(frozen=True)
class Video:
    clave: str
    mejor_id: str
    mejor_enlace: str
    mejores_visitas: int
    comentarios_mejor: int
    publicaciones: int
    alguna_en_feed: bool
    pie: str
    ganador: bool
    ids: tuple[str, ...]          # todas las publicaciones de este vídeo
    ultima_publicacion: str       # ISO, UTC
    duracion_s: float | None
    retencion: float | None       # tiempo medio visto / duración, de la mejor publicación


def leer_env() -> dict[str, str]:
    datos: dict[str, str] = {}
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.startswith("#"):
            clave, valor = linea.split("=", 1)
            datos[clave.strip()] = valor.strip()
    return datos


def pedir(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error = json.loads(e.read().decode("utf-8")).get("error", {})
        raise SystemExit(f"ERROR de Instagram ({error.get('code')}): {error.get('message')}")


def listar_reels(env: dict[str, str]) -> list[dict]:
    campos = "id,media_product_type,is_shared_to_feed,timestamp,permalink,comments_count,caption,media_url"
    params = urllib.parse.urlencode({"fields": campos, "limit": 100, "access_token": env["IG_TOKEN"]})
    url: str | None = f"{env['GRAPH_BASE']}/{env['IG_USER_ID']}/media?{params}"
    todos: list[dict] = []
    while url:
        resp = pedir(url)
        todos.extend(resp.get("data", []))
        url = resp.get("paging", {}).get("next")
    return [m for m in todos if m.get("media_product_type") == "REELS"]


def metricas_de(env: dict[str, str], media_id: str) -> tuple[int, float | None]:
    """Visitas y tiempo medio visto (en segundos) de una publicación."""
    params = urllib.parse.urlencode({"metric": "views,ig_reels_avg_watch_time", "access_token": env["IG_TOKEN"]})
    resp = pedir(f"{env['GRAPH_BASE']}/{media_id}/insights?{params}")
    valores = {d["name"]: (d.get("values") or [{}])[0].get("value") for d in resp.get("data", [])}
    medio_ms = valores.get("ig_reels_avg_watch_time")
    return int(valores.get("views") or 0), (medio_ms / 1000 if medio_ms else None)


def duracion_de(url: str | None) -> float | None:
    if not url:
        return None
    salida = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", url],
                            capture_output=True, text=True, check=False).stdout.strip()
    try:
        return round(float(salida), 1)
    except ValueError:
        return None


def dhash_fotograma(url: str, segundo: int) -> int | None:
    """Huella de 64 bits de un fotograma: cada bit dice si un píxel es más claro que el de al lado."""
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(segundo), "-i", url, "-frames:v", "1",
         "-vf", "scale=9:8,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=False).stdout
    if len(crudo) != 72:
        return None
    return sum(1 << i for i in range(64) if crudo[(i // 8) * 9 + i % 8] > crudo[(i // 8) * 9 + i % 8 + 1])


def huella_de(url: str | None) -> tuple[int, ...] | None:
    if not url:
        return None
    partes = [dhash_fotograma(url, s) for s in SEGUNDOS_HUELLA]
    return None if None in partes else tuple(partes)  # type: ignore[arg-type]


def distancia(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b)) / len(a)


def publicados_por_maestrials() -> set[str]:
    """Trials publicados por MaesTrials: no son reels de Jose y no cuentan para elegir ganadores."""
    registro = RAIZ / "datos" / "publicaciones.json"   # registro único (Fase 1 incluida)
    if not registro.exists():
        return set()
    return {p["publicacion"] for p in json.loads(registro.read_text(encoding="utf-8"))}


def clave_del_video(pie: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", pie).encode("ascii", "ignore").decode()
    solo_letras = re.sub(r"[^a-z0-9]", "", sin_tildes.lower())
    return solo_letras[:LETRAS_CLAVE] or "sin-pie"


def candidatas(env: dict[str, str]) -> list[Publicacion]:
    ahora = datetime.now(timezone.utc)
    desde, hasta = ahora - timedelta(days=DIAS_CANDIDATOS), ahora - timedelta(hours=HORAS_MINIMAS)
    excluir = publicados_por_maestrials()
    lista: list[Publicacion] = []
    for m in listar_reels(env):
        fecha = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if m["id"] in excluir or not (desde <= fecha <= hasta):
            continue
        visitas, tiempo_medio_s = metricas_de(env, m["id"])
        lista.append(Publicacion(
            id=m["id"], fecha=m["timestamp"][:10], momento=fecha.astimezone(timezone.utc).isoformat(),
            en_feed=bool(m.get("is_shared_to_feed")), visitas=visitas,
            comentarios=int(m.get("comments_count") or 0),
            pie=(m.get("caption") or "").replace("\n", " ")[:80], enlace=m["permalink"],
            huella=huella_de(m.get("media_url")), tiempo_medio_s=tiempo_medio_s,
            duracion_s=duracion_de(m.get("media_url"))))
    return lista


def mismo_video(a: Publicacion, b: Publicacion) -> bool:
    """Sin huella (vídeo que no se pudo leer) nunca se junta con otro: mejor separado que mal unido."""
    return a.huella is not None and b.huella is not None and distancia(a.huella, b.huella) <= UMBRAL_HUELLA


def agrupar(pubs: list[Publicacion]) -> dict[str, list[Publicacion]]:
    """Unión de conjuntos: si A se parece a B y B a C, los tres son el mismo vídeo."""
    jefe = list(range(len(pubs)))

    def raiz(i: int) -> int:
        while jefe[i] != i:
            jefe[i] = jefe[jefe[i]]
            i = jefe[i]
        return i

    for i in range(len(pubs)):
        for j in range(i + 1, len(pubs)):
            if mismo_video(pubs[i], pubs[j]):
                jefe[raiz(i)] = raiz(j)
    grupos: dict[str, list[Publicacion]] = {}
    for i, p in enumerate(pubs):
        grupos.setdefault(str(raiz(i)), []).append(p)
    # Nombre del grupo = id de su mejor publicación (único). Con el pie se pisaban grupos
    # distintos que empiezan igual (bug encontrado el 9-nov-2026 con "Comenta N8N").
    return {max(v, key=lambda p: p.visitas).id: v for v in grupos.values()}


def decidir(grupos: dict[str, list[Publicacion]]) -> tuple[list[Video], float]:
    mejores = {k: max(v, key=lambda p: p.visitas) for k, v in grupos.items()}
    visitas = [p.visitas for p in mejores.values()]
    corte = statistics.quantiles(visitas, n=100)[PERCENTIL - 1] if len(visitas) >= 5 else float("inf")
    videos = []
    for clave, mejor in mejores.items():
        gana = mejor.visitas >= corte or (UMBRAL_FIJO is not None and mejor.visitas >= UMBRAL_FIJO)
        retencion = (round(mejor.tiempo_medio_s / mejor.duracion_s, 3)
                     if mejor.tiempo_medio_s and mejor.duracion_s else None)
        videos.append(Video(
            clave=clave, mejor_id=mejor.id, mejor_enlace=mejor.enlace, mejores_visitas=mejor.visitas,
            comentarios_mejor=mejor.comentarios, publicaciones=len(grupos[clave]),
            alguna_en_feed=any(p.en_feed for p in grupos[clave]), pie=mejor.pie, ganador=gana,
            ids=tuple(p.id for p in grupos[clave]), ultima_publicacion=max(p.momento for p in grupos[clave]),
            duracion_s=mejor.duracion_s, retencion=retencion))
    return sorted(videos, key=lambda v: v.mejores_visitas, reverse=True), corte


def main() -> None:
    env = leer_env()
    pubs = candidatas(env)
    if not pubs:
        raise SystemExit("No hay reels candidatos")
    videos, corte = decidir(agrupar(pubs))
    ganadores = [v for v in videos if v.ganador]
    SALIDA.write_text(json.dumps({"corte_percentil": corte, "umbral_fijo": UMBRAL_FIJO,
                                  "videos": [asdict(v) for v in videos]}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"Publicaciones candidatas: {len(pubs)} | vídeos distintos: {len(videos)} | "
          f"corte P{PERCENTIL}: {corte:,.0f} visitas | GANADORES: {len(ganadores)}")
    for v in videos:
        marca = "GANA" if v.ganador else "    "
        feed = "feed" if v.alguna_en_feed else "trial"
        print(f"{marca} {v.mejores_visitas:>9,} vis | {v.comentarios_mejor:>5} com | {v.publicaciones} pub ({feed:<5}) | {v.pie[:50]}")


if __name__ == "__main__":
    sys.exit(main())
