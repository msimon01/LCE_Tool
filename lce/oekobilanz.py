"""Ökobilanz je Schicht (A1–A3, B4, C3, C4, D) und Betrieb B6.

Formeln (Entwicklungsplan Abschnitt 5, Module nach DIN EN 15978 / EN 15804+A2):
    Wert_Modul = m · Kennwert je kg                    [kg CO2e/m²] bzw. [MJ/m²]
    N = T / ND − 1, gerundet nach gewählter Regel      [-]  (N ≥ 0)
    B4 = N · (A1–A3 + C3 + C4)
    D  = m · Kennwert D, nur für den Erstaufbau, immer getrennt ausgewiesen
Betrieb B6 (Heizgradstundenverfahren):
    Q = U · Gt [kWh/(m²a)];  E = Q / Wirkungsgrad
    GWP_B6 = Σ_t E · Emissionsfaktor(t)    (Strom: Faktor aus strom_szenario.csv je Jahr)
    PENRT_B6 = Σ_t E · Primärenergiefaktor_nren · 3,6 MJ/kWh
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lce.einheiten import kwh_in_mj, waermeverlust_kwh_m2a

INDIKATOREN = ("gwp", "penrt")
MODULE_HERSTELLUNG = ("a1a3", "c3", "c4", "d")

# Spaltennamen der Kennwerte in materialien.csv
KENNWERT_SPALTE = {
    ("gwp", "a1a3"): "gwp_a1a3_kg", ("gwp", "c3"): "gwp_c3_kg",
    ("gwp", "c4"): "gwp_c4_kg", ("gwp", "d"): "gwp_d_kg",
    ("penrt", "a1a3"): "penrt_a1a3_mj_kg", ("penrt", "c3"): "penrt_c3_mj_kg",
    ("penrt", "c4"): "penrt_c4_mj_kg", ("penrt", "d"): "penrt_d_mj_kg",
}
EINHEIT = {"gwp": "kg_co2e_m2", "penrt": "mj_m2"}

# Rundungsregeln für die Austauschhäufigkeit
RUNDUNG_AUFRUNDEN = "aufrunden"
RUNDUNG_KAUFMAENNISCH = "kaufmaennisch"
RUNDUNGSREGELN = {
    RUNDUNG_AUFRUNDEN: "Aufrunden",
    RUNDUNG_KAUFMAENNISCH: "Kaufmännisch runden (DIN EN 15978:2026)",
}


def spalte(indikator: str, modul: str) -> str:
    """Ergebnisspalte, z. B. gwp_a1a3_kg_co2e_m2."""
    return f"{indikator}_{modul}_{EINHEIT[indikator]}"


def austausch_anzahl(zeitraum_a: float, nutzungsdauer_a: float, regel: str) -> int:
    """N = T / ND − 1, gerundet; nie negativ.

    aufrunden:     N = ⌈T/ND − 1⌉
    kaufmaennisch: N = ⌊T/ND − 1 + 0,5⌋
    Auf 9 Stellen gerundet, damit z. B. 50/25 − 1 nicht durch Gleitkommarauschen
    zu 1,0000000001 und damit zu 2 Austauschen wird.
    """
    if nutzungsdauer_a <= 0:
        raise ValueError(f"Nutzungsdauer muss größer als 0 sein, ist {nutzungsdauer_a}")
    n_roh = round(zeitraum_a / nutzungsdauer_a - 1.0, 9)
    if regel == RUNDUNG_AUFRUNDEN:
        n = math.ceil(n_roh)
    elif regel == RUNDUNG_KAUFMAENNISCH:
        n = math.floor(n_roh + 0.5)
    else:
        raise ValueError(f"unbekannte Rundungsregel '{regel}'")
    return max(n, 0)


def oekobilanz_schichten(bestandteile: pd.DataFrame, materialien: pd.DataFrame,
                         zeitraum_a: float, regel: str) -> pd.DataFrame:
    """Ergänzt die Massentabelle (je Bestandteil) um Nutzungsdauer, N und alle Module."""
    mat = materialien.set_index("id")
    df = bestandteile.copy()
    df["nutzungsdauer_a"] = df["material"].map(mat["nutzungsdauer_a"]).astype(float)
    df["austausch_n"] = [austausch_anzahl(zeitraum_a, nd, regel) for nd in df["nutzungsdauer_a"]]
    for ind in INDIKATOREN:
        for mod in MODULE_HERSTELLUNG:
            # Wert = m · Kennwert je kg
            df[spalte(ind, mod)] = df["masse_kg_m2"] * df["material"].map(mat[KENNWERT_SPALTE[ind, mod]])
        # B4 = N · (A1–A3 + C3 + C4)
        df[spalte(ind, "b4")] = df["austausch_n"] * (
            df[spalte(ind, "a1a3")] + df[spalte(ind, "c3")] + df[spalte(ind, "c4")])
    return df


def emissionsfaktor_strom(jahr: float, szenario: pd.DataFrame) -> float:
    """Strom-Emissionsfaktor in kg CO2e/kWh für ein Jahr.

    Linear interpoliert zwischen den Stützjahren in strom_szenario.csv,
    vor dem ersten bzw. nach dem letzten Stützjahr konstant.
    """
    s = szenario.sort_values("jahr")
    return float(np.interp(jahr, s["jahr"].astype(float), s["emissionsfaktor_kg_kwh"].astype(float)))


def betrieb_b6(u_w_m2k: float, gt_kkh_a: float, traeger: pd.Series, zeitraum_a: int,
               startjahr: int, szenario: pd.DataFrame) -> dict[str, float]:
    """Betrieb B6 über den Betrachtungszeitraum, je m² Wand.

    Q = U · Gt; E = Q / η; GWP = Σ_t E · EF(t); PENRT = Σ_t E · fp,nren · 3,6.
    """
    q = waermeverlust_kwh_m2a(u_w_m2k, gt_kkh_a)
    e = q / float(traeger["wirkungsgrad"])
    jahre = [startjahr + t for t in range(int(zeitraum_a))]   # t = 1 … T ↔ startjahr … startjahr+T−1
    if int(traeger["strom"]) == 1:
        gwp = sum(e * emissionsfaktor_strom(j, szenario) for j in jahre)
    else:
        gwp = e * float(traeger["emissionsfaktor_kg_kwh"]) * len(jahre)
    penrt = kwh_in_mj(e * float(traeger["primaerenergiefaktor_nren"])) * len(jahre)
    return {"q_kwh_m2a": q, "e_kwh_m2a": e,
            spalte("gwp", "b6"): gwp, spalte("penrt", "b6"): penrt}
