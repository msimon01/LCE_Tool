"""CSV-Ausgabe nach ergebnisse/. Nur Darstellung, keine Berechnung.

Format für Excel (deutsch): Trennzeichen ";", Dezimalkomma, UTF-8 mit BOM.
Werte ungerundet (10 signifikante Stellen), Einheiten stehen im Spaltennamen.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

SPALTEN_MASSE = ["variante", "position", "schicht", "material", "anteil",
                 "dicke_m", "rohdichte_kg_m3", "masse_kg_m2"]

# Zahlen mit 10 signifikanten Stellen: praktisch ungerundet, aber ohne
# Gleitkommarauschen wie 12,696000000000002
ZAHLENFORMAT = "%.10g"


def csv_text(df: pd.DataFrame) -> str:
    return df.to_csv(sep=";", decimal=",", index=False, float_format=ZAHLENFORMAT)


def csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV als Bytes (UTF-8 mit BOM), z. B. für einen Download-Knopf."""
    return csv_text(df).encode("utf-8-sig")


def schreibe_csv(df: pd.DataFrame, pfad: Path) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_bytes(csv_bytes(df))
    return pfad


def schreibe_masse_csv(bestandteile: pd.DataFrame, ordner: Path) -> Path:
    """ergebnisse/masse.csv, wird bei jedem Lauf überschrieben."""
    return schreibe_csv(bestandteile[SPALTEN_MASSE], Path(ordner) / "masse.csv")


def einstellungen_tabelle(einst) -> pd.DataFrame:
    return pd.DataFrame({"schluessel": list(asdict(einst)), "wert": list(asdict(einst).values())})


def aufbauten_als_daten_csv(aufbauten: pd.DataFrame) -> bytes:
    """Aufbauten im Format von daten/ (Trennzeichen ";", Dezimalpunkt, UTF-8 ohne BOM),
    damit sie sich in daten/aufbauten.csv übernehmen lassen."""
    return aufbauten.to_csv(sep=";", decimal=".", index=False).encode("utf-8")


def ergebnis_dateien(ergebnis, einst, optimierung=None, verlauf=None) -> dict[str, pd.DataFrame]:
    """Alle Ergebnistabellen mit Dateinamen (optimierung: Ergebnis von lce.optimierung)."""
    dateien = {
        "varianten.csv": ergebnis.varianten,
        "schichten.csv": ergebnis.schichten,
        "einstellungen.csv": einstellungen_tabelle(einst),
    }
    if not ergebnis.schichten.empty:
        dateien["masse.csv"] = ergebnis.schichten[SPALTEN_MASSE]
    if optimierung is not None and not optimierung.optima.empty:
        dateien["optimum.csv"] = optimierung.optima
        dateien["optimum_verlauf.csv"] = optimierung.verlauf
    if verlauf is not None and not verlauf.empty:
        dateien["verlauf.csv"] = verlauf          # eine Zeile je Variante und Jahr (E04)
    return dateien


def schreibe_ergebnisse(ergebnis, einst, ordner: Path, optimierung=None, verlauf=None) -> list[Path]:
    """Schreibt alle Ergebnis-CSV nach `ordner` (bei jedem Lauf überschrieben)."""
    return [schreibe_csv(df, Path(ordner) / name)
            for name, df in ergebnis_dateien(ergebnis, einst, optimierung, verlauf).items()]
