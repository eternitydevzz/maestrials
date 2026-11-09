"""Servidor para probar el panel en el PC: http://localhost:8787

Uso (desde la raíz del proyecto):
  python -I -X utf8 herramientas/servidor_local.py

Sirve public/ y manda /api/panel a la misma lógica que usa Vercel. Solo escucha en este PC.
"""
import importlib.util
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUERTO = 8787

spec = importlib.util.spec_from_file_location("panel", RAIZ / "api" / "panel.py")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


class Local(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")   # en pruebas, siempre la última versión de css/js
        super().end_headers()

    def _api(self, metodo: str) -> bool:
        if self.path.startswith("/api/panel"):
            panel.atender(self, metodo, segura=False)
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
    ThreadingHTTPServer(("127.0.0.1", PUERTO), partial(Local, directory=str(RAIZ / "public"))).serve_forever()
