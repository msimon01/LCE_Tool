"""Start des LCE-Tools: python main.py (aus dem Projektordner)."""

from __future__ import annotations

import sys
from pathlib import Path

from ausgabe.konsole import zeige_fehler, zeige_uebersicht
from lce.daten_laden import lade_daten

PROJEKTORDNER = Path(__file__).resolve().parent
DATENORDNER = PROJEKTORDNER / "daten"


def main() -> int:
    # Windows-Konsole: Umlaute und Pfeile sicher ausgeben
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ergebnis = lade_daten(DATENORDNER)
    if not ergebnis.ok:
        zeige_fehler(ergebnis)
        return 1
    zeige_uebersicht(ergebnis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
