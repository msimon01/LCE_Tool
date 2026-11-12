"""Start des LCE-Tools: python main.py (aus dem Projektordner)."""

from __future__ import annotations

import sys
from pathlib import Path

from ausgabe.csv_export import schreibe_masse_csv
from ausgabe.konsole import zeige_datei, zeige_fehler, zeige_masse, zeige_uebersicht
from lce.daten_laden import lade_daten
from lce.masse import masse_je_bestandteil, masse_je_schicht, masse_je_variante

PROJEKTORDNER = Path(__file__).resolve().parent
DATENORDNER = PROJEKTORDNER / "daten"
ERGEBNISORDNER = PROJEKTORDNER / "ergebnisse"


def main() -> int:
    # Windows-Konsole: Umlaute und Pfeile sicher ausgeben
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ergebnis = lade_daten(DATENORDNER)
    if not ergebnis.ok:
        zeige_fehler(ergebnis)
        return 1
    zeige_uebersicht(ergebnis)

    # Rechenkern
    daten = ergebnis.daten
    bestandteile = masse_je_bestandteil(daten["aufbauten.csv"], daten["materialien.csv"])

    # Ausgabe
    zeige_masse(masse_je_schicht(bestandteile), masse_je_variante(bestandteile))
    zeige_datei(schreibe_masse_csv(bestandteile, ERGEBNISORDNER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
