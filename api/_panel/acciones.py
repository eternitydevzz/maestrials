"""Acciones del panel que cambian cosas. Solo se usan en el PC (herramientas/servidor_local.py):
ver la cola, publicar ahora, descartar, editar, rehacer con Claude, encender/apagar el autopilot y añadir ganadores.
Cada cambio se sube a GitHub para que el autopilot lo vea.
"""
import json
import re
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import repo
from .config import RAIZ

sys.path.insert(0, str(RAIZ / "fase3"))
sys.path.insert(0, str(RAIZ / "automatico"))
import preparar  # noqa: E402
import publicar as autopilot  # noqa: E402
import variar  # noqa: E402

AJUSTES = RAIZ / "datos" / "ajustes.json"
URL_REEL = re.compile(r"instagram\.com/(?:[\w.]+/)?(?:reel|reels|p)/([A-Za-z0-9_-]+)")
MAX_PIE = 2200            # límite de Instagram para el pie
PAGINAS_BUSQUEDA = 5      # 5 × 50 = las últimas 250 publicaciones de la cuenta
PUBLICADAS_A_MOSTRAR = 30


class ErrorAccion(Exception):
    pass


def _clave(archivo: str) -> str:
    return archivo.rsplit("-", 1)[1].removesuffix(".mp4")


def _pendiente(archivo: str) -> dict:
    ficha = next((f for f in preparar.pendientes() if f["archivo"] == archivo), None)
    if not ficha:
        raise ErrorAccion("Esa versión ya no está en la cola (puede que el autopilot la haya publicado). Sincroniza.")
    return ficha


def _leer_ajustes() -> dict:
    return json.loads(AJUSTES.read_text(encoding="utf-8"))


def _titulos() -> dict[str, str]:
    todos = json.loads(preparar.GANADORES.read_text(encoding="utf-8"))["videos"] + preparar.videos_ganadores()
    return {i: v.get("pie", "") for v in todos for i in v["ids"]}


def proximo_hueco(ahora: datetime, ajustes: dict, registro: list[dict]) -> str | None:
    """Próximo hueco en el que el autopilot publicaría de verdad (salta los de días que ya tienen su cupo)."""
    zona = ZoneInfo(ajustes["zona"])
    ny = ahora.astimezone(zona)
    for dias in range(3):
        dia = (ny + timedelta(days=dias)).date()
        hechas = sum(1 for p in registro if datetime.fromisoformat(p["publicado_en"]).astimezone(zona).date() == dia)
        for orden, hora in enumerate(ajustes["huecos_ny"], start=1):
            momento = datetime(dia.year, dia.month, dia.day, hora, tzinfo=zona)
            if momento > ny and hechas < min(orden, ajustes["maximo_dia"]):
                return momento.isoformat()
    return None


def _resumen(ficha: dict, titulos: dict[str, str]) -> dict:
    return {"archivo": ficha["archivo"], "origen": ficha["origen"], "titulo": titulos.get(ficha["origen"], ""),
            "gancho": ficha["gancho"], "pie": ficha["pie"], "palabra": ficha["palabra"],
            "cambios": ficha["cambios"], "video": f"/v/{ficha['archivo']}", "creada": ficha.get("creada")}


def versiones() -> dict:
    ajustes = _leer_ajustes()
    titulos = _titulos()
    fichas = {f["archivo"]: f for f in variar.todas_las_fichas()}
    publicadas = []
    for p in list(reversed(variar.leer_registro()))[:PUBLICADAS_A_MOSTRAR]:
        ficha = fichas.get(p["archivo"], {})
        publicadas.append({"archivo": p["archivo"], "titulo": titulos.get(p["origen"], ""),
                           "gancho": ficha.get("gancho", []), "publicado_en": p["publicado_en"], "enlace": p.get("enlace"),
                           "visitas_24h": (p.get("metricas_24h") or {}).get("views"),
                           "visitas": (p.get("metricas_ultimas") or {}).get("views")})
    return {"autopilot": ajustes["autopilot"], "huecos_ny": ajustes["huecos_ny"],
            "proximo_hueco": proximo_hueco(datetime.now(timezone.utc), ajustes, variar.leer_registro()),
            "cola": [_resumen(f, titulos) for f in autopilot.cola_por_retencion()], "publicadas": publicadas}


def publicar_ahora(archivo: str) -> dict:
    ficha = _pendiente(archivo)
    try:
        variar.publicar(ficha["origen"], archivo)
    except SystemExit as e:
        raise ErrorAccion(str(e)) from None
    finally:
        repo.guardar("panel: publicar ahora", ["datos"])
    return variar.leer_registro()[-1]


def descartar(archivo: str, subir: bool = True) -> None:
    _pendiente(archivo)
    (variar.VERSIONES / f"{_clave(archivo)}.json").unlink(missing_ok=True)
    (variar.PUBLICO / archivo).unlink(missing_ok=True)
    if subir:
        repo.guardar("panel: descartar versión", ["datos", "public/v"])


