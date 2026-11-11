"""MaesTrials — recordatorio de renovar el token "maestrials-cron" (el que usa cron-job.org).

Lo lanza la tarea diaria de preparar como último paso. Desde DIAS_AVISO días antes de la fecha de
`token_cron_caduca` (datos/ajustes.json) termina en error: la ejecución sale en rojo y GitHub avisa por email.
Al renovar el token, poner la nueva fecha de caducidad en datos/ajustes.json.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AJUSTES = RAIZ / "datos" / "ajustes.json"
DIAS_AVISO = 14


def main() -> None:
    caduca_txt = json.loads(AJUSTES.read_text(encoding="utf-8")).get("token_cron_caduca")
    if not caduca_txt:
        raise SystemExit("AVISO: falta token_cron_caduca en datos/ajustes.json")
    caduca = date.fromisoformat(caduca_txt)
    faltan = (caduca - date.today()).days
    if caduca - date.today() <= timedelta(days=DIAS_AVISO):
        raise SystemExit(f"RENUEVA EL TOKEN: maestrials-cron caduca el {caduca:%d-%m-%Y} (faltan {faltan} días). "
                         "GitHub → Fine-grained tokens → maestrials-cron → Regenerate; pegarlo en las 2 tareas de "
                         "cron-job.org (encabezado Authorization) y poner la fecha nueva en datos/ajustes.json.")
    print(f"Token maestrials-cron vigente hasta el {caduca:%d-%m-%Y} (faltan {faltan} días)")


if __name__ == "__main__":
    sys.exit(main())
