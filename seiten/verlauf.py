"""Seite Verlauf über die Zeit (E04): Wann entstehen die Emissionen?"""

from __future__ import annotations

import streamlit as st

from ausgabe.beschriftung import GWP, PENRT
from lce.oekobilanz import RUNDUNGSREGELN, spalte
from lce.verlauf import kurve, schnittpunkte
from oberflaeche.diagramme import kumuliert
from oberflaeche.stil import kopf, varianten_titel
from oberflaeche.zustand import betrieb_schalter, fehler_in_aufbauten_hinweis, kontext

INDIKATOREN = {"gwp": ("GWP", GWP), "penrt": ("PENRT", PENRT)}

k = kontext()
kopf(f"Verlauf über die Zeit · {k.einst.modus_text}", "Kumuliert von der Herstellung (Bau) über Ersatz und Betrieb bis "
                              "zum Rückbau – wann entstehen die Unterschiede?")
if fehler_in_aufbauten_hinweis():
    st.stop()
verlauf_df, fehler = k.verlauf()
for v, text in {**k.ergebnis.fehler, **fehler}.items():
    st.error(f"**{v}**: {text}")
if verlauf_df.empty:
    st.info("Keine Variante berechnet.")
    st.stop()

st.write("")
kopfzeile = st.columns([3, 2])
ind = kopfzeile[0].segmented_control(
    "Indikator", options=list(INDIKATOREN), default="gwp", key="indikator_verlauf",
    format_func=lambda i: INDIKATOREN[i][0], label_visibility="collapsed") or "gwp"
mit_betrieb = betrieb_schalter(kopfzeile[1], "betrieb_verlauf")
name, einheit = INDIKATOREN[ind]

df = verlauf_df.assign(wert=kurve(verlauf_df, ind, mit_betrieb))
kreuz = schnittpunkte(verlauf_df, ind, mit_betrieb)
st.altair_chart(kumuliert(df, "wert", k.farben, einheit, k.einst.zeitraum_a, kreuz),
                width="stretch")
st.caption(f"Bau = Herstellung A1–A3 (Jahr 0) · Stufen = Ersatz B4 im Austauschjahr · "
           f"{'gleichmäßiger Anstieg = Betrieb B6 · ' if mit_betrieb else ''}"
           f"Rückbau = C3 + C4 · Modul D nicht enthalten · Austausche: "
           f"{RUNDUNGSREGELN[k.einst.rundung]}")

# --------------------------------------------------------------------------- Schnittpunkte
with st.container(border=True):
    if kreuz.empty:
        st.markdown(f"**Keine Schnittpunkte** – die Reihenfolge der Varianten bei {name} ist über "
                    "den gesamten Zeitraum gleich.")
    else:
        st.markdown("**Schnittpunkte**")
        for _, z in kreuz.iterrows():
            wann = "beim Rückbau" if z["beim_rueckbau"] else f"in Jahr {z['zeitpunkt']:.1f}"
            st.markdown(f"- {z['variante_a']} × {z['variante_b']}: {wann} – vorher liegt "
                        f"**{z['vorher_besser']}** niedriger, danach **{z['nachher_besser']}**")

# --------------------------------------------------------------------------- Zerlegung je Variante
T = k.einst.zeitraum_a
spalten = st.columns(len(df["variante"].unique()), gap="medium")
var = k.ergebnis.varianten.set_index("variante")
for spalte_ui, (v, g) in zip(spalten, df.groupby("variante", sort=False)):
    g = g.set_index("zeitpunkt")
    with spalte_ui, st.container(border=True):
        varianten_titel(v, k.farben[v])
        m = st.columns(2)
        m[0].metric(f"Bau [{einheit}]", f"{g.loc[0, 'wert']:,.0f}".replace(",", " "))
        m[1].metric(f"Ende [{einheit}]", f"{g.loc[T + 1, 'wert']:,.0f}".replace(",", " "))
        anteil_bau = g.loc[0, "wert"] / g.loc[T + 1, "wert"] if g.loc[T + 1, "wert"] else float("nan")
        st.caption(f"Herstellung = {anteil_bau:.0%} der Summe · D (getrennt): "
                   f"{var.loc[v, spalte(ind, 'd')]:,.1f} {einheit}".replace(",", " "))
