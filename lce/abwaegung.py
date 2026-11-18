"""Zielkonflikt Ökologie gegen Kosten (E05): nicht übertroffene Varianten und Robustheits-Ampel.

Eine Variante ist „übertroffen“, wenn eine andere in beiden Größen (x = GWP oder PENRT,
y = Lebenszykluskosten; kleiner = besser) mindestens gleich gut und in mindestens einer
besser ist. Varianten mit genau gleichen Werten übertreffen sich nicht gegenseitig.

Ampel je Variante aus der Robustheitsprüfung (lce.sensitivitaet): geprüft wird jeder Fall,
in dem eine Annahme auf ihren unteren oder oberen Wert gesetzt ist.
    grün: in allen Fällen nicht übertroffen
    gelb: nur in einem Teil der Fälle nicht übertroffen
    rot:  in keinem Fall nicht übertroffen
Die Rechenergebnisse selbst werden nicht verändert.
"""

from __future__ import annotations

import pandas as pd

from lce.sensitivitaet import BETRIEB_SENS, KRITERIEN_SENS, Sensitivitaet

GRUEN, GELB, ROT = "grün", "gelb", "rot"

# Toleranz für „gleich gut“ (Gleitkommarauschen), relativ zum Betrag
GLEICH_TOLERANZ = 1e-9


def _besser_gleich(a: float, b: float) -> bool:
    return a <= b + GLEICH_TOLERANZ * max(1.0, abs(b))


def _besser(a: float, b: float) -> bool:
    return a < b - GLEICH_TOLERANZ * max(1.0, abs(b))


def uebertroffen_von(df: pd.DataFrame, x: str, y: str) -> dict[str, list[str]]:
    """Variante → Liste der Varianten, die sie übertreffen (leer = nicht übertroffen)."""
    ergebnis: dict[str, list[str]] = {}
    for _, a in df.iterrows():
        von = []
        for _, b in df.iterrows():
            if b["variante"] == a["variante"]:
                continue
            if (_besser_gleich(b[x], a[x]) and _besser_gleich(b[y], a[y])
                    and (_besser(b[x], a[x]) or _besser(b[y], a[y]))):
                von.append(b["variante"])
        ergebnis[a["variante"]] = von
    return ergebnis


def nicht_uebertroffen(df: pd.DataFrame, x: str, y: str) -> pd.Series:
    """True je Variante (Index = variante), wenn sie von keiner anderen übertroffen wird."""
    von = uebertroffen_von(df, x, y)
    return pd.Series({v: not liste for v, liste in von.items()}, name="nicht_uebertroffen")


def punktwolke(varianten: pd.DataFrame, oeko: str, mit_betrieb: bool) -> pd.DataFrame:
    """x = GWP oder PENRT, y = Lebenszykluskosten, mit oder ohne Betrieb; plus Kennzeichnung."""
    sx, sy = KRITERIEN_SENS[oeko], KRITERIEN_SENS["lcc"]
    df = pd.DataFrame({"variante": varianten["variante"],
                       "x": varianten[sx] - (0 if mit_betrieb else varianten[BETRIEB_SENS[oeko]]),
                       "y": varianten[sy] - (0 if mit_betrieb else varianten[BETRIEB_SENS["lcc"]])})
    von = uebertroffen_von(df, "x", "y")
    df["nicht_uebertroffen"] = df["variante"].map(lambda v: not von[v])
    df["uebertroffen_von"] = df["variante"].map(lambda v: ", ".join(von[v]))
    return df


def ampel(sens: Sensitivitaet, oeko: str, mit_betrieb: bool) -> pd.DataFrame:
    """Ampel je Variante aus allen Robustheitsfällen (je Annahme unterer und oberer Wert).

    Spalten: variante, ampel, faelle, nicht_uebertroffen_in, kipp_faelle (Text der Fälle,
    in denen die Variante übertroffen wird, mit der übertreffenden Variante).
    """
    e = sens.ergebnis
    wert = "wert" if mit_betrieb else "wert_ohne_betrieb"
    breit = e[e["kriterium"].isin([oeko, "lcc"])].pivot_table(
        index=["groesse", "richtung", "spanne", "variante"], columns="kriterium", values=wert,
        aggfunc="first").reset_index()
    zaehler: dict[str, int] = {}
    kipp: dict[str, list[str]] = {}
    faelle = 0
    for (g, r, s), fall in breit.groupby(["groesse", "richtung", "spanne"], sort=False):
        faelle += 1
        von = uebertroffen_von(fall, oeko, "lcc")
        for v, liste in von.items():
            zaehler.setdefault(v, 0)
            kipp.setdefault(v, [])
            if liste:
                kipp[v].append(f"{g} {r}{s:.0%} (übertroffen von {', '.join(liste)})")
            else:
                zaehler[v] += 1
    zeilen = []
    for v, n in zaehler.items():
        farbe = GRUEN if n == faelle else ROT if n == 0 else GELB
        zeilen.append({"variante": v, "ampel": farbe, "faelle": faelle,
                       "nicht_uebertroffen_in": n, "kipp_faelle": kipp[v]})
    return pd.DataFrame(zeilen)
