"""Seite Zielkonflikt (E05): Punktwolke Ökologie gegen Kosten und Robustheits-Ampel."""

from __future__ import annotations

import streamlit as st

from ausgabe.beschriftung import EUR, GWP, PENRT
from lce.abwaegung import GELB, GRUEN, ROT, ampel, punktwolke
from oberflaeche.diagramme import zielkonflikt
from oberflaeche.stil import AMPEL_SYMBOL, AMPELFARBEN, GRAU, kopf, varianten_titel
from oberflaeche.zustand import betrieb_schalter, fehler_in_aufbauten_hinweis, kontext

OEKO = {"gwp": ("GWP", GWP), "penrt": ("PENRT", PENRT)}
AMPEL_TEXT = {GRUEN: "in allen Robustheitsfällen nicht übertroffen",
              GELB: "nur in einem Teil der Fälle nicht übertroffen",
              ROT: "in keinem Robustheitsfall nicht übertroffen"}

k = kontext()
kopf(f"Zielkonflikt Ökologie ↔ Kosten · {k.einst.modus_text}",
     "Welche Varianten sind nicht übertroffen – und bleibt das so, wenn sich Annahmen ändern?")
if fehler_in_aufbauten_hinweis():
    st.stop()
var = k.ergebnis.varianten
if var.empty:
    st.info("Keine Variante berechnet.")
    st.stop()

st.write("")
kopfzeile = st.columns([3, 2])
oeko = kopfzeile[0].segmented_control(
    "Ökologische Größe", options=list(OEKO), default="gwp", key="oeko_zielkonflikt",
    format_func=lambda i: OEKO[i][0], label_visibility="collapsed") or "gwp"
mit_betrieb = betrieb_schalter(kopfzeile[1], "betrieb_zielkonflikt")
name, einheit = OEKO[oeko]

wolke = punktwolke(var, oeko, mit_betrieb)

# Ampel aus der Robustheitsprüfung (Modus gleicher U-Wert, siehe Hinweis)
ampel_df = None
if k.modus_ampel_moeglich():
    with st.spinner("Werte Robustheitsfälle aus …"):
        sens = k.sensitivitaet()
    if sens is not None and not sens.ergebnis.empty:
        ampel_df = ampel(sens, oeko, mit_betrieb).set_index("variante")
    elif k.sens_fehler:
        st.warning(f"Ampel nicht verfügbar: {k.sens_fehler}")
else:
    st.info("Die Robustheits-Ampel gibt es nur im Modus **gleicher U-Wert**, weil die "
            "Robustheitsprüfung in diesem Modus rechnet. Die Punktwolke zeigt den aktuellen Modus.")

punktfarben = {v: AMPELFARBEN[ampel_df.loc[v, "ampel"]] if ampel_df is not None and v in ampel_df.index
               else k.farben[v] for v in wolke["variante"]}
links, rechts = st.columns([3, 2], gap="large")
with links:
    st.altair_chart(zielkonflikt(wolke, punktfarben, k.farben, f"{name} [{einheit}]",
                                 f"Lebenszykluskosten [{EUR}]"), width="stretch")
    st.caption("Unten links ist besser. Große Punkte: nicht übertroffen (keine andere Variante ist "
               "in beiden Größen mindestens gleich gut und in einer besser); gestrichelt verbunden. "
               "Füllung = Ampel, Ring = Variantenfarbe."
               + ("" if mit_betrieb else " Ohne Betrieb B6 bzw. Heizkosten."))

with rechts:
    for _, z in wolke.sort_values(["nicht_uebertroffen", "x"], ascending=[False, True]).iterrows():
        v = z["variante"]
        with st.container(border=True):
            chips = [("nicht übertroffen", True)] if z["nicht_uebertroffen"] else \
                [(f"übertroffen von {z['uebertroffen_von']}", False)]
            varianten_titel(v, k.farben[v], chips)
            if ampel_df is not None and v in ampel_df.index:
                a = ampel_df.loc[v]
                st.markdown(f"{AMPEL_SYMBOL[a['ampel']]} **{a['ampel'].capitalize()}** – "
                            f"{AMPEL_TEXT[a['ampel']]} ({a['nicht_uebertroffen_in']} von {a['faelle']})")
                if a["ampel"] == GELB:
                    with st.expander("Welche Annahmen kippen das Ergebnis?"):
                        st.markdown("\n".join(f"- {f}" for f in a["kipp_faelle"]))
            st.caption(f"{name} {z['x']:,.1f} {einheit} · Kosten {z['y']:,.1f} {EUR}".replace(",", " "))

st.caption("Ampel: Jede Annahme der Robustheitsprüfung wird einzeln auf ihren unteren und oberen "
           "Wert gesetzt (Spannen in parameter.csv) und geprüft, ob die Variante übertroffen wird. "
           "Die gewichtete Gesamtbewertung auf der Übersicht bleibt davon unberührt.")
