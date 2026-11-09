"""Rutas del panel: /api/panel?r=<ruta>. Todo pide sesión menos `entrar`."""
import json
import time
from dataclasses import dataclass

from . import auth, datos
from .config import entorno
from .instagram import ErrorInstagram

ESPERA_CLAVE_MALA_S = 1.0   # frena a quien pruebe contraseñas


@dataclass(frozen=True)
class Respuesta:
    estado: int
    cuerpo: bytes
    cabeceras: tuple[tuple[str, str], ...] = ()


def _json(estado: int, contenido: object, *cabeceras: tuple[str, str]) -> Respuesta:
    return Respuesta(estado, json.dumps(contenido, ensure_ascii=False).encode("utf-8"),
                     (("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store"), *cabeceras))


def _entrar(env: dict[str, str], cuerpo: bytes, segura: bool) -> Respuesta:
    try:
        clave = json.loads(cuerpo or b"{}").get("clave", "")
    except (json.JSONDecodeError, AttributeError):
        clave = ""
    if not isinstance(clave, str) or not env.get("PANEL_SECRET") or not auth.clave_correcta(env.get("PANEL_PASSWORD"), clave):
        time.sleep(ESPERA_CLAVE_MALA_S)
        return _json(401, {"error": "Contraseña incorrecta"})
    sesion = auth.crear_sesion(env["PANEL_SECRET"])
    return _json(200, {"ok": True}, ("Set-Cookie", auth.cabecera_cookie(sesion, segura)))


def responder(metodo: str, ruta: str, cookies: dict[str, str], cuerpo: bytes, segura: bool) -> Respuesta:
    env = entorno()
    if ruta == "entrar" and metodo == "POST":
        return _entrar(env, cuerpo, segura)
    if not auth.sesion_valida(env.get("PANEL_SECRET"), cookies.get(auth.COOKIE)):
        return _json(401, {"error": "Hace falta entrar"})
    try:
        if ruta == "salir" and metodo == "POST":
            return _json(200, {"ok": True}, ("Set-Cookie", f"{auth.COOKIE}=; Path=/; Max-Age=0"))
        if ruta == "ganadores" and metodo == "GET":
            return _json(200, datos.ganadores(env, datos.almacen(env)))
        if ruta == "resultados" and metodo == "GET":
            return _json(200, datos.resultados(env, datos.almacen(env)))
    except ErrorInstagram as e:
        return _json(502, {"error": str(e)})
    return _json(404, {"error": "Esa ruta no existe"})
