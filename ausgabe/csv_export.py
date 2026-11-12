"""CSV-Ausgabe nach ergebnisse/. Nur Darstellung, keine Berechnung.

Format für Excel (deutsch): Trennzeichen ";", Dezimalkomma, UTF-8 mit BOM.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SPALTEN_MASSE = ["variante", "position", "schicht", "material", "anteil",
                 "dicke_m", "rohdichte_kg_m3", "masse_kg_m2"]

# Zahlen mit 10 signifikanten Stellen: praktisch ungerundet, aber ohne
# Gleitkommarauschen wie 12,696000000000002
ZAHLENFORMAT = "%.10g"


def schreibe_csv(df: pd.DataFrame, pfad: Path) -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(pfad, sep=";", decimal=",", encoding="utf-8-sig", index=False,
              float_format=ZAHLENFORMAT)
    return pfad


def schreibe_masse_csv(bestandteile: pd.DataFrame, ordner: Path) -> Path:
    """ergebnisse/masse.csv, wird bei jedem Lauf überschrieben."""
    return schreibe_csv(bestandteile[SPALTEN_MASSE], Path(ordner) / "masse.csv")
