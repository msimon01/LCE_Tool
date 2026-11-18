"""Seite Projekt, Bericht & Export."""

from __future__ import annotations


import streamlit as st

from ausgabe.csv_export import csv_bytes, ergebnis_dateien, schreibe_ergebnisse
from lce.daten_laden import zaehle_geschaetzt
from oberflaeche.bericht import erstelle_bericht
from oberflaeche.projekt import projekt_json
from oberflaeche.stil import kopf
from oberflaeche.zustand import ERGEBNISORDNER, kontext, ordner_beschreibbar, projekt_uebernehmen

BESCHREIBUNG = {
    "varianten.csv": "eine Zeile je Variante, alle Kennwerte",
    "schichten.csv": "eine Zeile je Schicht-Bestandteil",
    "masse.csv": "Masse je Schicht",
    "einstellungen.csv": "verwendete Randbedingungen",
    "optimum.csv": "Optimum und Bereich je Variante und Kriterium",
    "optimum_verlauf.csv": "Werte über der Dicke",
    "verlauf.csv": "kumulierter Verlauf je Variante und Jahr",
}

k = kontext()
kopf("Projekt, Bericht & Export", "Arbeitsstand sichern, Bericht für Abgabe oder Präsentation, "
                                  "Ergebnisse als CSV")

meldung = st.session_state.pop("projekt_meldung", None)
if meldung:
    (st.success if meldung[0] == "success" else st.error)(meldung[1])

# --------------------------------------------------------------------------- Projekt + Bericht
links, rechts = st.columns(2, gap="medium")
with links, st.container(border=True):
    st.markdown("### 💾 Projekt")
    st.caption("Aufbauten, Variantenauswahl, Randbedingungen, Suchbereich und Gewichte als "
               ".json-Datei. daten/ bleibt unverändert.")
    such = None
    if k.such is not None:
        such = {"d_min_m": k.such.d_min_m, "d_max_m": k.such.d_max_m,
                "schritt_m": k.such.schritt_m, "toleranz": k.such.toleranz}
    st.download_button("Projekt speichern", icon=":material/save:", type="primary",
                       data=projekt_json(k.einst, k.auswahl, st.session_state.aufbauten,
                                         k.gewichte, such).encode("utf-8"),
                       file_name="lce_projekt.json", mime="application/json", width="stretch")
    st.file_uploader("Projekt laden", type=["json"], key="projekt_datei",
                     on_change=projekt_uebernehmen, help="Ersetzt Aufbauten und Einstellungen")

with rechts, st.container(border=True):
    st.markdown("### 📄 Bericht")
    st.caption("Druckfertige Seite mit Randbedingungen, Wandschnitt, Kennzahlen, Gesamtbewertung, "
               "Optimum und Robustheit. Im Browser öffnen und mit Strg + P als PDF speichern.")
    if k.geprueft.ok and k.ergebnis is not None and not k.ergebnis.varianten.empty:
        titel = st.text_input("Titel", value="Variantenvergleich Außenwand")
        if st.button("Bericht erstellen", icon=":material/description:", width="stretch"):
            with st.spinner("Erstelle Bericht …"):
                st.session_state.bericht_html = erstelle_bericht(k, titel)
        if "bericht_html" in st.session_state:
            st.download_button("Bericht herunterladen (.html)", icon=":material/download:",
                               data=st.session_state.bericht_html.encode("utf-8"),
                               file_name="lce_bericht.html", mime="text/html", width="stretch")
            st.caption("Hinweis: Der Bericht gibt den Stand beim Erstellen wieder.")
    else:
        st.info("Kein Ergebnis vorhanden.")

# --------------------------------------------------------------------------- CSV
st.markdown("### Ergebnisse als CSV")
st.caption("Ungerundet; Trennzeichen „;“, Dezimalkomma, UTF-8 mit BOM")
if not k.geprueft.ok or k.ergebnis is None:
    st.error("Die Aufbauten enthalten Fehler, daher gibt es keine Ergebnisse.")
else:
    dateien = ergebnis_dateien(k.ergebnis, k.einst, k.optimierung(), k.verlauf()[0])
    spalten = st.columns(3)
    for i, (name, df) in enumerate(dateien.items()):
        with spalten[i % 3], st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(BESCHREIBUNG.get(name, ""))
            st.download_button("Herunterladen", data=csv_bytes(df), file_name=name,
                               mime="text/csv", key=f"dl_{name}", icon=":material/download:",
                               width="stretch")
    # Speichern in ergebnisse/ nur, wenn der Ordner beschreibbar ist (lokal); auf einem Server
    # genügen die Downloads oben (E07).
    if ordner_beschreibbar(ERGEBNISORDNER):
        if st.button("Alle zusätzlich in ergebnisse/ speichern", icon=":material/folder:"):
            try:
                pfade = schreibe_ergebnisse(k.ergebnis, k.einst, ERGEBNISORDNER, k.optimierung(),
                                            k.verlauf()[0])
                st.toast("Gespeichert: " + ", ".join(p.name for p in pfade), icon="✅")
            except OSError as e:
                st.warning(f"Speichern in ergebnisse/ nicht möglich ({e}). Bitte die Downloads "
                           "oben verwenden.")

st.markdown("### Eingangsdaten (daten/)")
for h in k.basis.hinweise:
    st.caption(f"⚠ {h}")
anzahl = zaehle_geschaetzt(k.daten_basis)
kosten_geschuetzt = st.session_state.get("kosten_quelle") == "Secret"
if kosten_geschuetzt:
    st.caption("🔒 Die Kosten stammen aus einem geschützten Datensatz und werden hier nicht als "
               "Tabelle angezeigt.")
for datei, df in k.daten_basis.items():
    if kosten_geschuetzt and datei == "kosten.csv":
        continue
    extra = f" · {anzahl[datei]} × „geschätzt“" if anzahl.get(datei) else ""
    with st.expander(f"{datei} · {len(df)} Zeilen{extra}"):
        st.dataframe(df, hide_index=True, width="stretch")
