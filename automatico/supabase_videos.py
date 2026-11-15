"""MaesTrials — vídeos en Supabase Storage (bucket público "videos") para las cuentas con videos_en_supabase.

Por qué (decisión de Jose, 15-nov): con 10 trials al día el repo crecería ~4 GB al mes. Instagram solo necesita el
enlace mientras procesa el vídeo, así que se sube al montar la versión y se borra después de publicarla.
La clave sale de SUPABASE_SECRET_KEY (secreto de GitHub o .env) y nunca se imprime.
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import cuenta

BUCKET = "videos"


def _clave() -> str:
    valor = os.environ.get("SUPABASE_SECRET_KEY")
    if not valor and (cuenta.RAIZ / ".env").exists():
        for linea in (cuenta.RAIZ / ".env").read_text(encoding="utf-8").splitlines():
            if linea.startswith("SUPABASE_SECRET_KEY="):
                valor = linea.split("=", 1)[1].strip()
    if not valor:
        raise SystemExit("Falta SUPABASE_SECRET_KEY (secreto de GitHub o .env)")
    return valor


def _pedir(metodo: str, ruta: str, cuerpo: bytes | None, tipo: str, extra: dict | None = None) -> None:
    clave = _clave()
    peticion = urllib.request.Request(f"{cuenta.SUPABASE_URL}/storage/v1/{ruta}", data=cuerpo, method=metodo,
                                      headers={"apikey": clave, "Authorization": f"Bearer {clave}",
                                               "Content-Type": tipo, **(extra or {})})
    try:
        with urllib.request.urlopen(peticion, timeout=300):
            return
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Supabase {metodo} {ruta}: {e.code} {e.read().decode(errors='replace')[:200]}")


def nombre(archivo: str) -> str:
    return f"{cuenta.CARPETA}/{archivo}"


def subir(local: Path, archivo: str) -> None:
    """Sube el vídeo (si ya existe, lo sustituye: sirve para volver a montar una versión)."""
    _pedir("POST", f"object/{BUCKET}/{nombre(archivo)}", local.read_bytes(), "video/mp4", {"x-upsert": "true"})


def borrar(archivo: str) -> None:
    _pedir("DELETE", f"object/{BUCKET}", json.dumps({"prefixes": [nombre(archivo)]}).encode(), "application/json")
