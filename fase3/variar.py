"""MaesTrials — Fase 3: versiones con cambios suaves, gancho en pantalla y pie reescrito por Claude.

Uso (desde la raíz del proyecto):
  python -I -X utf8 fase3/variar.py preparar <media_id> [<media_id> ...]
  python -I -X utf8 fase3/variar.py remontar <media_id> <archivo.mp4>   (mismo gancho y pie, sin llamar a Claude)
  python -I -X utf8 fase3/variar.py publicar <media_id> <archivo.mp4>

`preparar` monta la versión en public/v/ y deja su ficha en trabajo/<media_id>/.
`publicar` solo se usa cuando Jose ha visto y aprobado la versión, y después de commit + push.
Los tokens se leen de .env y nunca se imprimen.
"""
import json
import random
import re
import secrets
import subprocess
import sys
import textwrap
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase1"))
from pasada import (PUBLICO, TRABAJO, api, carpeta, descargar,  # noqa: E402
                    esperar_procesado, leer_env, medir)

URL_PUBLICA = "https://maestrials.vercel.app/v/"
REGISTRO = TRABAJO / "publicaciones.json"
DIAS_MINIMOS = 4                  # decisión de Jose: mínimo 4 días entre publicaciones del mismo vídeo
MINUTOS_ENTRE_SUBIDAS = 45

MODELO_CLAUDE = "claude-opus-5-5"
INTENTOS_CLAUDE = 3
MODELO_WHISPER = "small"

# Gancho en pantalla: caja blanca arriba, encima de la zona de subtítulos, solo al principio.
FUENTE = "C\\:/Windows/Fonts/ariblk.ttf"
SEGUNDOS_GANCHO = 3.0
LETRAS_POR_LINEA = 22
LINEAS_GANCHO = 2
TAM_LETRA = 38
BORDE_CAJA = 16
Y_PRIMERA_LINEA = 0.09            # proporción de la altura del vídeo
SALTO_LINEA = TAM_LETRA + 2 * BORDE_CAJA - 4   # las dos cajas se tocan: parecen una sola etiqueta

# Márgenes de los cambios suaves (se sortea un valor dentro de cada uno).
MARGEN_ZOOM = (1.04, 1.10)
MARGEN_DESPLAZAR_Y = (0.35, 0.45)
MARGEN_VELOCIDAD = (1.00, 1.05)
MARGEN_SATURACION = (1.00, 1.08)
MARGEN_CONTRASTE = (1.00, 1.04)
MARGEN_INICIO_S = (0.0, 0.5)


@dataclass(frozen=True)
class Cambios:
    zoom: float
    desplazar_y: float
    velocidad: float
    saturacion: float
    contraste: float
    inicio_s: float


def sortear_cambios(semilla: int) -> Cambios:
    azar = random.Random(semilla)

    def valor(margen: tuple[float, float]) -> float:
        return round(azar.uniform(*margen), 3)

    return Cambios(valor(MARGEN_ZOOM), valor(MARGEN_DESPLAZAR_Y), valor(MARGEN_VELOCIDAD),
                   valor(MARGEN_SATURACION), valor(MARGEN_CONTRASTE), valor(MARGEN_INICIO_S))


def transcribir(video: Path) -> str:
    guardada = video.parent / "transcripcion.txt"
    if guardada.exists():
        return guardada.read_text(encoding="utf-8")
    import numpy as np
    from faster_whisper import WhisperModel
    # El audio lo saca ffmpeg (16 kHz, mono): así no dependemos del paquete av, que choca de versión.
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "f32le", "-ac", "1",
                            "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(crudo, dtype=np.float32)
    modelo = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(audio, language="es")
    texto = " ".join(s.text.strip() for s in segmentos)
    guardada.write_text(texto, encoding="utf-8")
    return texto


