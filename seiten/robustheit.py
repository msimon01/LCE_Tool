"""Seite Robustheit: Welche Eingangsgrößen verschieben das Ergebnis am stärksten?"""

from __future__ import annotations

import streamlit as st

from ausgabe.beschriftung import KRITERIUM_NAMEN
from lce.einheiten import anteil_in_prozent
from lce.sensitivitaet import hebel
from oberflaeche.diagramme import tornado
from oberflaeche.stil import kopf, varianten_titel
from oberflaeche.zustand import fehler_in_aufbauten_hinweis, kontext

k = kontext()
if k.einst.modus != "u_wert":
    st.info("Diese Seite rechnet immer im Modus **gleicher U-Wert** "
            f"({k.einst.ziel_u_w_m2k:.3f} W/(m²K)), auch wenn in der Seitenleiste "
            "„gleiche Wanddicke“ gewählt ist.", icon="ℹ️")
kopf("Robustheit", "Jede Eingangsgröße einzeln nach unten und oben verschoben – "
                   "wo liegen die großen Hebel, und bleibt die Rangfolge?")
if fehler_in_aufbauten_hinweis():
    st.stop()
with st.spinner("Rechne Varianten mit veränderten Eingangsgrößen …"):
    sens = k.sensitivitaet()
if sens is None:
    st.warning(k.sens_fehler or "Robustheit nicht berechenbar.")
    st.stop()
if sens.ergebnis.empty:
    st.info("Keine Variante berechnet.")
    st.stop()
for f in sens.fehler:
    st.error(f)

st.write("")
kriterium = st.segmented_control(
    "Kriterium", options=list(KRITERIUM_NAMEN), default="gwp", key="kriterium_robust",
    format_func=lambda kr: KRITERIUM_NAMEN[kr][0], label_visibility="collapsed") or "gwp"
name, einheit = KRITERIUM_NAMEN[kriterium]

# --------------------------------------------------------------------------- Rangfolge
w = sens.rangwechsel[sens.rangwechsel["kriterium"] == kriterium]
geaendert = w[w["geaendert"]]
with st.container(border=True):
    if geaendert.empty:
        st.markdown(f"#### ✅ Rangfolge {name} stabil")
        st.caption("In keinem der untersuchten Fälle ändert sich die Reihenfolge: "
                   + " > ".join(sens.basis_rangfolge[kriterium]))
    else:
        st.markdown(f"#### ⚠️ Rangfolge {name} ändert sich in {len(geaendert)} Fällen")
        st.caption("Basis: " + " > ".join(sens.basis_rangfolge[kriterium]))
        st.dataframe(geaendert[["groesse", "richtung", "spanne", "rangfolge"]].assign(
            spanne=lambda d: d["spanne"].map(lambda s: f"{anteil_in_prozent(s):.0f} %")).rename(
            columns={"groesse": "Größe", "richtung": "Richtung", "spanne": "Spanne",
                     "rangfolge": "neue Rangfolge"}), hide_index=True, width="stretch")

# --------------------------------------------------------------------------- Tornado je Variante
varianten = list(dict.fromkeys(sens.ergebnis["variante"]))
spalten = st.columns(min(len(varianten), 2), gap="large")
for i, v in enumerate(varianten):
    h = hebel(sens, v, kriterium)
    h = h[h["spannweite"] > 1e-9]
    with spalten[i % len(spalten)], st.container(border=True):
        groesster = h.iloc[0] if not h.empty else None
        chips = [(f"größter Hebel: {groesster['groesse']}", True)] if groesster is not None else []
        varianten_titel(v, k.farben[v], chips)
        if h.empty:
            st.caption("Keine der Größen wirkt auf dieses Kriterium.")
        else:
            st.altair_chart(tornado(h, einheit), width="stretch")

st.caption("Spannen aus daten/parameter.csv (sensitivitaet_*). Der Ziel-U-Wert bleibt fest, die "
           "Dämmdicke wird in jedem Fall neu angepasst. Nutzungsdauern wirken sprunghaft: "
           "Unterschreitet eine Nutzungsdauer den Betrachtungszeitraum, kommt durch die Rundung "
           "ein ganzer Austausch hinzu.")
