"""Robustheit: einzelne Eingangsgrößen nach oben und unten verschieben (one-at-a-time).

Je Größe zwei Rechnungen mit Faktor (1 − s) und (1 + s); s aus parameter.csv
(sensitivitaet_*). Ergebnis je Variante und Kriterium: Abweichung zum Basisfall und
ob sich die Rangfolge der Varianten ändert. Der Ziel-U-Wert bleibt fest, die
Dämmdicke wird also in jedem Fall neu angepasst.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from lce.berechnung import Einstellungen, berechne
from lce.daten_laden import parameter
from lce.waermeschutz import Berechnungsfehler

KRITERIEN_SENS = {"gwp": "gwp_summe_kg_co2e_m2", "penrt": "penrt_summe_mj_m2",
                  "lcc": "lcc_summe_eur_m2"}

# Betriebsanteil je Kriterium (für Auswertungen ohne Betrieb, z. B. Ampel in E05)
BETRIEB_SENS = {"gwp": "gwp_b6_kg_co2e_m2", "penrt": "penrt_b6_mj_m2", "lcc": "lcc_heizung_eur_m2"}

KOSTENSPALTEN = ("kosten_fix_eur_m2", "kosten_je_cm_eur_m2", "abbruch_fix_eur_m2",
                 "abbruch_je_cm_eur_m2")


def _skaliere(daten, datei: str, spalten, faktor: float):
    neu = dict(daten)
    df = daten[datei].copy()
    for s in spalten:
        df[s] = df[s] * faktor
    neu[datei] = df
    return neu


def _kennwertspalten(daten) -> list[str]:
    return [s for s in daten["materialien.csv"].columns
            if (s.startswith("gwp_") or s.startswith("penrt_")) and s.endswith("_kg")
            and not s.startswith("gwp_a1a3_biogen")]


@dataclass(frozen=True)
class Groesse:
    """Eine Eingangsgröße: Name, Parameter für die Spanne und wie sie verändert wird."""

    name: str
    parameter: str
    anwenden: Callable[[dict, Einstellungen, float], tuple[dict, Einstellungen]]


GROESSEN: list[Groesse] = [
    Groesse("Baustoff- und Abbruchkosten", "sensitivitaet_kosten",
            lambda d, e, f: (_skaliere(d, "kosten.csv", KOSTENSPALTEN, f), e)),
    Groesse("Energiepreis", "sensitivitaet_energiepreis",
            lambda d, e, f: (_skaliere(d, "energietraeger.csv", ["preis_eur_kwh"], f), e)),
    Groesse("Zins", "sensitivitaet_wirtschaft",
            lambda d, e, f: (d, e.mit(zins=e.zins * f))),
    Groesse("Preissteigerung Bau", "sensitivitaet_wirtschaft",
            lambda d, e, f: (d, e.mit(preissteigerung_bau=e.preissteigerung_bau * f))),
    Groesse("Preissteigerung Energie", "sensitivitaet_wirtschaft",
            lambda d, e, f: (d, e.mit(preissteigerung_energie=e.preissteigerung_energie * f))),
    Groesse("Nutzungsdauern", "sensitivitaet_nutzungsdauer",
            lambda d, e, f: (_skaliere(d, "materialien.csv", ["nutzungsdauer_a"], f), e)),
    Groesse("GWP-/PENRT-Kennwerte Baustoffe", "sensitivitaet_kennwerte",
            lambda d, e, f: (_skaliere(d, "materialien.csv", _kennwertspalten(d), f), e)),
    Groesse("Emissions- und Primärenergiefaktoren", "sensitivitaet_energiefaktoren",
            lambda d, e, f: (_skaliere(_skaliere(d, "energietraeger.csv",
                                                 ["emissionsfaktor_kg_kwh",
                                                  "primaerenergiefaktor_nren"], f),
                                       "strom_szenario.csv", ["emissionsfaktor_kg_kwh"], f), e)),
    Groesse("Heizgradstunden", "sensitivitaet_heizgradstunden",
            lambda d, e, f: (d, e.mit(heizgradstunden_kkh=e.heizgradstunden_kkh * f))),
]


def spannen_aus_daten(daten) -> dict[str, float]:
    """Parameter → Spanne s (Anteil). Fehlende Parameter → Berechnungsfehler."""
    vorhanden = set(daten["parameter.csv"]["schluessel"])
    benoetigt = list(dict.fromkeys(g.parameter for g in GROESSEN))
    fehlend = [p for p in benoetigt if p not in vorhanden]
    if fehlend:
        raise Berechnungsfehler("parameter.csv: für die Robustheit fehlen " + ", ".join(fehlend))
    spannen = {p: parameter(daten, p) for p in benoetigt}
    for p, s in spannen.items():
        if not 0 <= s < 1:
            raise Berechnungsfehler(f"{p} muss zwischen 0 und 1 liegen, ist {s}")
    return spannen


@dataclass
class Sensitivitaet:
    ergebnis: pd.DataFrame       # je Variante, Größe, Richtung und Kriterium
    rangwechsel: pd.DataFrame    # je Größe, Richtung und Kriterium: Rangfolge geändert?
    basis_rangfolge: dict[str, list[str]]
    fehler: list[str] = field(default_factory=list)


def _rangfolge(var: pd.DataFrame, s: str) -> list[str]:
    return list(var.sort_values(s, kind="stable")["variante"])


def untersuche(daten, einst: Einstellungen, varianten: list[str] | None = None,
               spannen: dict[str, float] | None = None) -> Sensitivitaet:
    spannen = spannen or spannen_aus_daten(daten)
    basis = berechne(daten, einst, varianten).varianten
    if basis.empty:
        return Sensitivitaet(pd.DataFrame(), pd.DataFrame(), {})
    basis_i = basis.set_index("variante")
    basis_rang = {k: _rangfolge(basis, s) for k, s in KRITERIEN_SENS.items()}
    zeilen, wechsel, fehler = [], [], []
    for g in GROESSEN:
        s = spannen[g.parameter]
        for richtung, faktor in (("−", 1.0 - s), ("+", 1.0 + s)):
            d, e = g.anwenden(daten, einst, faktor)
            erg = berechne(d, e, varianten)
            for v, text in erg.fehler.items():
                fehler.append(f"{g.name} {richtung}{s:.0%}: {v}: {text}")
            var = erg.varianten
            if var.empty:
                continue
            for k, sp in KRITERIEN_SENS.items():
                for _, z in var.iterrows():
                    b = float(basis_i.loc[z["variante"], sp])
                    zeilen.append({"variante": z["variante"], "groesse": g.name,
                                   "spanne": s, "richtung": richtung, "kriterium": k,
                                   "basis": b, "wert": float(z[sp]),
                                   "wert_ohne_betrieb": float(z[sp]) - float(z[BETRIEB_SENS[k]]),
                                   "abweichung": float(z[sp]) - b,
                                   "abweichung_anteil": (float(z[sp]) - b) / abs(b) if b else 0.0})
                neu = _rangfolge(var, sp)
                wechsel.append({"groesse": g.name, "richtung": richtung, "spanne": s,
                                "kriterium": k, "rangfolge": " > ".join(neu),
                                "geaendert": neu != [v for v in basis_rang[k] if v in neu]})
    return Sensitivitaet(pd.DataFrame(zeilen), pd.DataFrame(wechsel), basis_rang, fehler)


def hebel(sens: Sensitivitaet, variante: str, kriterium: str) -> pd.DataFrame:
    """Tornado-Daten: je Größe Abweichung bei − und +, sortiert nach größter Spannweite."""
    df = sens.ergebnis
    df = df[(df["variante"] == variante) & (df["kriterium"] == kriterium)]
    if df.empty:
        return pd.DataFrame()
    breit = df.pivot_table(index="groesse", columns="richtung", values="abweichung",
                           aggfunc="first").rename(columns={"−": "minus", "+": "plus"})
    breit["spannweite"] = (breit["plus"] - breit["minus"]).abs()
    spannen = df.drop_duplicates("groesse").set_index("groesse")["spanne"]
    breit["spanne"] = spannen
    return breit.sort_values("spannweite", ascending=False).reset_index()
