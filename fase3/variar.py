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
sys.path.append(str(RAIZ / "automatico"))
import cuenta  # noqa: E402
import niveles  # noqa: E402
from pasada import (PUBLICO, TRABAJO, api, carpeta, descargar,  # noqa: E402
                    esperar_procesado, leer_env, medir)

URL_PUBLICA = cuenta.URL_VIDEOS
REGISTRO = cuenta.DATOS / "publicaciones.json"   # en el repo: lo leen y escriben el PC y GitHub Actions
DIAS_MINIMOS = 4                  # decisión de Jose: mínimo 4 días entre publicaciones del mismo vídeo
MINUTOS_ENTRE_SUBIDAS = 45

MODELO_CLAUDE = "claude-opus-5-5"
INTENTOS_CLAUDE = 3
MODELO_WHISPER = "small"

# Gancho en pantalla, estilo texto "Classic" de Instagram (decisión de Jose, 13-nov): letra blanca en mayúsculas,
# cajas negras redondeadas unidas, alineado a la izquierda, arriba de la zona segura y solo al principio.
FUENTE = RAIZ / "recursos" / "fuentes" / "InstrumentSans.ttf"   # libre (OFL); la más parecida a "Classic" que probamos
PESO_FUENTE = 700                 # Bold (el máximo de Instrument Sans)
VERSIONES = cuenta.DATOS / "versiones"                 # fichas de cada versión (en el repo)
TRANSCRIPCIONES = cuenta.DATOS / "transcripciones"     # Whisper solo se ejecuta una vez por vídeo
SEGUNDOS_GANCHO = 3.0
LETRAS_POR_LINEA = 22
LINEAS_GANCHO = 2
ZONA_SEGURA_ARRIBA = 0.14         # las guías de reels piden dejar libre el 14 % de arriba (lo tapa la interfaz)
ZONA_SEGURA_LADO = 0.06           # y el 6 % de cada lado
ANCHO_MAX_GANCHO = 0.80           # la línea más larga ocupa como mucho el 80 % del ancho del vídeo
TAM_LETRA = 0.075                 # tamaño de letra = 7,5 % del ancho del vídeo (se reduce si no cabe)
ALTO_LINEA = 1.45                 # alto de cada caja, en veces el tamaño de letra
MARGEN_CAJA = 0.42                # margen del texto dentro de la caja, en veces el tamaño de letra
RADIO_CAJA = 0.32                 # radio de las esquinas, en veces el tamaño de letra

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


def transcribir(media_id: str, video: Path) -> str:
    guardada = TRANSCRIPCIONES / f"{media_id}.txt"
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
    TRANSCRIPCIONES.mkdir(parents=True, exist_ok=True)
    guardada.write_text(texto, encoding="utf-8")
    return texto


def palabra_clave(pie: str) -> str:
    encontrada = re.search(r"(?i:escribe|comenta)\s+(?i:la\s+palabra\s+)?[*\"“«]*([A-ZÁÉÍÓÚÑ0-9]{2,})\b", pie)
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


