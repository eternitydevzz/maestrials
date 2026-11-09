"""Variables de entorno: en Vercel vienen de su panel; en el PC, de .env."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CLAVES = ("IG_TOKEN", "IG_USER_ID", "GRAPH_BASE", "ANTHROPIC_API_KEY", "PANEL_PASSWORD", "PANEL_SECRET",
          "DATABASE_URL", "BLOB_READ_WRITE_TOKEN")


def entorno() -> dict[str, str]:
    valores: dict[str, str] = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    valores.update({k: v for k, v in os.environ.items() if k in CLAVES and v})
    return valores
