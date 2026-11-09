"""Sincronizar con GitHub desde el panel del PC: traer lo que hizo GitHub Actions y subir lo que cambia Jose."""
import subprocess

from .config import RAIZ

CREDENCIAL = ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
ESPERA_S = 120


class ErrorRepo(Exception):
    pass


def _git(*argumentos: str) -> str:
    try:
        r = subprocess.run(["git", *CREDENCIAL, *argumentos], cwd=RAIZ, capture_output=True,
                           text=True, encoding="utf-8", timeout=ESPERA_S)
    except subprocess.TimeoutExpired:
        raise ErrorRepo(f"git {argumentos[0]} tardó más de {ESPERA_S} s") from None
    if r.returncode != 0:
        raise ErrorRepo(f"git {argumentos[0]} falló: {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout


def sincronizar() -> None:
    """Trae los datos nuevos (mediciones, versiones, publicaciones del autopilot)."""
    _git("pull", "--rebase", "--autostash", "-q")


def guardar(mensaje: str, rutas: list[str]) -> bool:
    """Sube a GitHub los cambios de esas rutas. Devuelve False si no había nada que subir."""
    _git("add", "-A", "--", *rutas)
    if not _git("diff", "--cached", "--name-only", "--", *rutas).strip():
        return False
    _git("commit", "-q", "-m", mensaje, "--", *rutas)
    _git("pull", "--rebase", "--autostash", "-q")
    _git("push", "-q")
    return True
