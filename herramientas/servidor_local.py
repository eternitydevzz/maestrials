"""Panel de MaesTrials en el PC: http://localhost:8787

Uso (desde la raíz del proyecto):
  python -I -X utf8 herramientas/servidor_local.py

Sirve el panel (panel/web/), los vídeos (public/v/) y /api/panel con la misma lógica que el resto.
Solo escucha en este ordenador (127.0.0.1), por eso no pide contraseña.
"""
import importlib.util
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "panel" / "web"
VIDEOS = RAIZ / "public" / "v"
PUERTO = 8787

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
        if not self._api("GET"):
            super().do_GET()

    def do_POST(self) -> None:
        if not self._api("POST"):
            self.send_error(404)


if __name__ == "__main__":
    print(f"Panel en http://localhost:{PUERTO}  (Ctrl+C para parar)")
    sys.stdout.flush()
    ThreadingHTTPServer(("127.0.0.1", PUERTO), partial(Local, directory=str(WEB))).serve_forever()
