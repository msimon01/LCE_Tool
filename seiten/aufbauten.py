"""Seite Aufbauten: Wandschnitt und Bearbeitung der Schichten."""

from __future__ import annotations

import streamlit as st

from ausgabe.csv_export import aufbauten_als_daten_csv
from oberflaeche.diagramme import wandschnitt
from oberflaeche.stil import kopf
from oberflaeche.zustand import (editor_aenderungen_uebernehmen, editor_als_rohdaten,
                                 editor_zuruecksetzen, kontext, meldungen_text)

k = kontext()
kopf("Aufbauten", "Schichten von innen nach außen. Änderungen gelten nur in dieser Sitzung; "
                  "daten/ bleibt unverändert.")

# --------------------------------------------------------------------------- Wandschnitt
if k.geprueft.ok and k.ergebnis is not None and not k.ergebnis.schichten.empty:
    st.markdown(f"### Wandschnitt bei {k.einst.modus_text}")
    # eine Zeile je Schicht, Material wie eingegeben (inhomogen z. B. kvh:0.12|glaswolle:0.88)
    sch = (k.ergebnis.schichten.drop_duplicates(["variante", "position"])
           .assign(material=lambda d: d["material_angabe"]))
    st.altair_chart(wandschnitt(sch, k.daten["materialien.csv"], k.auswahl), width="stretch")
elif not k.geprueft.ok:
    st.error("**Fehler in den Aufbauten**\n\n" + meldungen_text(k.geprueft.fehler, editor=True))

# --------------------------------------------------------------------------- Editor
st.markdown("### Schichten bearbeiten")
schluessel = f"editor_{st.session_state.editor_version}"
materialien = ", ".join(k.daten_basis["materialien.csv"]["id"])
st.data_editor(
    st.session_state.aufbauten, key=schluessel, num_rows="dynamic", width="stretch",
    hide_index=True, height=38 + 35 * min(len(st.session_state.aufbauten) + 1, 16),
    on_change=editor_aenderungen_uebernehmen, args=(schluessel,),
    column_config={
        "variante": st.column_config.TextColumn("Variante", help="Neuer Name = neue Variante",
                                                required=True, width="medium"),
        "position": st.column_config.NumberColumn("Pos.", help="innen → außen", step=1,
                                                  format="%d", required=True, width="small"),
        "schicht": st.column_config.TextColumn("Schicht", width="medium"),
        "material": st.column_config.TextColumn(
            "Material", help=f"Material-ID: {materialien}. Inhomogen: kvh:0.12|glaswolle:0.88",
            width="medium"),
        "dicke_cm": st.column_config.NumberColumn("Dicke [cm]", min_value=0.0, format="%.2f",
                                                  width="small"),
        "anpassbar": st.column_config.CheckboxColumn(
            "anpassbar", help="Wird auf den Ziel-U-Wert angepasst bzw. für das Optimum variiert",
            width="small"),
    })

c = st.columns([1, 1, 3])
if c[0].button("Katalog wiederherstellen", icon=":material/restart_alt:"):
    editor_zuruecksetzen(k.daten_basis["aufbauten.csv"])
    st.rerun()
c[1].download_button("Als CSV speichern", icon=":material/download:",
                     data=aufbauten_als_daten_csv(editor_als_rohdaten(st.session_state.aufbauten)),
                     file_name="aufbauten.csv", mime="text/csv",
                     help="Im Format von daten/aufbauten.csv, zum Übernehmen in VS Code")

with st.expander("Verfügbare Materialien"):
    st.dataframe(
        k.daten_basis["materialien.csv"][["id", "name", "kategorie", "rohdichte_kg_m3",
                                          "lambda_W_mK", "nutzungsdauer_a", "status"]]
        .rename(columns={"id": "ID", "name": "Name", "kategorie": "Kategorie",
                         "rohdichte_kg_m3": "ρ [kg/m³]", "lambda_W_mK": "λ [W/(mK)]",
                         "nutzungsdauer_a": "ND [a]", "status": "Status"}),
        hide_index=True, width="stretch")
