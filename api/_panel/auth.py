"""Entrada con contraseña y sesión firmada en una cookie. Si falta la configuración, no deja entrar a nadie."""
import hashlib
import hmac
import time

COOKIE = "mt_sesion"
DURACION_S = 30 * 24 * 3600


def _firma(secreto: str, caduca: int) -> str:
    return hmac.new(secreto.encode(), f"panel|{caduca}".encode(), hashlib.sha256).hexdigest()


def clave_correcta(esperada: str | None, recibida: str) -> bool:
    return bool(esperada) and hmac.compare_digest(esperada.encode(), recibida.encode())


def crear_sesion(secreto: str) -> str:
    caduca = int(time.time()) + DURACION_S
    return f"{caduca}.{_firma(secreto, caduca)}"


def sesion_valida(secreto: str | None, valor: str | None) -> bool:
    if not secreto or not valor:
        return False
    try:
        caduca_txt, firma = valor.split(".", 1)
        caduca = int(caduca_txt)
    except ValueError:
        return False
    return caduca > time.time() and hmac.compare_digest(firma, _firma(secreto, caduca))


def cabecera_cookie(valor: str, segura: bool) -> str:
    extra = "; Secure" if segura else ""
    return f"{COOKIE}={valor}; Path=/; Max-Age={DURACION_S}; HttpOnly; SameSite=Strict{extra}"
