"""MaesTrials — de qué cuenta de Instagram se trata (variable MT_CUENTA; si no está, la de Jose).

Cada cuenta tiene su carpeta de datos y de vídeos. La de Jose usa las de siempre (datos/ y public/v/);
la de Cristian, datos/cristian/ y public/v/cristian/.
Para una cuenta que no es la de Jose, el token y el id salen de IG_TOKEN_<NOMBRE> e IG_USER_ID_<NOMBRE>
(secretos de GitHub o .env) y se ponen como IG_TOKEN / IG_USER_ID, así el resto del código no cambia.
Si el id no es el de la cuenta, se para: nunca se publica en la cuenta equivocada. Los tokens nunca se imprimen.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL_BASE = "https://maestrials.vercel.app/v/"
# Proyecto "maestrials" de Supabase (15-nov). La URL no es secreta; la clave va en SUPABASE_SECRET_KEY.
SUPABASE_URL = "https://ihjjzhfjrsctobwvpzbt.supabase.co"
CUENTAS = {
    # Jose (17-nov, Fase 7): 10 al día como Cristian → público de España, ubicación Madrid, sin "gratis",
    # vídeos en Supabase (carpeta "jose/") y 30 min entre subidas. Sus datos siguen en datos/ (carpeta "").
    "jose": {"arroba": "@josenews.ai", "carpeta": "", "ig_id": "17841438323050307",
             "idioma": "en español de España (palabras de España como ordenador, móvil o vale; tutea al lector)",
             "ubicacion_id": "112446056797834",   # página de lugar "Madrid" (la misma que Cristian)
             "videos_en_supabase": True, "gancho_sin": ["gratis", "gratuit"],
             "minutos_entre_subidas": 30},
    # Cristian (decisión de Jose, 13-nov): público de España → español de España y ubicación Madrid
    "cristian": {"arroba": "@cristianews.ai", "carpeta": "cristian", "ig_id": "17841431048478322",
                 "idioma": "en español de España (palabras de España como ordenador, móvil o vale; tutea al lector)",
                 "ubicacion_id": "112446056797834",   # página de lugar "Madrid" (Instagram la aceptó el 13-nov)
                 # 15-nov: sus vídeos van a Supabase Storage, no al repo (con 10 al día el repo crecería ~4 GB/mes)
                 "videos_en_supabase": True,
                 # 15-nov: sin "gratis" en el gancho (Jose quiere tráfico cualificado, aunque con "gratis" hubo más visitas)
                 "gancho_sin": ["gratis", "gratuit"],
                 # 15-nov: con 10 huecos de hora en hora, 45 min bloqueaba el hueco siguiente si uno salía con retraso
                 "minutos_entre_subidas": 30},
}

NOMBRE = (os.environ.get("MT_CUENTA") or "jose").strip().lower()
if NOMBRE not in CUENTAS:
    raise SystemExit(f"MT_CUENTA desconocida: {NOMBRE!r} (valen: {', '.join(CUENTAS)})")
_CUENTA = CUENTAS[NOMBRE]
ARROBA = _CUENTA["arroba"]
IDIOMA = _CUENTA["idioma"]
UBICACION_ID = _CUENTA["ubicacion_id"]
MINUTOS_ENTRE_SUBIDAS = _CUENTA["minutos_entre_subidas"]
GANCHO_SIN = _CUENTA["gancho_sin"]   # palabras que el gancho no puede llevar (en minúsculas, se buscan dentro)
DATOS = RAIZ / "datos" / _CUENTA["carpeta"]
VIDEOS = RAIZ / "public" / "v" / _CUENTA["carpeta"]
VIDEOS_EN_SUPABASE = _CUENTA["videos_en_supabase"]
CARPETA = _CUENTA["carpeta"]
# En Supabase cada cuenta tiene su carpeta, también la de Jose (cuyos datos van en la raíz de datos/).
CARPETA_SUPABASE = CARPETA or NOMBRE
if VIDEOS_EN_SUPABASE:   # bucket público "videos", una carpeta por cuenta
    URL_VIDEOS = f"{SUPABASE_URL}/storage/v1/object/public/videos/{CARPETA_SUPABASE}/"
else:
    URL_VIDEOS = URL_BASE + (f"{CARPETA}/" if CARPETA else "")


def _leer_dot_env() -> dict[str, str]:
    archivo = RAIZ / ".env"
    if not archivo.exists():
        return {}
    pares = (linea.split("=", 1) for linea in archivo.read_text(encoding="utf-8").splitlines()
             if "=" in linea and not linea.startswith("#"))
    return {k.strip(): v.strip() for k, v in pares}


def _poner_token() -> None:
    dot_env = _leer_dot_env()
    if _CUENTA["carpeta"]:
        sufijo = NOMBRE.upper()
        for clave in ("IG_TOKEN", "IG_USER_ID"):
            valor = os.environ.get(f"{clave}_{sufijo}") or dot_env.get(f"{clave}_{sufijo}")
            if not valor:
                raise SystemExit(f"Falta {clave}_{sufijo} (secreto de GitHub o .env)")
            os.environ[clave] = valor
    ig_id = os.environ.get("IG_USER_ID") or dot_env.get("IG_USER_ID")
    if ig_id != _CUENTA["ig_id"]:
        raise SystemExit(f"El IG_USER_ID no es el de {ARROBA}: me paro para no tocar otra cuenta")


_poner_token()
