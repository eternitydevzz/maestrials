"""MaesTrials — recalcula la lista de ganadores si tiene más de DIAS_VALIDEZ días.

Lo lanza la tarea diaria de preparar (antes de preparar), así no hace falta otro horario.
Uso (desde la raíz del proyecto):
  python -I -X utf8 automatico/ganadores_si_toca.py           # solo si toca
  python -I -X utf8 automatico/ganadores_si_toca.py --ya      # recalcula ahora
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "fase2"))
import ganadores  # noqa: E402

DIAS_VALIDEZ = 7


def toca(ahora: datetime) -> bool:
    if not ganadores.SALIDA.exists():
        return True
    generado = json.loads(ganadores.SALIDA.read_text(encoding="utf-8")).get("generado_en")
    return generado is None or ahora - datetime.fromisoformat(generado) >= timedelta(days=DIAS_VALIDEZ)


def main() -> None:
    if "--ya" in sys.argv[1:] or toca(datetime.now(timezone.utc)):
        print("Recalculando ganadores (la lista tiene más de 7 días o no tiene fecha)…")
        ganadores.main()
    else:
        print("La lista de ganadores tiene menos de 7 días: no se recalcula")


if __name__ == "__main__":
    main()
