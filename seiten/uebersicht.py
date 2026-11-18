"""Seite Übersicht: Kennzahlen je Variante, Diagramm, Rangliste."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ausgabe.beschriftung import EUR, GWP, PENRT, VARIANTEN_SPALTEN, anzeige
from lce.einheiten import anteil_in_prozent, m_in_cm
from lce.berechnung import MODUS_U_WERT, MODUS_WANDDICKE, rangfolge
from lce.oekobilanz import RUNDUNGSREGELN, spalte
from oberflaeche.diagramme import gestapelt
from oberflaeche.stil import kopf, rangliste_html, varianten_titel
from oberflaeche.zustand import betrieb_schalter, fehler_in_aufbauten_hinweis, kontext

KRITERIEN = {"gwp": ("GWP", GWP, spalte("gwp", "summe")),
             "penrt": ("PENRT", PENRT, spalte("penrt", "summe")),
             "lcc": ("Kosten", EUR, "lcc_summe_eur_m2")}

k = kontext()
traeger = k.daten_basis["energietraeger.csv"].set_index("id").loc[k.einst.energietraeger_id, "name"]
kopf(f"Variantenvergleich bei {k.einst.modus_text}",
     f"je m² Wand · {k.einst.zeitraum_a} Jahre ab {k.einst.startjahr} · {traeger} · "
     f"{RUNDUNGSREGELN[k.einst.rundung]}")
if k.einst.modus == MODUS_WANDDICKE:
    st.warning("Modus **gleiche Wanddicke**: Die Varianten haben unterschiedliche U-Werte und sind "
               "thermisch nicht gleichwertig. Der Betrieb B6 ist nur vereinfacht über "
               "Heizgradstunden abgebildet.", icon="📏")

if fehler_in_aufbauten_hinweis():
    st.stop()

erg = k.ergebnis
for v, text in erg.fehler.items():
    st.error(f"**{v}**: {text}")
var = erg.varianten
if var.empty:
    st.info("Keine Variante berechnet.")
    st.stop()

st.write("")

# --------------------------------------------------------------------------- Karten
beste = {kr: var[s].min() for kr, (_, _, s) in KRITERIEN.items()}
bewertung = k.bewertung()
punkte = bewertung.set_index("variante") if bewertung is not None else None


def abstand(wert: float, bester: float) -> str | None:
    """Abstand zur besten Variante in % (bezogen auf |bester|), None für die beste."""
    if abs(wert - bester) < 1e-9:
        return None
    return f"+{anteil_in_prozent((wert - bester) / abs(bester)):.0f} %"


spalten = st.columns(len(var), gap="medium")
for spalte_ui, (_, z) in zip(spalten, var.iterrows()):
    v = z["variante"]
    with spalte_ui, st.container(border=True):
        chips = [(f"{m_in_cm(z['dicke_nachher_m']):.1f} cm {z['angepasste_schicht']}", False)] \
            if z["dicke_nachher_m"] == z["dicke_nachher_m"] and z["dicke_nachher_m"] is not None else []
        if k.einst.modus == MODUS_WANDDICKE:
            chips.insert(0, (f"U = {z['u_nachher_w_m2k']:.3f} W/(m²K)", False))
        siege = [name for kr, (name, _, s) in KRITERIEN.items() if abs(z[s] - beste[kr]) < 1e-9]
        if siege:
            chips.insert(0, ("★ beste: " + ", ".join(siege), True))
        if punkte is not None:
            p_v = punkte.loc[v]
            chips.insert(0, (f"Gesamt {p_v['punkte_gesamt']:.0f} Punkte · Rang {int(p_v['rang'])}",
                             int(p_v["rang"]) == 1))
        varianten_titel(v, k.farben[v], chips)
        m = st.columns(3)
        for mc, (kr, (name, einheit, s)) in zip(m, KRITERIEN.items()):
            mc.metric(f"{name} [{einheit}]", f"{z[s]:,.0f}".replace(",", " ") if kr == "penrt"
                      else f"{z[s]:.1f}", delta=abstand(z[s], beste[kr]), delta_color="inverse")
        hinweise = list(erg.hinweise.get(v, []))
        if z["geschaetzt"]:
            hinweise.insert(0, f"enthält geschätzte Werte: {z['geschaetzt']}")
        unten = st.columns([3, 2])
        unten[0].caption(f"Masse {z['masse_kg_m2']:.0f} kg/m² · Wand {m_in_cm(z['wanddicke_m']):.1f} cm")
        if hinweise:
            with unten[1].popover(f"⚠ {len(hinweise)}", use_container_width=True):
                for h in hinweise:
                    st.markdown(f"- {h}")

st.write("")

# --------------------------------------------------------------------------- Diagramm + Rangliste
links, rechts = st.columns([5, 2], gap="large")
with links:
    kopfzeile = st.columns([3, 2])
    kriterium = kopfzeile[0].segmented_control(
        "Kriterium", options=list(KRITERIEN), default="gwp", key="kriterium_uebersicht",
        format_func=lambda kr: KRITERIEN[kr][0], label_visibility="collapsed") or "gwp"
    mit_betrieb = betrieb_schalter(kopfzeile[1], "betrieb_uebersicht")
    name, einheit, s = KRITERIEN[kriterium]
    st.altair_chart(gestapelt(var, kriterium, mit_betrieb, einheit), width="stretch")
    if kriterium != "lcc":
        st.caption("Modul D (Gutschriften) ist nicht enthalten, siehe „Alle Kennwerte“.")

with rechts:
    st.markdown(f"### Rangliste {name}")
    rang = var[["variante", s]].sort_values(s).reset_index(drop=True)
    st.markdown(rangliste_html(rang, s, k.farben, einheit), unsafe_allow_html=True)
    if bewertung is not None:
        g = k.gewichte
        st.markdown("### Gesamtbewertung")
        st.markdown(rangliste_html(bewertung, "punkte_gesamt", k.farben, "Punkte (beste je "
                                   "Kriterium = 100)", absteigend=True), unsafe_allow_html=True)
        st.caption(f"Gewichte GWP / PENRT / Kosten = {g['gwp']:g} / {g['penrt']:g} / {g['lcc']:g} "
                   "(Seitenleiste)")

# --------------------------------------------------------------------------- Rangfolge beider Modi
if k.einst.ziel_wanddicke_m is not None:
    with st.expander("Rangfolge: gleicher U-Wert ↔ gleiche Wanddicke", expanded=False):
        erg_u, erg_w = k.ergebnis_im_modus(MODUS_U_WERT), k.ergebnis_im_modus(MODUS_WANDDICKE)
        zeilen = []
        for kr, (name, einheit, s) in KRITERIEN.items():
            ru = rangfolge(erg_u.varianten, s) if not erg_u.varianten.empty else []
            rw = rangfolge(erg_w.varianten, s) if not erg_w.varianten.empty else []
            gemeinsam = [v for v in ru if v in rw]
            geaendert = "ja" if gemeinsam != [v for v in rw if v in ru] else "nein"
            zeilen.append({"Kriterium": name, "Rangfolge geändert": geaendert,
                           f"gleicher U-Wert ({k.einst.ziel_u_w_m2k:.2f} W/(m²K))": " > ".join(ru),
                           f"gleiche Wanddicke ({m_in_cm(k.einst.ziel_wanddicke_m):.0f} cm)": " > ".join(rw)})
        st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")
        for v, text in erg_w.fehler.items():
            st.caption(f"⚠ gleiche Wanddicke – {v}: {text}")
        st.caption("Links ist besser („>“ = vor). Varianten, die in einem Modus nicht rechenbar sind, "
                   "fehlen dort.")

with st.expander("Alle Kennwerte"):
    st.dataframe(anzeige(var, VARIANTEN_SPALTEN, index="variante").T.astype(str),
                 width="stretch", height=38 + 35 * len(VARIANTEN_SPALTEN))
