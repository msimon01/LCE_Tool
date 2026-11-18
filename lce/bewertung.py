"""Gewichtete Gesamtbewertung der Varianten.

Je Kriterium (kleiner = besser) Punkte relativ zur besten Variante:
    Punkte_k = 100 · (1 − (Wert − Bester) / |Bester|),  nicht kleiner als 0
    → beste Variante 100 Punkte, eine um 20 % schlechtere 80 Punkte.
Gesamt = Σ (Gewicht_k · Punkte_k) / Σ Gewicht_k
Gewichte: parameter.csv (bewertung_gewicht_*), in der Oberfläche änderbar.
"""

from __future__ import annotations

import pandas as pd

from lce.daten_laden import parameter
from lce.waermeschutz import Berechnungsfehler

# Kriterium → Spalte im Variantenergebnis
KRITERIEN_BEWERTUNG = {"gwp": "gwp_summe_kg_co2e_m2", "penrt": "penrt_summe_mj_m2",
                       "lcc": "lcc_summe_eur_m2"}
BEWERTUNG_PARAMETER = {k: f"bewertung_gewicht_{k}" for k in KRITERIEN_BEWERTUNG}
PUNKTE_MAX = 100.0


def gewichte_aus_daten(daten: dict[str, pd.DataFrame]) -> dict[str, float]:
    vorhanden = set(daten["parameter.csv"]["schluessel"])
    fehlend = [s for s in BEWERTUNG_PARAMETER.values() if s not in vorhanden]
    if fehlend:
        raise Berechnungsfehler("parameter.csv: für die Gesamtbewertung fehlen " + ", ".join(fehlend))
    return {k: parameter(daten, s) for k, s in BEWERTUNG_PARAMETER.items()}


def punkte(werte: pd.Series) -> pd.Series:
    """Punkte relativ zur besten (kleinsten) Variante, 0 … 100."""
    bester = float(werte.min())
    if bester == 0:
        return werte.map(lambda w: PUNKTE_MAX if w == 0 else 0.0)
    return (PUNKTE_MAX * (1.0 - (werte - bester) / abs(bester))).clip(lower=0.0)


def bewerte(varianten: pd.DataFrame, gewichte: dict[str, float]) -> pd.DataFrame:
    """Punkte je Kriterium, Gesamtpunkte und Rang (1 = beste) je Variante."""
    if any(g < 0 for g in gewichte.values()):
        raise Berechnungsfehler("Gewichte dürfen nicht negativ sein")
    summe_g = sum(gewichte.values())
    if summe_g <= 0:
        raise Berechnungsfehler("mindestens ein Gewicht muss größer als 0 sein")
    df = pd.DataFrame({"variante": varianten["variante"]})
    for k, s in KRITERIEN_BEWERTUNG.items():
        df[f"punkte_{k}"] = punkte(varianten[s]).to_numpy()
    df["punkte_gesamt"] = sum(gewichte[k] * df[f"punkte_{k}"] for k in KRITERIEN_BEWERTUNG) / summe_g
    df["rang"] = df["punkte_gesamt"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("rang").reset_index(drop=True)
