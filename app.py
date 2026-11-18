"""Oberfläche des LCE-Tools (Streamlit).

Start: Doppelklick auf start.bat oder `python -m streamlit run app.py` im Projektordner.
Die Oberfläche rechnet nicht selbst, sie ruft nur den Rechenkern (lce/) auf und zeigt dessen
Ergebnisse an. daten/ wird nie verändert. Die Seiten liegen in seiten/, gemeinsame Bausteine
in oberflaeche/.
"""

from __future__ import annotations

import streamlit as st

from lce.berechnung import MODI, MODUS_U_WERT, MODUS_WANDDICKE, standard_einstellungen
from lce.bewertung import BEWERTUNG_PARAMETER
from lce.daten_laden import lies_rohdaten, parameter, parameter_info, pruefe_rohdaten
from lce.einheiten import anteil_in_prozent, cm_in_m, m_in_cm, prozent_in_anteil
from lce.oekobilanz import RUNDUNGSREGELN
from oberflaeche.stil import css
from oberflaeche.zustand import (DATENORDNER, baue_kontext, editor_initialisieren,
                                 meldungen_text, optimierungsparameter_fehlen, standardwert)

st.set_page_config(page_title="LCE-Tool Außenwand", page_icon="🧱", layout="wide",
                   initial_sidebar_state="auto")  # Handy: eingeklappt
css()

# --------------------------------------------------------------------------- Daten
roh, lesefehler = lies_rohdaten(DATENORDNER)
basis = pruefe_rohdaten(roh, lesefehler)
if not basis.ok:
    st.title("LCE-Tool Außenwand")
    st.error("**Fehler in daten/**\n\n" + meldungen_text(basis.fehler))
    st.info("Bitte die genannten Stellen korrigieren und die Seite neu laden (F5).")
    st.stop()
daten_basis = basis.daten
standard = standard_einstellungen(daten_basis)
editor_initialisieren(daten_basis["aufbauten.csv"])
vorhanden = set(daten_basis["parameter.csv"]["schluessel"])


def hilfe(schluessel: str) -> str:
    info = parameter_info(daten_basis, schluessel)
    return (f"{info['beschreibung']}\n\n**Einheit:** {info['einheit']} · **Status:** "
            f"{info['status']} · **Standard:** {parameter(daten_basis, schluessel):g}")


# Startwerte der Eingaben (aus daten/), danach führt Streamlit sie über die Schlüssel
standardwert("e_ziel_u", standard.ziel_u_w_m2k)
standardwert("e_modus", MODUS_U_WERT)
mit_wanddicke = standard.ziel_wanddicke_m is not None
if mit_wanddicke:
    standardwert("e_wanddicke", m_in_cm(standard.ziel_wanddicke_m))
standardwert("e_traeger", standard.energietraeger_id)
standardwert("e_rundung", standard.rundung)
standardwert("e_zeitraum", standard.zeitraum_a)
standardwert("e_startjahr", standard.startjahr)
standardwert("e_gt", standard.heizgradstunden_kkh)
standardwert("e_zins", standard.zins)
standardwert("e_p_bau", standard.preissteigerung_bau)
standardwert("e_p_energie", standard.preissteigerung_energie)
mit_optimum = not optimierungsparameter_fehlen(daten_basis)
if mit_optimum:
    standardwert("e_d_min", m_in_cm(parameter(daten_basis, "optimierung_d_min_m")))
    standardwert("e_d_max", m_in_cm(parameter(daten_basis, "optimierung_d_max_m")))
    standardwert("e_schritt", m_in_cm(parameter(daten_basis, "optimierung_schritt_m")))
    standardwert("e_tol", anteil_in_prozent(parameter(daten_basis, "optimierung_toleranz")))
mit_bewertung = all(p in vorhanden for p in BEWERTUNG_PARAMETER.values())
if mit_bewertung:
    for kr, p in BEWERTUNG_PARAMETER.items():
        standardwert(f"e_w_{kr}", float(parameter(daten_basis, p)))