def palabra_clave(pie: str) -> str:
    encontrada = re.search(r"(?i:escribe|comenta)\s+[\"“«]?([A-ZÁÉÍÓÚÑ0-9]{2,})\b", pie)
    if not encontrada:
        raise SystemExit("No encuentro la palabra clave (\"escribe PALABRA\" o \"comenta PALABRA\") en el pie")
    return encontrada.group(1)


def partir_gancho(gancho: str) -> list[str] | None:
    """Parte el gancho en líneas lo más parecidas posible en largo (queda mejor que llenar la primera)."""
    texto = gancho.strip()
    ancho_minimo = max(1, -(-len(texto) // LINEAS_GANCHO))
    for ancho in range(ancho_minimo, LETRAS_POR_LINEA + 1):
        lineas = textwrap.wrap(texto, ancho)
        if 0 < len(lineas) <= LINEAS_GANCHO:
            return lineas
    return None


INSTRUCCIONES = f"""Escribes para el Instagram @josenews.ai: IA práctica, en español neutro, tono cercano y directo.
Te paso la transcripción de un reel, su pie original, la palabra clave de su automatización y los ganchos que ya se usaron.

Devuelve dos textos:
- gancho: frase que se verá en pantalla durante los primeros {SEGUNDOS_GANCHO:.0f} segundos, encima del vídeo.
  Como mucho {LETRAS_POR_LINEA * LINEAS_GANCHO - 8} caracteres, contando espacios. Sin emojis, sin comillas y sin hashtags.
  Tiene que dar curiosidad y ser fiel a lo que dice el vídeo: no prometas nada que el vídeo no cuente.
  Que sea distinto de los ganchos ya usados.
- pie: el pie original reescrito con otras palabras, en 1 o 2 frases y de 3 a 5 hashtags relacionados.
  Mantén la llamada a la acción con la palabra clave EXACTA y en mayúsculas, con el mismo verbo que el original
  (por ejemplo "escribe API"). Puedes cambiar los emojis. Como mucho 300 caracteres."""

ESQUEMA_TEXTOS = {
    "type": "object",
    "properties": {"gancho": {"type": "string"}, "pie": {"type": "string"}},
    "required": ["gancho", "pie"],
    "additionalProperties": False,
}


def pedir_textos(transcripcion: str, pie: str, palabra: str, ganchos_usados: list[str]) -> tuple[list[str], str]:
    import anthropic
    cliente = anthropic.Anthropic(api_key=leer_env()["ANTHROPIC_API_KEY"])
    peticion = (f"TRANSCRIPCIÓN:\n{transcripcion}\n\nPIE ORIGINAL:\n{pie}\n\n"
                f"PALABRA CLAVE: {palabra}\n\nGANCHOS YA USADOS: {ganchos_usados or 'ninguno'}")
    for intento in range(1, INTENTOS_CLAUDE + 1):
        try:
            respuesta = cliente.beta.messages.create(
                model=MODELO_CLAUDE, max_tokens=16000, system=INSTRUCCIONES,
                messages=[{"role": "user", "content": peticion}],
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ESQUEMA_TEXTOS}},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except anthropic.APIConnectionError:
            raise SystemExit("ERROR: no hay conexión con la API de Claude")
        except anthropic.APIStatusError as e:
            raise SystemExit(f"ERROR de la API de Claude ({e.status_code}): {e.message}")
        if respuesta.stop_reason == "refusal":
            raise SystemExit("Claude rechazó la petición (refusal); no se monta esta versión")
        datos = json.loads(next(b.text for b in respuesta.content if b.type == "text"))
        lineas = partir_gancho(datos["gancho"])
        palabra_ok = re.search(rf"\b{re.escape(palabra)}\b", datos["pie"]) is not None
        if lineas and palabra_ok:
            return lineas, datos["pie"].strip()
        motivo = [] if lineas else [f"gancho de {len(datos['gancho'])} letras no cabe: {datos['gancho']!r}"]
        motivo += [] if palabra_ok else [f"el pie no lleva {palabra}: {datos['pie']!r}"]
        print(f"  intento {intento} rechazado ({'; '.join(motivo)}); repito")
    raise SystemExit(f"Claude no devolvió textos válidos en {INTENTOS_CLAUDE} intentos")


def ruta_ffmpeg(ruta: Path) -> str:
    return str(ruta).replace("\\", "/").replace(":", "\\:")


def filtro_gancho(lineas: list[str], carpeta_version: Path) -> str:
    partes = []
    for i, linea in enumerate(lineas):
        archivo = carpeta_version / f"gancho_{i}.txt"
        archivo.write_text(linea, encoding="utf-8")
        partes.append(
            f"drawtext=fontfile='{FUENTE}':textfile='{ruta_ffmpeg(archivo)}':fontsize={TAM_LETRA}"
            f":fontcolor=white:box=1:boxcolor=black@0.85:boxborderw={BORDE_CAJA}"
            f":x=(w-text_w)/2:y=h*{Y_PRIMERA_LINEA}+{i * SALTO_LINEA}"
            f":enable='between(t,0,{SEGUNDOS_GANCHO})'")
    return ",".join(partes)


def montar(original: Path, destino: Path, cambios: Cambios, gancho: str) -> float:
    ancho, alto, _, _ = medir(original)
    filtro_v = (f"scale=iw*{cambios.zoom}:ih*{cambios.zoom},"
                f"crop={ancho}:{alto}:(iw-{ancho})/2:(ih-{alto})*{cambios.desplazar_y},"
                f"eq=saturation={cambios.saturacion}:contrast={cambios.contraste},"
                f"setpts=PTS/{cambios.velocidad},{gancho},format=yuv420p")
    orden = ["ffmpeg", "-y", "-v", "error", "-ss", str(cambios.inicio_s), "-i", str(original),
             "-vf", filtro_v, "-af", f"atempo={cambios.velocidad}",
             "-map_metadata", "-1", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
             "-movflags", "+faststart", "-use_editlist", "0", str(destino)]
    inicio = time.time()
    subprocess.run(orden, check=True)
    return time.time() - inicio


def fichas(media_id: str) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(carpeta(media_id).glob("version_*.json"))]


