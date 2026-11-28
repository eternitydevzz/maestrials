"""Panel de MaesTrials en el PC: un panel por cuenta, cada uno en su puerto.

Uso (desde la raíz del proyecto):
  python -I -X utf8 herramientas/servidor_local.py            → Jose     en http://localhost:8787
  python -I -X utf8 herramientas/servidor_local.py cristian   → Cristian en http://localhost:8788

Sirve el panel (panel/web/), los vídeos (public/v/) y /api/panel con la misma lógica que el resto.
Cada programa solo toca su cuenta: automatico/cuenta.py la fija al arrancar (variable MT_CUENTA).
Solo escucha en este ordenador (127.0.0.1), por eso no pide contraseña.
"""
import importlib.util
import json
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "panel" / "web"
PUERTOS = {"jose": 8787, "cristian": 8788}   # 28-nov (decisión de Jose): un panel por cuenta

NOMBRE = (sys.argv[1] if len(sys.argv) > 1 else "jose").strip().lower()
if NOMBRE not in PUERTOS:
    raise SystemExit(f"Cuenta desconocida: {NOMBRE!r} (valen: {', '.join(PUERTOS)})")
os.environ["MT_CUENTA"] = NOMBRE   # antes de cargar el panel: cuenta.py la lee al importarse
PUERTO = PUERTOS[NOMBRE]

sys.path.insert(0, str(RAIZ / "automatico"))
import cuenta  # noqa: E402  (se para si el token o el id no son de esta cuenta)

VIDEOS = cuenta.VIDEOS
# Lo que la web necesita para la cabecera: qué cuenta es y dónde está el panel de las demás.
INFO_CUENTA = json.dumps({"nombre": NOMBRE, "arroba": cuenta.ARROBA,
                          "otras": [{"nombre": n, "arroba": cuenta.CUENTAS[n]["arroba"], "url": f"http://localhost:{p}/"}
                                    for n, p in PUERTOS.items() if n != NOMBRE]}, ensure_ascii=False).encode("utf-8")

spec = importlib.util.spec_from_file_location("panel", RAIZ / "api" / "panel.py")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


class Local(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")   # siempre la última versión de css/js/datos
        super().end_headers()

    def translate_path(self, path: str) -> str:
        ruta = unquote(urlparse(path).path)
        if ruta.startswith("/v/"):
            nombre = Path(ruta).name                      # solo el nombre: nada de ../
            return str(VIDEOS / nombre)
        return super().translate_path(path)

    def _api(self, metodo: str) -> bool:
        if self.path.startswith("/api/panel"):
            panel.atender(self, metodo, segura=False, local=True)
            return True
        return False

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/cuenta.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(INFO_CUENTA)
            return
        if not self._api("GET"):
            super().do_GET()

    def do_POST(self) -> None:
        if not self._api("POST"):
            self.send_error(404)


if __name__ == "__main__":
    print(f"Panel de {cuenta.ARROBA} en http://localhost:{PUERTO}  (Ctrl+C para parar)")
    sys.stdout.flush()
    ThreadingHTTPServer(("127.0.0.1", PUERTO), partial(Local, directory=str(WEB))).serve_forever()
