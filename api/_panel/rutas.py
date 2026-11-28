"""Rutas del panel: /api/panel?r=<ruta>.

- En el PC (servidor_local, solo escucha en este ordenador) no pide contraseña y permite las acciones.
- Fuera del PC pide sesión y solo deja leer.
"""
import json
import time
from dataclasses import dataclass

from . import auth, datos
from .config import entorno
from .instagram import ErrorInstagram

ESPERA_CLAVE_MALA_S = 1.0   # frena a quien pruebe contraseñas
SOLO_PC = {"versiones", "estado", "sincronizar", "publicar", "descartar", "editar", "rehacer", "autopilot", "anadir"}
LECTURAS_PC = {"versiones", "estado"}   # rutas del PC que se piden con GET (no cambian nada)


@dataclass(frozen=True)
class Respuesta:
    estado: int
    cuerpo: bytes
    cabeceras: tuple[tuple[str, str], ...] = ()


def _json(estado: int, contenido: object, *cabeceras: tuple[str, str]) -> Respuesta:
    return Respuesta(estado, json.dumps(contenido, ensure_ascii=False).encode("utf-8"),
                     (("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store"), *cabeceras))


def _cuerpo(cuerpo: bytes) -> dict:
    try:
        datos_json = json.loads(cuerpo or b"{}")
    except json.JSONDecodeError:
        return {}
    return datos_json if isinstance(datos_json, dict) else {}


def _texto(peticion: dict, campo: str) -> str:
    valor = peticion.get(campo, "")
    return valor if isinstance(valor, str) else ""


def _entrar(env: dict[str, str], cuerpo: bytes, segura: bool) -> Respuesta:
    clave = _texto(_cuerpo(cuerpo), "clave")
    if not env.get("PANEL_SECRET") or not auth.clave_correcta(env.get("PANEL_PASSWORD"), clave):
        time.sleep(ESPERA_CLAVE_MALA_S)
        return _json(401, {"error": "Contraseña incorrecta"})
    sesion = auth.crear_sesion(env["PANEL_SECRET"])
    return _json(200, {"ok": True}, ("Set-Cookie", auth.cabecera_cookie(sesion, segura)))


def _accion_pc(ruta: str, cuerpo: bytes) -> Respuesta:
    from . import acciones, repo   # solo en el PC: importa fase3 y automatico
    try:
        return _json(200, _accion(acciones, ruta, _cuerpo(cuerpo)))
    except acciones.ErrorAccion as e:
        return _json(400, {"error": str(e)})
    except repo.ErrorRepo as e:
        return _json(500, {"error": f"No se pudo sincronizar con GitHub: {e}"})


def _accion(acciones: object, ruta: str, peticion: dict) -> object:
    archivo = _texto(peticion, "archivo")
    if ruta == "versiones":
        return acciones.versiones()
    if ruta == "estado":
        return acciones.estado()
    if ruta == "sincronizar":
        acciones.repo.sincronizar()
        return {"ok": True}
    if ruta == "publicar":
        return acciones.publicar_ahora(archivo)
    if ruta == "descartar":
        acciones.descartar(archivo)
        return {"ok": True}
    if ruta == "editar":
        return acciones.editar(archivo, _texto(peticion, "gancho"), _texto(peticion, "pie"))
    if ruta == "rehacer":
        acciones.rehacer(archivo)
        return {"ok": True}
    if ruta == "autopilot":
        return acciones.cambiar_autopilot(peticion.get("encendido") is True)
    return acciones.anadir_ganador(_texto(peticion, "enlace"))


def responder(metodo: str, ruta: str, cookies: dict[str, str], cuerpo: bytes, segura: bool,
              local: bool = False) -> Respuesta:
    env = entorno()
    if ruta == "entrar" and metodo == "POST":
        return _entrar(env, cuerpo, segura)
    if not local and not auth.sesion_valida(env.get("PANEL_SECRET"), cookies.get(auth.COOKIE)):
        return _json(401, {"error": "Hace falta entrar"})
    if ruta in SOLO_PC and not local:
        return _json(403, {"error": "Esta acción solo funciona en el panel del PC"})
    try:
        if ruta == "salir" and metodo == "POST":
            return _json(200, {"ok": True}, ("Set-Cookie", f"{auth.COOKIE}=; Path=/; Max-Age=0"))
        if ruta == "ganadores" and metodo == "GET":
            return _json(200, datos.ganadores(env, datos.almacen(env)))
        if ruta == "resultados" and metodo == "GET":
            return _json(200, datos.resultados(env, datos.almacen(env)))
        if ruta in SOLO_PC and (metodo == "POST" or ruta in LECTURAS_PC):
            return _accion_pc(ruta, cuerpo)
    except ErrorInstagram as e:
        return _json(502, {"error": str(e)})
    return _json(404, {"error": "Esa ruta no existe"})