def preparar(media_id: str) -> None:
    if not (carpeta(media_id) / "original.mp4").exists():
        descargar(media_id)
    original = carpeta(media_id) / "original.mp4"
    info = json.loads((carpeta(media_id) / "info.json").read_text(encoding="utf-8"))
    palabra = palabra_clave(info["caption"])
    print(f"[{media_id}] transcribiendo…")
    transcripcion = transcribir(original)
    usados = [" ".join(f["gancho"]) for f in fichas(media_id)]
    print(f"[{media_id}] pidiendo gancho y pie a Claude…")
    lineas, pie = pedir_textos(transcripcion, info["caption"], palabra, usados)
    clave = secrets.token_hex(4)
    semilla = secrets.randbits(32)
    ficha = {"origen": media_id, "archivo": f"{media_id}-f3-{clave}.mp4", "clave": clave, "semilla": semilla,
             "cambios": asdict(sortear_cambios(semilla)), "gancho": lineas, "pie": pie, "palabra": palabra,
             "creada": datetime.now(timezone.utc).isoformat()}
    (carpeta(media_id) / f"version_{clave}.json").write_text(
        json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
    montar_ficha(ficha)


def montar_ficha(ficha: dict) -> None:
    """Monta (o vuelve a montar) una versión con los cambios, gancho y pie guardados en su ficha."""
    media_id, archivo = ficha["origen"], ficha["archivo"]
    clave = archivo.rsplit("-", 1)[1].removesuffix(".mp4")
    PUBLICO.mkdir(parents=True, exist_ok=True)
    segundos = montar(carpeta(media_id) / "original.mp4", PUBLICO / archivo, Cambios(**ficha["cambios"]),
                      filtro_gancho(ficha["gancho"], carpeta(media_id)))
    vista = carpeta(media_id) / f"vista_{clave}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(PUBLICO / archivo),
                    "-frames:v", "1", str(vista)], check=True)
    _, _, _, duracion = medir(PUBLICO / archivo)
    print(f"[{media_id}] versión: public/v/{archivo} ({duracion:.1f} s, ffmpeg {segundos:.0f} s)")
    print(f"  cambios: {ficha['cambios']}")
    print(f"  gancho:  {' / '.join(ficha['gancho'])}")
    print(f"  pie:     {ficha['pie']}")
    print(f"  vista:   {vista}")


