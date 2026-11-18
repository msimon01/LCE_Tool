"""Kumulierter Verlauf von GWP und PENRT über den Betrachtungszeitraum (E04).

Zeitpunkte je Variante:
    0        Herstellung A1–A3 (Erstaufbau)
    1 … T    Betrieb B6 je Jahr; Ersatz B4 im Austauschjahr t = k · ND (k = 1 … N)
    T + 1    Rückbau C3 + C4 (eigener Punkt nach dem letzten Jahr)
Je Austausch fällt A1–A3 + C3 + C4 der Schicht an (wie in B4 = N · (A1–A3 + C3 + C4)),
N ist dieselbe Austauschzahl wie im Ergebnis (gewählte Rundungsregel). B6 im Jahr t:
E · Emissionsfaktor(startjahr + t − 1), bei Strom aus strom_szenario.csv (wie betrieb_b6).
Modul D ist nicht Teil der Kurve. Der letzte Punkt ist gleich der Summe im Ergebnis.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lce.berechnung import Einstellungen, berechne_variante
from lce.einheiten import kwh_in_mj
from lce.oekobilanz import emissionsfaktor_strom, spalte
from lce.waermeschutz import Berechnungsfehler

INDIKATOREN_VERLAUF = ("gwp", "penrt")
EINHEIT_VERLAUF = {"gwp": "kg_co2e_m2", "penrt": "mj_m2"}
ART_HERSTELLUNG, ART_JAHR, ART_RUECKBAU = "Herstellung", "Nutzung", "Rückbau"


def verlauf_spalte(indikator: str, teil: str) -> str:
    """z. B. gwp_konstruktion_kum_kg_co2e_m2 (teil: konstruktion_kum, betrieb_kum, …)."""
    return f"{indikator}_{teil}_{EINHEIT_VERLAUF[indikator]}"


def austauschjahr(k: int, nutzungsdauer_a: float, zeitraum_a: int) -> int:
    """Jahr des k-ten Austauschs: t = k · ND, bei nicht ganzzahliger ND auf das volle
    Jahr aufgerundet und höchstens T."""
    return min(int(math.ceil(round(k * nutzungsdauer_a, 9))), int(zeitraum_a))


def betrieb_je_jahr(e_kwh_m2a: float, traeger: pd.Series, zeitraum_a: int, startjahr: int,
                    szenario: pd.DataFrame) -> pd.DataFrame:
    """B6 je Jahr t = 1 … T: GWP = E · EF(startjahr + t − 1), PENRT = E · fp,nren · 3,6."""
    t = np.arange(1, int(zeitraum_a) + 1)
    kalender = startjahr + t - 1
    if int(traeger["strom"]) == 1:
        ef = np.array([emissionsfaktor_strom(j, szenario) for j in kalender])
    else:
        ef = np.full(len(t), float(traeger["emissionsfaktor_kg_kwh"]))
    return pd.DataFrame({"zeitpunkt": t, "kalenderjahr": kalender,
                         "gwp": e_kwh_m2a * ef,
                         "penrt": kwh_in_mj(e_kwh_m2a * float(traeger["primaerenergiefaktor_nren"]))})


def verlauf_variante(daten: dict[str, pd.DataFrame], einst: Einstellungen, variante: str,
                     dicke_m: float | None = None, z: dict | None = None,
                     schichten: pd.DataFrame | None = None) -> pd.DataFrame:
    """Jährliche und kumulierte Werte einer Variante (Zeilen: Zeitpunkt 0 … T + 1)."""
    if z is None or schichten is None:
        z, schichten, _ = berechne_variante(daten, einst, variante, dicke_m=dicke_m)
    T = int(einst.zeitraum_a)
    zeit = np.arange(0, T + 2)
    df = pd.DataFrame({"variante": variante, "vergleichsmodus": einst.modus_text, "zeitpunkt": zeit,
                       "kalenderjahr": [einst.startjahr - 1 + t if t <= T else einst.startjahr + T - 1
                                        for t in zeit],
                       "art": [ART_HERSTELLUNG if t == 0 else ART_RUECKBAU if t == T + 1 else ART_JAHR
                               for t in zeit]})
    traeger = daten["energietraeger.csv"].set_index("id").loc[einst.energietraeger_id]
    betrieb = betrieb_je_jahr(z["e_kwh_m2a"], traeger, T, einst.startjahr, daten["strom_szenario.csv"])
    for ind in INDIKATOREN_VERLAUF:
        a1a3, c3, c4 = (schichten[spalte(ind, m)] for m in ("a1a3", "c3", "c4"))
        herstellung = np.zeros(len(zeit))
        ersatz = np.zeros(len(zeit))
        rueckbau = np.zeros(len(zeit))
        herstellung[0] = float(a1a3.sum())
        rueckbau[T + 1] = float(c3.sum() + c4.sum())
        # Ersatz: je Austausch A1–A3 + C3 + C4 der Schicht im Austauschjahr
        for i, s in schichten.iterrows():
            for k in range(1, int(s["austausch_n"]) + 1):
                ersatz[austauschjahr(k, s["nutzungsdauer_a"], T)] += a1a3[i] + c3[i] + c4[i]
        b6 = np.zeros(len(zeit))
        b6[1:T + 1] = betrieb[ind].to_numpy()
        df[verlauf_spalte(ind, "herstellung")] = herstellung
        df[verlauf_spalte(ind, "ersatz")] = ersatz
        df[verlauf_spalte(ind, "betrieb")] = b6
        df[verlauf_spalte(ind, "rueckbau")] = rueckbau
        konstruktion = herstellung + ersatz + rueckbau
        df[verlauf_spalte(ind, "konstruktion_kum")] = np.cumsum(konstruktion)
        df[verlauf_spalte(ind, "betrieb_kum")] = np.cumsum(b6)
        df[verlauf_spalte(ind, "summe_kum")] = np.cumsum(konstruktion + b6)
    return df


def verlauf(daten, einst: Einstellungen, varianten: list[str] | None = None,
            ergebnis=None) -> tuple[pd.DataFrame, dict[str, str]]:
    """Verlauf aller (gewählten) Varianten. Rückgabe: (Verlauf, Fehler je Variante)."""
    alle = list(dict.fromkeys(daten["aufbauten.csv"]["variante"]))
    auswahl = [v for v in alle if varianten is None or v in varianten]
    teile, fehler = [], {}
    for v in auswahl:
        try:
            if ergebnis is not None and v in set(ergebnis.varianten["variante"]):
                z = ergebnis.varianten.set_index("variante").loc[v].to_dict()
                sch = ergebnis.schichten[ergebnis.schichten["variante"] == v].reset_index(drop=True)
                teile.append(verlauf_variante(daten, einst, v, z=z, schichten=sch))
            else:
                teile.append(verlauf_variante(daten, einst, v))
        except Berechnungsfehler as e:
            fehler[v] = str(e)
    return (pd.concat(teile, ignore_index=True) if teile else pd.DataFrame()), fehler


def kurve(verlauf_df: pd.DataFrame, indikator: str, mit_betrieb: bool) -> pd.Series:
    """Kumulierte Kurve je Zeile: mit oder ohne Betrieb B6."""
    if mit_betrieb:
        return verlauf_df[verlauf_spalte(indikator, "summe_kum")]
    return verlauf_df[verlauf_spalte(indikator, "konstruktion_kum")]


def schnittpunkte(verlauf_df: pd.DataFrame, indikator: str, mit_betrieb: bool) -> pd.DataFrame:
    """Kreuzungen je Variantenpaar: Zeitpunkt, an dem die Differenz das Vorzeichen wechselt.

    Zwischen zwei Zeitpunkten wird linear interpoliert (B6 wächst innerhalb eines Jahres
    gleichmäßig); liegt der Wechsel zwischen T und T + 1, ist es der Rückbau.
    """
    df = verlauf_df.assign(_wert=kurve(verlauf_df, indikator, mit_betrieb))
    varianten = list(dict.fromkeys(df["variante"]))
    breit = df.pivot(index="zeitpunkt", columns="variante", values="_wert")
    T = int(breit.index.max()) - 1
    zeilen = []
    for i, a in enumerate(varianten):
        for b in varianten[i + 1:]:
            d = (breit[a] - breit[b]).to_numpy()
            t = breit.index.to_numpy()
            vorz_alt = 0
            for j in range(len(d)):
                vorz = int(np.sign(round(d[j], 9)))
                if vorz == 0:
                    continue
                if vorz_alt != 0 and vorz != vorz_alt:
                    # letzter Punkt mit altem Vorzeichen
                    j0 = max(k for k in range(j) if int(np.sign(round(d[k], 9))) == vorz_alt)
                    x = t[j0] + (t[j] - t[j0]) * d[j0] / (d[j0] - d[j])
                    zeilen.append({"variante_a": a, "variante_b": b, "zeitpunkt": float(x),
                                   "beim_rueckbau": bool(x > T),
                                   "vorher_besser": a if vorz_alt < 0 else b,
                                   "nachher_besser": a if vorz < 0 else b})
                vorz_alt = vorz
    return pd.DataFrame(zeilen, columns=["variante_a", "variante_b", "zeitpunkt", "beim_rueckbau",
                                         "vorher_besser", "nachher_besser"])
