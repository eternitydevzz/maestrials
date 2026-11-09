"""Función de Vercel del panel. También la usa herramientas/servidor_local.py para probar en el PC."""
import sys
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _panel.rutas import responder  # noqa: E402

MAX_CUERPO = 1_000_000


def atender(peticion: BaseHTTPRequestHandler, metodo: str, segura: bool, local: bool = False) -> None:
    ruta = parse_qs(urlparse(peticion.path).query).get("r", [""])[0]
    try:
        cookies = {k: m.value for k, m in SimpleCookie(peticion.headers.get("Cookie", "")).items()}
    except CookieError:
        cookies = {}
    largo = min(int(peticion.headers.get("Content-Length") or 0), MAX_CUERPO)
    cuerpo = peticion.rfile.read(largo) if largo else b""
    respuesta = responder(metodo, ruta, cookies, cuerpo, segura, local=local)
    peticion.send_response(respuesta.estado)
    for clave, valor in respuesta.cabeceras:
        peticion.send_header(clave, valor)
    peticion.end_headers()
    peticion.wfile.write(respuesta.cuerpo)


class handler(BaseHTTPRequestHandler):  # Vercel busca una clase con este nombre exacto
    def do_GET(self) -> None:
        atender(self, "GET", segura=True)

    def do_POST(self) -> None:
        atender(self, "POST", segura=True)
