"""Seite Details je Schicht (wie eLCA)."""

from __future__ import annotations

import streamlit as st

from ausgabe.beschriftung import EUR, GWP, PENRT, SCHICHT_SPALTEN, anzeige
from lce.einheiten import m_in_cm
from lce.oekobilanz import spalte
from oberflaeche.diagramme import wandschnitt
from oberflaeche.stil import kopf, varianten_titel
from oberflaeche.zustand import fehler_in_aufbauten_hinweis, kontext

KURZ = ["position", "schicht", "material", "anteil", "dicke_cm", "masse_kg_m2", "nutzungsdauer_a",
        "austausch_n", "gwp_a1a3_kg_co2e_m2", "gwp_b4_kg_co2e_m2", "gwp_c3_kg_co2e_m2",
        "gwp_c4_kg_co2e_m2", "gwp_d_kg_co2e_m2", "lcc_herstellung_eur_m2"]

k = kontext()
kopf(f"Details je Schicht · {k.einst.modus_text}", "Eine Zeile je Schicht bzw. je Bestandteil einer inhomogenen Schicht, "
                           "Werte je m² Wand über den Betrachtungszeitraum")
if fehler_in_aufbauten_hinweis():
    st.stop()
erg = k.ergebnis
if erg.schichten.empty:
    st.info("Keine Variante berechnet.")
    st.stop()

varianten = list(dict.fromkeys(erg.schichten["variante"]))
st.write("")
v = st.segmented_control("Variante", varianten, default=varianten[0], key="variante_details",
                         label_visibility="collapsed") or varianten[0]
z = erg.varianten.set_index("variante").loc[v]
sch = erg.schichten[erg.schichten["variante"] == v]

with st.container(border=True):
    varianten_titel(v, k.farben[v])
    m = st.columns(6)
    m[0].metric("U vorher [W/(m²K)]", f"{z['u_vorher_w_m2k']:.3f}")
    m[1].metric("U nachher [W/(m²K)]", f"{z['u_nachher_w_m2k']:.3f}")
    if z["dicke_nachher_m"] == z["dicke_nachher_m"] and z["dicke_nachher_m"] is not None:
        m[2].metric(f"{z['angepasste_schicht']} [cm]", f"{m_in_cm(z['dicke_nachher_m']):.2f}",
                    delta=f"{m_in_cm(z['dicke_nachher_m'] - z['dicke_vorher_m']):+.2f} cm",
                    delta_color="off")
    m[3].metric("Masse [kg/m²]", f"{z['masse_kg_m2']:.1f}")
    m[4].metric(f"GWP B6 [{GWP}]", f"{z[spalte('gwp', 'b6')]:.1f}",
                help=f"Q = {z['q_kwh_m2a']:.2f} kWh/(m²a), E = {z['e_kwh_m2a']:.2f} kWh/(m²a), "
                     f"PENRT B6 = {z[spalte('penrt', 'b6')]:.0f} {PENRT}")
    m[5].metric(f"Heizkosten [{EUR}]", f"{z['lcc_heizung_eur_m2']:.1f}")
    st.altair_chart(wandschnitt(sch.drop_duplicates("position").assign(
        material=lambda d: d["material_angabe"]), k.daten["materialien.csv"], [v]),
        width="stretch")

alle = st.toggle("Alle Spalten zeigen (PENRT, λ, R, Rohdichte, Kosten, Status)")
spalten = SCHICHT_SPALTEN if alle else {s: SCHICHT_SPALTEN[s] for s in KURZ}
st.dataframe(anzeige(sch, spalten), hide_index=True, width="stretch")