# Variantenauswahl: neue Varianten automatisch auswählen, gelöschte entfernen
varianten_katalog = list(dict.fromkeys(st.session_state.aufbauten["variante"].dropna()))
bekannt = st.session_state.get("e_bekannt", [])
standardwert("e_auswahl", list(varianten_katalog))
st.session_state.e_auswahl = [v for v in st.session_state.e_auswahl if v in varianten_katalog] \
    + [v for v in varianten_katalog if v not in bekannt and v not in st.session_state.e_auswahl]
st.session_state.e_bekannt = varianten_katalog

# --------------------------------------------------------------------------- Seitenleiste
et = daten_basis["energietraeger.csv"].set_index("id")
with st.sidebar:
    st.markdown("### 🧱 LCE-Tool Außenwand")
    st.caption("Variantenvergleich in der Vor- und Entwurfsplanung")

    st.segmented_control(
        "Vergleich bei", options=list(MODI), format_func=MODI.get, key="e_modus",
        help="Gleicher U-Wert: alle Varianten thermisch gleichwertig. Gleiche Wanddicke: "
             "Geometrie vorgegeben, der U-Wert ergibt sich je Variante – die Varianten sind dann "
             "thermisch nicht gleichwertig, B6 nur vereinfacht über Heizgradstunden.")
    # Abgewählter Umschalter (None) = Standardmodus
    modus = st.session_state.e_modus if st.session_state.e_modus in MODI else MODUS_U_WERT
    wanddicke_modus = modus == MODUS_WANDDICKE and mit_wanddicke
    st.number_input("Ziel-U-Wert [W/(m²K)]", min_value=0.05, max_value=2.0, step=0.01,
                    format="%.3f", key="e_ziel_u", help=hilfe("ziel_u_w_m2k"),
                    disabled=wanddicke_modus)
    if mit_wanddicke:
        st.number_input("Zielwanddicke [cm]", min_value=1.0, max_value=200.0, step=1.0,
                        format="%.1f", key="e_wanddicke", help=hilfe("ziel_wanddicke_m"),
                        disabled=not wanddicke_modus)
    elif modus == MODUS_WANDDICKE:
        st.warning("Für den Modus „gleiche Wanddicke“ fehlt `ziel_wanddicke_m` in "
                   "daten/parameter.csv.", icon="⚠️")
    st.selectbox("Energieträger Heizung", options=list(et.index), key="e_traeger",
                 format_func=lambda i: et.loc[i, "name"],
                 help="Für Betrieb B6 und Heizkosten. Standard = erste Zeile in "
                      "energietraeger.csv. Strom: Emissionsfaktor sinkt nach strom_szenario.csv.")
    st.multiselect("Varianten", varianten_katalog, key="e_auswahl", placeholder="alle Varianten")

    with st.expander("Erweitert"):
        st.radio("Austauschhäufigkeit", options=list(RUNDUNGSREGELN), key="e_rundung",
                 format_func=RUNDUNGSREGELN.get,
                 help="N = T/ND − 1. Aufrunden: jeder angebrochene Zyklus zählt. "
                      "Kaufmännisch: ab 0,5 zählt ein Austausch.")
        st.number_input("Betrachtungszeitraum [a]", min_value=1, max_value=200, step=1,
                        key="e_zeitraum", help=hilfe("zeitraum_a"))
        st.number_input("Startjahr", min_value=1990, max_value=2100, step=1, key="e_startjahr",
                        help=hilfe("startjahr"))
        st.number_input("Heizgradstunden [kKh/a]", min_value=0.0, step=1.0, key="e_gt",
                        help=hilfe("heizgradstunden_kkh"))
        st.number_input("Zins [1/a]", min_value=0.0, max_value=0.5, step=0.001, format="%.4f",
                        key="e_zins", help=hilfe("zins"))
        st.number_input("Preissteigerung Bau [1/a]", min_value=-0.2, max_value=0.5, step=0.001,
                        format="%.4f", key="e_p_bau", help=hilfe("preissteigerung_bau"))
        st.number_input("Preissteigerung Energie [1/a]", min_value=-0.2, max_value=0.5,
                        step=0.001, format="%.4f", key="e_p_energie",
                        help=hilfe("preissteigerung_energie"))
        if mit_optimum:
            st.markdown("**Optimum**")
            c1, c2 = st.columns(2)
            c1.number_input("min. Dicke [cm]", min_value=0.1, step=0.5, format="%.1f",
                            key="e_d_min", help=hilfe("optimierung_d_min_m"))
            c2.number_input("max. Dicke [cm]", min_value=0.2, step=1.0, format="%.1f",
                            key="e_d_max", help=hilfe("optimierung_d_max_m"))
            c1.number_input("Schritt [cm]", min_value=0.01, step=0.1, format="%.2f",
                            key="e_schritt", help=hilfe("optimierung_schritt_m"))
            c2.number_input("Toleranz [%]", min_value=0.0, max_value=100.0, step=1.0,
                            format="%.1f", key="e_tol", help=hilfe("optimierung_toleranz"))

    if mit_bewertung:
        with st.expander("Gewichtung Gesamtbewertung"):
            st.caption("Relative Gewichte; 1 / 1 / 1 = gleich wichtig")
            st.slider("GWP", 0.0, 5.0, step=0.5, key="e_w_gwp", help=hilfe("bewertung_gewicht_gwp"))
            st.slider("PENRT", 0.0, 5.0, step=0.5, key="e_w_penrt",
                      help=hilfe("bewertung_gewicht_penrt"))
            st.slider("Lebenszykluskosten", 0.0, 5.0, step=0.5, key="e_w_lcc",
                      help=hilfe("bewertung_gewicht_lcc"))

    if not wanddicke_modus and st.session_state.e_ziel_u > parameter(daten_basis, "geg_referenz_u"):
        st.warning(f"Ziel-U über GEG-Referenzwert "
                   f"{parameter(daten_basis, 'geg_referenz_u'):.2f} W/(m²K)", icon="⚠️")

