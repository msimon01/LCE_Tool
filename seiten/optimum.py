"""Seite Optimale Dämmdicke."""

from __future__ import annotations

import streamlit as st

from ausgabe.beschriftung import KRITERIUM_NAMEN, optimum_tabelle
from lce.einheiten import anteil_in_prozent, m_in_cm
from oberflaeche.diagramme import optimum_vergleich, optimum_zerlegung
from oberflaeche.stil import kopf, varianten_titel
from oberflaeche.zustand import fehler_in_aufbauten_hinweis, kontext

TEILE = {"gwp": ("Graue Emissionen (A1–A3, B4, C3, C4)", "Betrieb (B6)"),
         "penrt": ("Graue Energie (A1–A3, B4, C3, C4)", "Betrieb (B6)"),
         "lcc": ("Herstellung, Ersatz, Rückbau", "Heizkosten")}

k = kontext()
if k.einst.modus != "u_wert":
    st.info("Diese Seite rechnet immer im Modus **gleicher U-Wert** "
            f"({k.einst.ziel_u_w_m2k:.3f} W/(m²K)), auch wenn in der Seitenleiste "
            "„gleiche Wanddicke“ gewählt ist.", icon="ℹ️")
kopf("Optimale Dämmdicke",
     "Mehr Dämmung senkt den Betrieb, erhöht aber Herstellung und Entsorgung. "
     "Wo liegt das Minimum?")

if fehler_in_aufbauten_hinweis():
    st.stop()
if k.such is None:
    st.warning(k.such_fehler or "Suchbereich fehlt.")
    st.stop()

opt = k.optimierung()
for v, text in opt.fehler.items():
    st.error(f"**{v}**: {text}")
if opt.optima.empty:
    st.info("Keine Variante berechnet.")
    st.stop()

tol = anteil_in_prozent(k.such.toleranz)
st.write("")
kriterium = st.segmented_control(
    "Kriterium", options=list(KRITERIUM_NAMEN), default="gwp", key="kriterium_optimum",
    format_func=lambda kr: KRITERIUM_NAMEN[kr][0], label_visibility="collapsed") or "gwp"
name, einheit = KRITERIUM_NAMEN[kriterium]
optima_k = opt.optima[opt.optima["kriterium"] == kriterium]

# --------------------------------------------------------------------------- Karten
spalten = st.columns(len(optima_k), gap="medium")
for spalte_ui, (_, o) in zip(spalten, optima_k.iterrows()):
    v = o["variante"]
    with spalte_ui, st.container(border=True):
        chips = [(f"Bereich bis +{tol:g} %: {m_in_cm(o['dicke_von_m']):.0f}–"
                  f"{m_in_cm(o['dicke_bis_m']):.0f} cm", True)]
        if o["am_rand"]:
            chips.append(("Optimum am Rand", False))
        varianten_titel(v, k.farben[v], chips)
        m = st.columns(3)
        m[0].metric("Optimum [cm]", f"{m_in_cm(o['dicke_opt_m']):.1f}",
                    help=f"U = {o['u_opt_w_m2k']:.3f} W/(m²K)")
        m[1].metric(f"Minimum [{einheit}]", f"{o['wert_opt']:,.0f}".replace(",", " "))
        if "dicke_ziel_u_m" in o and o["dicke_ziel_u_m"] == o["dicke_ziel_u_m"]:
            m[2].metric("bei Ziel-U [cm]", f"{m_in_cm(o['dicke_ziel_u_m']):.1f}",
                        delta=f"+{anteil_in_prozent(o['mehr_bei_ziel_u_anteil']):.0f} %",
                        delta_color="inverse",
                        help="Dicke für den Ziel-U-Wert und Mehraufwand gegenüber dem Minimum")

hinweise = [f"**{v}**: {h}" for v, liste in opt.hinweise.items() for h in liste]
if hinweise:
    with st.expander(f"⚠ {len(hinweise)} Hinweise"):
        st.markdown("\n".join(f"- {h}" for h in hinweise))

# --------------------------------------------------------------------------- Diagramme
links, rechts = st.columns(2, gap="large")
with links:
    kopfzeile = st.columns([2, 3])
    kopfzeile[0].markdown(f"### Zerlegung {name}")
    v_wahl = kopfzeile[1].selectbox("Variante", list(optima_k["variante"]),
                                    label_visibility="collapsed", key="variante_optimum")
    o = optima_k.set_index("variante").loc[v_wahl]
    verlauf = opt.verlauf[opt.verlauf["variante"] == v_wahl]
    st.altair_chart(optimum_zerlegung(verlauf, kriterium, o, TEILE[kriterium], einheit,
                                      farbe=k.farben[v_wahl]), width="stretch")
    st.caption("Fläche: optimaler Bereich · Punkt: Optimum · gestrichelt: Dicke bei Ziel-U")
with rechts:
    st.markdown(f"### Alle Varianten: Summe {name}")
    st.altair_chart(optimum_vergleich(opt.verlauf, opt.optima, kriterium, k.farben, einheit),
                    width="stretch")
    st.caption(f"Suchbereich {m_in_cm(k.such.d_min_m):.0f}–{m_in_cm(k.such.d_max_m):.0f} cm, "
               f"Schritt {m_in_cm(k.such.schritt_m):.1f} cm (Seitenleiste → Erweitert)")

with st.expander("Tabelle aller Optima"):
    tabelle = optimum_tabelle(opt.optima).T.astype(str)
    st.dataframe(tabelle, width="stretch", height=38 + 35 * len(tabelle))
