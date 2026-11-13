"""MaesTrials — Fase 1: pasada de punta a punta con 1 reel ganador.

Uso (desde la raíz del proyecto):
  python -I -X utf8 fase1/pasada.py descargar <media_id>
  python -I -X utf8 fase1/pasada.py version   <media_id>
  python -I -X utf8 fase1/pasada.py publicar  <media_id> <video_url_publica>
  python -I -X utf8 fase1/pasada.py estado    <media_id>

El token se lee de .env y nunca se imprime.
"""
import json
import os
import secrets
import subprocess
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRABAJO = RAIZ / "trabajo"
sys.path.append(str(RAIZ / "automatico"))
import cuenta  # noqa: E402

PUBLICO = cuenta.VIDEOS   # Jose: public/v/ · Cristian: public/v/cristian/

# Cambios de la versión 1 (Fase 1). La variedad de verdad llega en la Fase 3.
ZOOM = 1.10            # reencuadre: 10 % más cerca
DESPLAZAR_Y = 0.40     # el recorte se coge algo por encima del centro (0 = arriba, 0.5 = centro)
VELOCIDAD = 1.05       # ritmo: 5 % más rápido (imagen y sonido)
SATURACION = 1.08
CONTRASTE = 1.04

ESPERA_ESTADO_S = 20   # cada cuánto se mira si Instagram ha procesado el vídeo
INTENTOS_ESTADO = 30   # 30 × 20 s = 10 min como mucho


CLAVES_ENTORNO = ("IG_TOKEN", "IG_USER_ID", "GRAPH_BASE", "ANTHROPIC_API_KEY")


def leer_env():
    """En el PC, de .env; en GitHub Actions, de las variables de entorno (secretos)."""
    datos = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.startswith("#"):
                clave, valor = linea.split("=", 1)
                datos[clave.strip()] = valor.strip()
    datos.update({k: v for k, v in os.environ.items() if k in CLAVES_ENTORNO and v})
    return datos


def api(metodo, ruta, params):
    env = leer_env()
    params = {**params, "access_token": env["IG_TOKEN"]}
    url = f"{env['GRAPH_BASE']}/{ruta}"
    datos = urllib.parse.urlencode(params).encode()
    if metodo == "GET":
        peticion = urllib.request.Request(url + "?" + datos.decode())
    else:
        peticion = urllib.request.Request(url, data=datos, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error = json.loads(e.read().decode("utf-8")).get("error", {})
        raise SystemExit(f"ERROR de Instagram ({error.get('code')}): {error.get('message')}")


def carpeta(media_id):
    c = TRABAJO / media_id
    c.mkdir(parents=True, exist_ok=True)
    return c


def descargar(media_id):
    m = api("GET", media_id, {"fields": "media_url,caption,permalink,timestamp,media_product_type"})
    if m.get("media_product_type") != "REELS":
        raise SystemExit(f"{media_id} no es un reel ({m.get('media_product_type')})")
    insights = api("GET", f"{media_id}/insights", {"metric": "views"})
    visitas = insights["data"][0]["values"][0]["value"]
    destino = carpeta(media_id) / "original.mp4"
    a_mano = cuenta.DATOS / "originales" / f"{media_id}.mp4"   # Instagram no da el vídeo si lleva música con derechos
    if m.get("media_url"):
        urllib.request.urlretrieve(m["media_url"], destino)
    elif a_mano.exists():
        shutil.copyfile(a_mano, destino)
    else:
        raise SystemExit(f"{media_id}: Instagram no da el vídeo y no hay archivo en {a_mano.relative_to(RAIZ)}")
    info = {"id": media_id, "permalink": m["permalink"], "timestamp": m["timestamp"],
            "visitas": visitas, "caption": m.get("caption") or ""}
    (carpeta(media_id) / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Descargado: {destino} ({destino.stat().st_size / 1e6:.1f} MB) | {visitas:,} visitas")


def medir(video):
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True)
    j = json.loads(salida.stdout)
    s = j["streams"][0]
    return int(s["width"]), int(s["height"]), s["r_frame_rate"], float(j["format"]["duration"])


def version(media_id):
    original = carpeta(media_id) / "original.mp4"
    ancho, alto, fps, dur = medir(original)
    PUBLICO.mkdir(parents=True, exist_ok=True)
    nombre = f"{media_id}-v1-{secrets.token_hex(4)}.mp4"
    destino = PUBLICO / nombre
    filtro_v = (f"scale=iw*{ZOOM}:ih*{ZOOM},"
                f"crop={ancho}:{alto}:(iw-{ancho})/2:(ih-{alto})*{DESPLAZAR_Y},"
                f"eq=saturation={SATURACION}:contrast={CONTRASTE},"
                f"setpts=PTS/{VELOCIDAD},format=yuv420p")
    filtro_a = f"atempo={VELOCIDAD}"
    orden = ["ffmpeg", "-y", "-v", "error", "-i", str(original), "-vf", filtro_v, "-af", filtro_a,
             "-map_metadata", "-1", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
             "-movflags", "+faststart", "-use_editlist", "0", str(destino)]
    inicio = time.time()
    subprocess.run(orden, check=True)
    segundos = time.time() - inicio
    _, _, _, dur_nueva = medir(destino)
    print(f"Versión: {destino}")
    print(f"Original {ancho}x{alto} {fps} fps {dur:.1f} s -> versión {dur_nueva:.1f} s | "
          f"{destino.stat().st_size / 1e6:.1f} MB | ffmpeg tardó {segundos:.0f} s")


def esperar_procesado(contenedor):
    for _ in range(INTENTOS_ESTADO):
        estado = api("GET", contenedor, {"fields": "status_code,status"})
        codigo = estado.get("status_code")
        print(f"  estado del vídeo en Instagram: {codigo}")
        if codigo == "FINISHED":
            return
        if codigo in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Instagram no pudo procesar el vídeo: {estado.get('status')}")
        time.sleep(ESPERA_ESTADO_S)
    raise SystemExit("Instagram tardó demasiado en procesar el vídeo")


def publicar(media_id, video_url):
    env = leer_env()
    info = json.loads((carpeta(media_id) / "info.json").read_text(encoding="utf-8"))
    contenedor = api("POST", f"{env['IG_USER_ID']}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": info["caption"],
        "share_to_feed": "false",
        "trial_params": json.dumps({"graduation_strategy": "MANUAL"}),
    })["id"]
    print(f"Contenedor creado: {contenedor}")
    esperar_procesado(contenedor)
    publicado = api("POST", f"{env['IG_USER_ID']}/media_publish", {"creation_id": contenedor})["id"]
    registro = {"contenedor": contenedor, "publicacion": publicado, "video_url": video_url,
                "publicado_en": datetime.now(timezone.utc).isoformat()}
    (carpeta(media_id) / "publicado.json").write_text(json.dumps(registro, indent=1), encoding="utf-8")
    print(f"PUBLICADO como trial reel: {publicado}")
    estado(media_id)


def estado(media_id):
    registro = json.loads((carpeta(media_id) / "publicado.json").read_text(encoding="utf-8"))
    m = api("GET", registro["publicacion"], {"fields": "permalink,timestamp,media_product_type,is_shared_to_feed"})
    print(json.dumps(m, ensure_ascii=False, indent=1))


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    comando, media_id = sys.argv[1], sys.argv[2]
    if comando == "descargar":
        descargar(media_id)
    elif comando == "version":
        version(media_id)
    elif comando == "publicar":
        if len(sys.argv) < 4:
            raise SystemExit("Falta la URL pública del vídeo")
        publicar(media_id, sys.argv[3])
    elif comando == "estado":
        estado(media_id)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
