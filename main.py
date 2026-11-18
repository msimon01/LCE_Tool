"""Start des LCE-Tools in der Konsole: python main.py (aus dem Projektordner).

Die Oberfläche startet mit: streamlit run app.py (bzw. start.bat).
"""

from __future__ import annotations

import sys
from pathlib import Path

from ausgabe.csv_export import schreibe_ergebnisse
from ausgabe.konsole import (zeige_dateien, zeige_einstellungen, zeige_ergebnis, zeige_fehler,
                             zeige_masse, zeige_optimierung, zeige_uebersicht)
from lce.berechnung import berechne, standard_einstellungen
from lce.daten_laden import lade_daten
from lce.masse import masse_je_schicht, masse_je_variante
from lce.oekobilanz import RUNDUNGSREGELN
from lce.optimierung import optimiere, suchbereich_aus_daten
from lce.verlauf import verlauf
from lce.waermeschutz import Berechnungsfehler

PROJEKTORDNER = Path(__file__).resolve().parent
DATENORDNER = PROJEKTORDNER / "daten"
ERGEBNISORDNER = PROJEKTORDNER / "ergebnisse"


def main() -> int:
    # Windows-Konsole: Umlaute und Pfeile sicher ausgeben
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    geladen = lade_daten(DATENORDNER)
    if not geladen.ok:
        zeige_fehler(geladen)
        return 1
    zeige_uebersicht(geladen)

    # Rechenkern
    daten = geladen.daten
    einst = standard_einstellungen(daten)
    ergebnis = berechne(daten, einst)
    try:
        such = suchbereich_aus_daten(daten)
        optimierung, fehlertext = optimiere(daten, einst, such=such), None
    except Berechnungsfehler as e:          # z. B. Parameter für die Optimierung fehlen
        such, optimierung, fehlertext = None, None, str(e)

    # Ausgabe
    traeger = daten["energietraeger.csv"].set_index("id").loc[einst.energietraeger_id, "name"]
    zeige_einstellungen(einst, traeger, RUNDUNGSREGELN[einst.rundung])
    if not ergebnis.schichten.empty:
        zeige_masse(masse_je_schicht(ergebnis.schichten), masse_je_variante(ergebnis.schichten))
    zeige_ergebnis(ergebnis)
    zeige_optimierung(optimierung, such, fehlertext)
    verlauf_df, _ = verlauf(daten, einst, ergebnis=ergebnis)
    zeige_dateien(schreibe_ergebnisse(ergebnis, einst, ERGEBNISORDNER, optimierung, verlauf_df))
    return 1 if ergebnis.fehler else 0


if __name__ == "__main__":
    sys.exit(main())
