"""Lebenszykluskosten als Barwert je m² Wand.

Formeln (Entwicklungsplan Abschnitt 5, Zins und Preissteigerung nach BNB 2.1.1 Anlage 4):
    BWF(t) = ((1 + p) / (1 + i))^t
    K_H = Anteil · (kosten_fix + kosten_je_cm · d_cm)          Herstellung je Schicht
    K_A = Anteil · (abbruch_fix + abbruch_je_cm · d_cm)        Abbruch je Schicht
    Herstellung = Σ K_H                                         (t = 0, nicht abgezinst)
    Ersatz      = Σ_k (K_H + K_A) · BWF_bau(k · ND),  k = 1 … N
    Rückbau     = Σ K_A · BWF_bau(T)
    Heizung     = Σ_t E · Preis · BWF_energie(t),  t = 1 … T
Die Kostenwerte in kosten.csv gelten je cm Schichtdicke bei 100 % Anteil.
"""

from __future__ import annotations

import pandas as pd

from lce.daten_laden import STATUS_GESCHAETZT
from lce.einheiten import m_in_cm

SPALTEN_LCC = ("lcc_herstellung_eur_m2", "lcc_ersatz_eur_m2", "lcc_rueckbau_eur_m2")


def barwertfaktor(t: float, preissteigerung: float, zins: float) -> float:
    """BWF(t) = ((1 + p) / (1 + i))^t."""
    return ((1.0 + preissteigerung) / (1.0 + zins)) ** t


def kosten_schichten(oeko: pd.DataFrame, kosten: pd.DataFrame, zeitraum_a: float,
                     zins: float, preissteigerung_bau: float) -> pd.DataFrame:
    """Ergänzt die Schichttabelle (mit austausch_n, nutzungsdauer_a) um Kosten.

    Material ohne Eintrag in kosten.csv: Kosten = leer (NaN), kosten_fehlen = True.
    """
    k = kosten.set_index("material_id")
    df = oeko.copy()
    kh, ka, ersatz, rueckbau, fehlen, geschaetzt = [], [], [], [], [], []
    for _, z in df.iterrows():
        mat = z["material"]
        if mat not in k.index:
            kh.append(float("nan")); ka.append(float("nan"))
            ersatz.append(float("nan")); rueckbau.append(float("nan"))
            fehlen.append(True); geschaetzt.append(False)
            continue
        d_cm = m_in_cm(z["dicke_m"])
        r = k.loc[mat]
        k_h = z["anteil"] * (r["kosten_fix_eur_m2"] + r["kosten_je_cm_eur_m2"] * d_cm)
        k_a = z["anteil"] * (r["abbruch_fix_eur_m2"] + r["abbruch_je_cm_eur_m2"] * d_cm)
        kh.append(k_h)
        ka.append(k_a)
        ersatz.append(sum((k_h + k_a) * barwertfaktor(n * z["nutzungsdauer_a"], preissteigerung_bau, zins)
                          for n in range(1, int(z["austausch_n"]) + 1)))
        rueckbau.append(k_a * barwertfaktor(zeitraum_a, preissteigerung_bau, zins))
        fehlen.append(False)
        geschaetzt.append(STATUS_GESCHAETZT in str(r["status"]).lower())
    df["k_herstellung_eur_m2"] = kh
    df["k_abbruch_eur_m2"] = ka
    df["lcc_herstellung_eur_m2"] = kh
    df["lcc_ersatz_eur_m2"] = ersatz
    df["lcc_rueckbau_eur_m2"] = rueckbau
    df["kosten_fehlen"] = fehlen
    df["kosten_geschaetzt"] = geschaetzt
    return df


def heizkosten(e_kwh_m2a: float, preis_eur_kwh: float, zeitraum_a: int,
               zins: float, preissteigerung_energie: float) -> float:
    """Heizung = Σ_{t=1..T} E · Preis · BWF_energie(t)  [€/m²]."""
    return sum(e_kwh_m2a * preis_eur_kwh * barwertfaktor(t, preissteigerung_energie, zins)
               for t in range(1, int(zeitraum_a) + 1))