def leer_registro() -> list[dict]:
    registro = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else []
    for anterior in TRABAJO.glob("*/publicado.json"):   # publicaciones de la Fase 1
        datos = json.loads(anterior.read_text(encoding="utf-8"))
        registro.append({"origen": anterior.parent.name, "publicado_en": datos["publicado_en"]})
    return registro


def comprobar_reglas(media_id: str) -> None:
    ahora = datetime.now(timezone.utc)
    registro = leer_registro()
    del_video = [datetime.fromisoformat(r["publicado_en"]) for r in registro if r["origen"] == media_id]
    if del_video and ahora - max(del_video) < timedelta(days=DIAS_MINIMOS):
        raise SystemExit(f"Regla de {DIAS_MINIMOS} días: {media_id} salió el {max(del_video):%d-%b %H:%M} UTC")
    todas = [datetime.fromisoformat(r["publicado_en"]) for r in registro]
    if todas and ahora - max(todas) < timedelta(minutes=MINUTOS_ENTRE_SUBIDAS):
        falta = timedelta(minutes=MINUTOS_ENTRE_SUBIDAS) - (ahora - max(todas))
        raise SystemExit(f"Faltan {int(falta.total_seconds() // 60) + 1} min para cumplir los {MINUTOS_ENTRE_SUBIDAS} min entre subidas")


def comprobar_url(url: str) -> None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            if r.status == 200:
                return
    except Exception as e:  # noqa: BLE001 — cualquier fallo de red significa "no está publicada"
        raise SystemExit(f"El vídeo no está en la URL pública ({url}): {e}. ¿Hiciste commit + push?")
    raise SystemExit(f"El vídeo no está en la URL pública ({url})")


def publicar(media_id: str, archivo: str) -> None:
    ficha = next((f for f in fichas(media_id) if f["archivo"] == archivo), None)
    if not ficha:
        raise SystemExit(f"No hay ficha de {archivo} en trabajo/{media_id}/")
    comprobar_reglas(media_id)
    url = URL_PUBLICA + archivo
    comprobar_url(url)
    env = leer_env()
    contenedor = api("POST", f"{env['IG_USER_ID']}/media", {
        "media_type": "REELS", "video_url": url, "caption": ficha["pie"], "share_to_feed": "false",
        "trial_params": json.dumps({"graduation_strategy": "MANUAL"}),
    })["id"]
    print(f"Contenedor creado: {contenedor}")
    esperar_procesado(contenedor)
    publicado = api("POST", f"{env['IG_USER_ID']}/media_publish", {"creation_id": contenedor})["id"]
    enlace = api("GET", publicado, {"fields": "permalink"}).get("permalink")
    registro = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else []
    registro.append({"origen": media_id, "archivo": archivo, "publicacion": publicado, "enlace": enlace,
                     "publicado_en": datetime.now(timezone.utc).isoformat()})
    REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO como trial reel: {publicado} → {enlace}")


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    comando = sys.argv[1]
    if comando == "preparar":
        for media_id in sys.argv[2:]:
            preparar(media_id)
    elif comando == "publicar" and len(sys.argv) == 4:
        publicar(sys.argv[2], sys.argv[3])
    elif comando == "remontar" and len(sys.argv) == 4:
        ficha = next((f for f in fichas(sys.argv[2]) if f["archivo"] == sys.argv[3]), None)
        if not ficha:
            raise SystemExit(f"No hay ficha de {sys.argv[3]} en trabajo/{sys.argv[2]}/")
        montar_ficha(ficha)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