s = st.session_state
einst = standard.mit(ziel_u_w_m2k=float(s.e_ziel_u), zeitraum_a=int(s.e_zeitraum),
                     startjahr=int(s.e_startjahr), heizgradstunden_kkh=float(s.e_gt),
                     zins=float(s.e_zins), preissteigerung_bau=float(s.e_p_bau),
                     preissteigerung_energie=float(s.e_p_energie),
                     energietraeger_id=str(s.e_traeger), rundung=str(s.e_rundung),
                     modus=MODUS_WANDDICKE if wanddicke_modus else MODUS_U_WERT,
                     ziel_wanddicke_m=cm_in_m(s.e_wanddicke) if mit_wanddicke else None)
such_werte = (cm_in_m(s.e_d_min), cm_in_m(s.e_d_max), cm_in_m(s.e_schritt),
              prozent_in_anteil(s.e_tol)) if mit_optimum else None
gewichte = {kr: float(s[f"e_w_{kr}"]) for kr in BEWERTUNG_PARAMETER} if mit_bewertung else None

# --------------------------------------------------------------------------- Rechnen
baue_kontext(roh, basis, einst, list(s.e_auswahl), such_werte, gewichte)

# --------------------------------------------------------------------------- Seiten
seiten = st.navigation({
    "Ergebnisse": [
        st.Page("seiten/uebersicht.py", title="Übersicht", icon=":material/dashboard:",
                default=True),
        st.Page("seiten/verlauf.py", title="Verlauf über die Zeit", icon=":material/show_chart:"),
        st.Page("seiten/zielkonflikt.py", title="Zielkonflikt", icon=":material/scatter_plot:"),
        st.Page("seiten/optimum.py", title="Optimale Dämmdicke", icon=":material/insights:"),
        st.Page("seiten/robustheit.py", title="Robustheit", icon=":material/tune:"),
        st.Page("seiten/details.py", title="Details je Schicht", icon=":material/table_rows:"),
    ],
    "Eingaben": [
        st.Page("seiten/aufbauten.py", title="Aufbauten", icon=":material/layers:"),
    ],
    "Sonstiges": [
        st.Page("seiten/export.py", title="Projekt, Bericht & Export",
                icon=":material/download:"),
        st.Page("seiten/hilfe.py", title="Methode & Hilfe", icon=":material/help:"),
    ],
})
seiten.run()