INSTRUCCIONES = f"""Escribes para el Instagram {cuenta.ARROBA}: IA práctica, {cuenta.IDIOMA}, tono cercano y directo.
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


def fuente_gancho(tam: int):
    from PIL import ImageFont
    fuente = ImageFont.truetype(str(FUENTE), tam)
    ejes = fuente.get_variation_axes()   # fuente variable: ancho normal y grosor Bold
    fuente.set_variation_by_axes([PESO_FUENTE if "eight" in str(e["name"]) else e["maximum"] if "idth" in str(e["name"])
                                  else e["default"] for e in ejes])
    return fuente


def dibujar_gancho(lineas: list[str], ancho_video: int, destino: Path) -> None:
    """PNG transparente con el gancho estilo "Classic": cajas negras redondeadas unidas, texto blanco a la izquierda."""
    from PIL import Image, ImageDraw
    textos = [t.upper() for t in lineas]
    tam = int(ancho_video * TAM_LETRA)
    fuente = fuente_gancho(tam)
    while max(fuente.getlength(t) for t in textos) > ancho_video * ANCHO_MAX_GANCHO and tam > 12:
        tam -= 2
        fuente = fuente_gancho(tam)
    alto, margen, radio = int(tam * ALTO_LINEA), int(tam * MARGEN_CAJA), int(tam * RADIO_CAJA)
    anchos = [int(fuente.getlength(t)) + 2 * margen for t in textos]
    imagen = Image.new("RGBA", (max(anchos) + 2, alto * len(textos) + 2), (0, 0, 0, 0))
    lapiz = ImageDraw.Draw(imagen)
    for i, ancho in enumerate(anchos):
        lapiz.rounded_rectangle((0, i * alto, ancho, (i + 1) * alto), radio, fill="black")
        if i:   # se une con la caja de arriba, sin muescas en la junta (como en Instagram)
            lapiz.rectangle((0, i * alto - radio, min(ancho, anchos[i - 1]), i * alto + radio), fill="black")
    for i, texto in enumerate(textos):
        lapiz.text((margen, i * alto + alto / 2), texto, font=fuente, fill="white", anchor="lm")
    imagen.save(destino)


def montar(original: Path, destino: Path, cambios: Cambios, lineas_gancho: list[str], png_gancho: Path) -> float:
    ancho, alto, _, _ = medir(original)
    dibujar_gancho(lineas_gancho, ancho, png_gancho)
    x, y = int(ancho * ZONA_SEGURA_LADO), int(alto * ZONA_SEGURA_ARRIBA) + 8
    filtro = (f"[0:v]scale=iw*{cambios.zoom}:ih*{cambios.zoom},"
              f"crop={ancho}:{alto}:(iw-{ancho})/2:(ih-{alto})*{cambios.desplazar_y},"
              f"eq=saturation={cambios.saturacion}:contrast={cambios.contraste},"
              f"setpts=PTS/{cambios.velocidad}[base];"
              f"[base][1:v]overlay={x}:{y}:enable='between(t,0,{SEGUNDOS_GANCHO})',format=yuv420p[v]")
    orden = ["ffmpeg", "-y", "-v", "error", "-ss", str(cambios.inicio_s), "-i", str(original), "-i", str(png_gancho),
             "-filter_complex", filtro, "-map", "[v]", "-map", "0:a:0?", "-af", f"atempo={cambios.velocidad}",
             "-map_metadata", "-1", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
             "-movflags", "+faststart", "-use_editlist", "0", str(destino)]
    inicio = time.time()
    subprocess.run(orden, check=True)
    return time.time() - inicio


def todas_las_fichas() -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(VERSIONES.glob("*.json"))]


def fichas(media_id: str) -> list[dict]:
    return [f for f in todas_las_fichas() if f["origen"] == media_id]


def preparar(media_id: str) -> None:
    if not (carpeta(media_id) / "original.mp4").exists():
        descargar(media_id)
    original = carpeta(media_id) / "original.mp4"
    info = json.loads((carpeta(media_id) / "info.json").read_text(encoding="utf-8"))
    palabra = palabra_clave(info["caption"])
    print(f"[{media_id}] transcribiendo…")
    transcripcion = transcribir(media_id, original)
    usados = [" ".join(f["gancho"]) for f in fichas(media_id)]
    print(f"[{media_id}] pidiendo gancho y pie a Claude…")
    lineas, pie = pedir_textos(transcripcion, info["caption"], palabra, usados)
    clave = secrets.token_hex(4)
    semilla = secrets.randbits(32)
    ficha = {"origen": media_id, "archivo": f"{media_id}-f3-{clave}.mp4", "clave": clave, "semilla": semilla,
             "cambios": asdict(sortear_cambios(semilla)), "gancho": lineas, "pie": pie, "palabra": palabra,
             "creada": datetime.now(timezone.utc).isoformat()}
    VERSIONES.mkdir(parents=True, exist_ok=True)
    (VERSIONES / f"{clave}.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
    montar_ficha(ficha)


def montar_ficha(ficha: dict) -> None:
    """Monta (o vuelve a montar) una versión con los cambios, gancho y pie guardados en su ficha."""
    media_id, archivo = ficha["origen"], ficha["archivo"]
    clave = archivo.rsplit("-", 1)[1].removesuffix(".mp4")
    PUBLICO.mkdir(parents=True, exist_ok=True)
    segundos = montar(carpeta(media_id) / "original.mp4", PUBLICO / archivo, Cambios(**ficha["cambios"]),
                      ficha["gancho"], carpeta(media_id) / f"gancho_{clave}.png")
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
    """Todas las publicaciones de MaesTrials (la de la Fase 1 ya está dentro)."""
    return json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else []


def comprobar_reglas(media_id: str) -> None:
    ahora = datetime.now(timezone.utc)
    registro = leer_registro()
    mismo_video = niveles.hermanos(media_id)   # el mismo vídeo publicado con otros ids también cuenta
    del_video = [datetime.fromisoformat(r["publicado_en"]) for r in registro if r["origen"] in mismo_video]
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
    parametros = {
        "media_type": "REELS", "video_url": url, "caption": ficha["pie"], "share_to_feed": "false",
        "trial_params": json.dumps({"graduation_strategy": "MANUAL"}),
    }
    if cuenta.UBICACION_ID:
        parametros["location_id"] = cuenta.UBICACION_ID
    contenedor = api("POST", f"{env['IG_USER_ID']}/media", parametros)["id"]
    print(f"Contenedor creado: {contenedor}")
    esperar_procesado(contenedor)
    publicado = api("POST", f"{env['IG_USER_ID']}/media_publish", {"creation_id": contenedor})["id"]
    # Se apunta YA: si algo falla después, el autopilot no puede volver a publicar lo mismo.
    entrada = {"origen": media_id, "archivo": archivo, "publicacion": publicado, "enlace": None,
               "publicado_en": datetime.now(timezone.utc).isoformat()}
    anterior = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else []
    REGISTRO.write_text(json.dumps([*anterior, entrada], ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        enlace = api("GET", publicado, {"fields": "permalink"}).get("permalink")
    except (SystemExit, Exception) as e:  # noqa: BLE001 — el enlace es un extra; lo publicado ya está apuntado
        print(f"  (no se pudo leer el enlace: {e})")
        enlace = None
    if enlace:
        REGISTRO.write_text(json.dumps([*anterior, {**entrada, "enlace": enlace}], ensure_ascii=False, indent=1),
                            encoding="utf-8")
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