def editar(archivo: str, gancho: str, pie: str) -> dict:
    ficha = _pendiente(archivo)
    lineas = variar.partir_gancho(gancho or "")
    if not lineas:
        raise ErrorAccion(f"El gancho tiene que caber en {variar.LINEAS_GANCHO} líneas de {variar.LETRAS_POR_LINEA} letras")
    pie = (pie or "").strip()
    if not re.search(rf"\b{re.escape(ficha['palabra'])}\b", pie):
        raise ErrorAccion(f"El pie tiene que llevar la palabra clave {ficha['palabra']} (tal cual, en mayúsculas)")
    if len(pie) > MAX_PIE:
        raise ErrorAccion(f"El pie pasa de {MAX_PIE} caracteres")
    if not (variar.carpeta(ficha["origen"]) / "original.mp4").exists():
        variar.descargar(ficha["origen"])
    clave = secrets.token_hex(4)
    nueva = {**ficha, "archivo": f"{ficha['origen']}-f3-{clave}.mp4", "clave": clave, "gancho": lineas, "pie": pie,
             "creada": datetime.now(timezone.utc).isoformat(), "editada_de": archivo}
    (variar.VERSIONES / f"{clave}.json").write_text(json.dumps(nueva, ensure_ascii=False, indent=1), encoding="utf-8")
    variar.montar_ficha(nueva)
    descartar(archivo, subir=False)
    repo.guardar("panel: editar versión", ["datos", "public/v"])
    return _resumen(nueva, _titulos())


def rehacer(archivo: str) -> None:
    ficha = _pendiente(archivo)
    descartar(archivo, subir=False)
    try:
        variar.preparar(ficha["origen"])
    except SystemExit as e:
        raise ErrorAccion(f"No se pudo rehacer: {e}") from None
    finally:
        repo.guardar("panel: rehacer versión", ["datos", "public/v"])


def cambiar_autopilot(encendido: bool) -> dict:
    nuevos = {**_leer_ajustes(), "autopilot": bool(encendido)}
    AJUSTES.write_text(json.dumps(nuevos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    repo.guardar(f"panel: autopilot {'encendido' if encendido else 'apagado'}", ["datos/ajustes.json"])
    return nuevos


def _buscar_reel(env: dict[str, str], codigo: str) -> dict:
    params = {"fields": "id,permalink,media_product_type,is_shared_to_feed,timestamp,caption,media_url", "limit": "50"}
    ruta = f"{env['IG_USER_ID']}/media"
    for _ in range(PAGINAS_BUSQUEDA):
        pagina = variar.api("GET", ruta, params)
        for m in pagina.get("data", []):
            if f"/{codigo}/" in (m.get("permalink") or ""):
                return m
        siguiente = pagina.get("paging", {}).get("cursors", {}).get("after")
        if not siguiente or not pagina.get("paging", {}).get("next"):
            break
        params = {**params, "after": siguiente}
    raise ErrorAccion("No encuentro ese reel entre las últimas publicaciones de tu cuenta")


def anadir_ganador(enlace: str) -> dict:
    coincide = URL_REEL.search(enlace or "")
    if not coincide:
        raise ErrorAccion("Pega el enlace de un reel de Instagram (https://www.instagram.com/reel/XXXX/)")
    env = variar.leer_env()
    try:
        reel = _buscar_reel(env, coincide.group(1))
        valores = {d["name"]: (d.get("values") or [{}])[0].get("value") for d in variar.api(
            "GET", f"{reel['id']}/insights", {"metric": "views,ig_reels_avg_watch_time"}).get("data", [])}
    except SystemExit as e:
        raise ErrorAccion(str(e)) from None
    if reel.get("media_product_type") != "REELS":
        raise ErrorAccion("Ese enlace no es un reel")
    if any(reel["id"] in v["ids"] for v in preparar.videos_ganadores()):
        raise ErrorAccion("Ese vídeo ya está en la lista de ganadores")
    salida = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                             reel.get("media_url", "")], capture_output=True, text=True, check=False).stdout.strip()
    duracion = round(float(salida), 1) if salida.replace(".", "", 1).isdigit() else None
    medio_s = (valores.get("ig_reels_avg_watch_time") or 0) / 1000
    momento = datetime.strptime(reel["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc).isoformat()
    entrada = {"clave": reel["id"], "mejor_id": reel["id"], "mejor_enlace": reel["permalink"],
               "mejores_visitas": int(valores.get("views") or 0), "comentarios_mejor": 0, "publicaciones": 1,
               "alguna_en_feed": bool(reel.get("is_shared_to_feed")),
               "pie": (reel.get("caption") or "").replace("\n", " ")[:80], "ganador": True, "ids": [reel["id"]],
               "ultima_publicacion": momento, "duracion_s": duracion,
               "retencion": round(medio_s / duracion, 3) if duracion and medio_s else None,
               "manual": True, "anadido_en": datetime.now(timezone.utc).isoformat()}
    anteriores = json.loads(preparar.MANUALES.read_text(encoding="utf-8")) if preparar.MANUALES.exists() else []
    preparar.MANUALES.write_text(json.dumps([*anteriores, entrada], ensure_ascii=False, indent=1), encoding="utf-8")
    repo.guardar("panel: añadir ganador a mano", ["datos/manuales.json"])
    return entrada
