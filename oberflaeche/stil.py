"""Farben und kleine Darstellungsbausteine der Oberfläche (keine Fachwerte)."""

from __future__ import annotations

import streamlit as st

AKZENT = "#3DD6B5"
GRAU = "#8B96A5"

# Eine feste Farbe je Variante (Reihenfolge wie in aufbauten.csv), überall gleich
# (ohne Orange, das ist für den Betrieb B6 reserviert)
VARIANTENFARBEN = ["#3DD6B5", "#5B9BF0", "#E86A92", "#A78BFA", "#9BD35A", "#4FC3F7",
                   "#F06292", "#B0BEC5"]

# Lebenszyklusmodule: Konstruktion in Blautönen, Betrieb orange
MODULFARBEN = {"a1a3": "#4F7CAC", "b4": "#7FA3C9", "c3": "#A9C4E0", "c4": "#D3E2F0",
               "b6": "#F2A541"}
LCC_FARBEN = {"lcc_herstellung_eur_m2": "#4F7CAC", "lcc_ersatz_eur_m2": "#7FA3C9",
              "lcc_rueckbau_eur_m2": "#A9C4E0", "lcc_heizung_eur_m2": "#F2A541"}

# Optimum-Diagramm wie Folie: Konstruktion grau, Betrieb orange, Summe Akzent
OPTIMUM_FARBEN = {"konstruktion": "#8B96A5", "betrieb": "#F2A541", "summe": AKZENT}

# Wandschnitt: Farbe nach Kategorie in materialien.csv
KATEGORIEFARBEN = {"Beton": "#8B949E", "Mauerwerk": "#C2703D", "Dämmstoff": "#F2D16B",
                   "Holz": "#B5835A", "Platte": "#E6E1D6", "Putz": "#CFC8BA",
                   "Metall": "#6E7781", "Folie": "#5B9BF0", "Luft": "#2D3540"}
ERSATZFARBEN = ["#9BD35A", "#E86A92", "#A78BFA", "#4FC3F7"]
MISCHFARBE = "#D9B26A"          # inhomogene Schicht aus mehreren Kategorien


def variantenfarben(varianten: list[str]) -> dict[str, str]:
    return {v: VARIANTENFARBEN[i % len(VARIANTENFARBEN)] for i, v in enumerate(varianten)}


def kategoriefarbe(kategorie: str, bekannt: dict[str, str]) -> str:
    if kategorie in KATEGORIEFARBEN:
        return KATEGORIEFARBEN[kategorie]
    if kategorie not in bekannt:
        bekannt[kategorie] = ERSATZFARBEN[len(bekannt) % len(ERSATZFARBEN)]
    return bekannt[kategorie]


def css() -> None:
    """Feinschliff, den das Theme nicht abdeckt."""
    st.markdown("""
<style>
.block-container {padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetricValue"] {font-size: 1.7rem; font-weight: 600;}
[data-testid="stMetricLabel"] p {font-size: 0.78rem; color: #8B96A5;}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; line-height: 1.2;}
[data-testid="stMetricLabel"] {min-height: 2.1rem; align-items: flex-start;}
h1 {font-size: 1.7rem !important; font-weight: 700 !important;}
h3 {font-size: 1.05rem !important; font-weight: 600 !important; color: #C9D1D9;}
.lce-kopf {display:flex; align-items:center; gap:.55rem; font-weight:600; font-size:1.02rem;}
.lce-punkt {width:.75rem; height:.75rem; border-radius:50%; display:inline-block;}
.lce-chip {display:inline-block; padding:.12rem .5rem; border-radius:1rem; font-size:.72rem;
           background:#1F2833; color:#8B96A5; margin-right:.3rem;}
.lce-chip-gut {background:rgba(61,214,181,.15); color:#3DD6B5;}
.lce-unter {color:#8B96A5; font-size:.85rem; margin-top:-.4rem;}
/* Handy (E07): weniger Rand, kleinere Schrift, nichts breiter als der Bildschirm */
@media (max-width: 640px) {
  .block-container {padding: 3rem .75rem 2rem .75rem;}
  h1 {font-size: 1.3rem !important;}
  [data-testid="stMetricValue"] {font-size: 1.35rem;}
  [data-testid="stMetricLabel"] {min-height: 0;}
  .lce-kopf {font-size: .95rem;}
  .lce-chip {white-space: normal;}
  .block-container, .block-container * {max-width: 100%;}
  [data-testid="stHorizontalBlock"] {flex-wrap: wrap;}
}
</style>""", unsafe_allow_html=True)


def kopf(titel: str, unterzeile: str = "") -> None:
    st.markdown(f"# {titel}")
    if unterzeile:
        st.markdown(f"<div class='lce-unter'>{unterzeile}</div>", unsafe_allow_html=True)


def varianten_titel(name: str, farbe: str, chips: list[tuple[str, bool]] = ()) -> None:
    chip_html = "".join(f"<span class='lce-chip{' lce-chip-gut' if gut else ''}'>{t}</span>"
                        for t, gut in chips)
    st.markdown(f"<div class='lce-kopf'><span class='lce-punkt' style='background:{farbe}'></span>"
                f"{name}</div><div style='margin:.25rem 0 .2rem'>{chip_html}</div>",
                unsafe_allow_html=True)


def rangliste_html(rang, spalte: str, farben: dict[str, str], einheit: str,
                   absteigend: bool = False) -> str:
    """Rangliste mit Balken (Länge relativ zum größten Wert), beste Variante oben."""
    rang = rang.sort_values(spalte, ascending=not absteigend).reset_index(drop=True)
    groesster = max(float(rang[spalte].abs().max()), 1e-12)
    zeilen = []
    for i, z in rang.iterrows():
        anteil = abs(float(z[spalte])) / groesster
        farbe = farben.get(z["variante"], AKZENT)
        zeilen.append(
            f"<div style='margin:.2rem 0 .85rem'>"
            f"<div style='display:flex;justify-content:space-between;font-size:.88rem'>"
            f"<span><b style='color:#8B96A5;margin-right:.45rem'>{i + 1}</b>{z['variante']}</span>"
            f"<span style='font-variant-numeric:tabular-nums'>{z[spalte]:,.0f}</span></div>"
            f"<div style='height:.42rem;background:#1F2833;border-radius:.3rem;margin-top:.3rem'>"
            f"<div style='width:{anteil * 100:.1f}%;height:100%;background:{farbe};"
            f"border-radius:.3rem'></div></div></div>")
    return ("".join(zeilen).replace(",", " ")
            + f"<div class='lce-unter' style='margin-top:0'>Einheit: {einheit}</div>")

# Ampel der Robustheit (E05)
AMPELFARBEN = {"grün": "#3FB950", "gelb": "#E3B341", "rot": "#F85149"}
AMPEL_SYMBOL = {"grün": "🟢", "gelb": "🟡", "rot": "🔴"}
