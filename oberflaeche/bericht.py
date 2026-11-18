"""Bericht als druckfertige HTML-Seite (im Browser „Drucken → Als PDF speichern“).

Enthält Randbedingungen, Aufbauten, Kennzahlen, Gesamtbewertung, Optimum, Robustheit und
Hinweise. Die Diagramme werden beim Öffnen mit Vega-Lite gezeichnet (Internetverbindung nötig,
Versionen wie im installierten Altair). Nur Darstellung, keine Berechnung.
"""

from __future__ import annotations

import html
import json
from datetime import date

import altair as alt
import pandas as pd

from ausgabe.beschriftung import EUR, GWP, KRITERIUM_NAMEN, PENRT, optimum_tabelle
from lce.einheiten import anteil_in_prozent, m_in_cm
from lce.oekobilanz import RUNDUNGSREGELN, spalte
from lce.sensitivitaet import hebel
from oberflaeche.diagramme import gestapelt, optimum_vergleich, wandschnitt

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #1d232b; font-size: 10.5pt;
       max-width: 900px; margin: 24px auto; padding: 0 16px; line-height: 1.45; }
h1 { font-size: 20pt; margin: 0 0 2px; }
h2 { font-size: 13pt; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #3DD6B5; }
.unter { color: #5b6672; margin-bottom: 14px; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9.5pt; }
th, td { border-bottom: 1px solid #dde3ea; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #f2f5f8; font-weight: 600; }
td.z { text-align: right; font-variant-numeric: tabular-nums; }
.karten { display: flex; gap: 10px; flex-wrap: wrap; }
.karte { flex: 1 1 200px; border: 1px solid #dde3ea; border-radius: 8px; padding: 8px 10px;
         border-top: 4px solid var(--f); break-inside: avoid; }
.karte b { display: block; margin-bottom: 4px; }
.kz { display: flex; justify-content: space-between; font-size: 9.5pt; }
.hinweis { color: #8a5a00; font-size: 9.5pt; }
.diagramm { break-inside: avoid; margin: 6px 0 12px; }
.seitenumbruch { break-before: page; }
.fuss { color: #5b6672; font-size: 8.5pt; margin-top: 24px; border-top: 1px solid #dde3ea; padding-top: 6px; }
@media print { .nicht-drucken { display: none; } body { margin: 0; } }
"""


def _hell(diagramm) -> dict:
    """Diagramm für den Druck: heller Hintergrund, dunkle Schrift."""
    return diagramm.properties(width=820).configure(background="#ffffff").configure_axis(
        labelColor="#1d232b", titleColor="#1d232b", gridColor="#e3e8ee", domainColor="#aab4bf"
    ).configure_legend(labelColor="#1d232b").configure_view(stroke=None).to_dict()


def _tabelle(df: pd.DataFrame, zahlen: set[str] = frozenset()) -> str:
    kopf = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    zeilen = []
    for _, z in df.iterrows():
        zellen = "".join(f"<td class='{'z' if c in zahlen else ''}'>{html.escape(str(z[c]))}</td>"
                         for c in df.columns)
        zeilen.append(f"<tr>{zellen}</tr>")
    return f"<table><thead><tr>{kopf}</tr></thead><tbody>{''.join(zeilen)}</tbody></table>"


def erstelle_bericht(k, titel: str = "Variantenvergleich Außenwand") -> str:
    """HTML-Bericht aus dem Kontext der Oberfläche (oberflaeche.zustand.Kontext)."""
    erg = k.ergebnis
    var = erg.varianten
    e = k.einst
    traeger = k.daten_basis["energietraeger.csv"].set_index("id").loc[e.energietraeger_id, "name"]
    diagramme: list[tuple[str, dict]] = []

    def diagramm(chart) -> str:
        nr = f"d{len(diagramme)}"
        diagramme.append((nr, _hell(chart)))
        return f"<div class='diagramm' id='{nr}'></div>"

    teile = [f"<h1>{html.escape(titel)}</h1>",
             f"<div class='unter'>LCE-Tool · erstellt am {date.today():%d.%m.%Y} · Vorstufe zu eLCA, "
             f"kein Ersatz</div>",
             "<p class='nicht-drucken'><b>Als PDF speichern:</b> Strg + P → „Als PDF speichern“.</p>"]

    # 1 Randbedingungen
    rb = pd.DataFrame([
        ("Vergleichsmodus", e.modus_text),
        ("Ziel-U-Wert", f"{e.ziel_u_w_m2k:.3f} W/(m²K)" if e.modus == "u_wert" else "– (ergibt sich je Variante)"),
        ("Betrachtungszeitraum", f"{e.zeitraum_a} a ab {e.startjahr}"),
        ("Heizgradstunden", f"{e.heizgradstunden_kkh:g} kKh/a"),
        ("Energieträger", traeger),
        ("Austauschhäufigkeit", RUNDUNGSREGELN[e.rundung]),
        ("Zins / Preissteigerung Bau / Energie",
         f"{e.zins:.4f} / {e.preissteigerung_bau:.4f} / {e.preissteigerung_energie:.4f} 1/a"),
    ], columns=["Größe", "Wert"])
    teile += ["<h2>1 Randbedingungen</h2>", _tabelle(rb)]

    # 2 Aufbauten
    sch = erg.schichten.drop_duplicates(["variante", "position"]).assign(
        material=lambda d: d["material_angabe"])
    teile += [f"<h2>2 Aufbauten ({html.escape(e.modus_text)})</h2>",
              diagramm(wandschnitt(sch, k.daten["materialien.csv"], list(var["variante"])))]
    auf = sch[["variante", "position", "schicht", "material", "dicke_m"]].assign(
        dicke=lambda d: d["dicke_m"].map(lambda w: f"{m_in_cm(w):.2f}"))
    auf = auf.drop(columns="dicke_m").rename(columns={
        "variante": "Variante", "position": "Pos.", "schicht": "Schicht", "material": "Material",
        "dicke": "Dicke [cm]"})
    teile.append(_tabelle(auf, {"Pos.", "Dicke [cm]"}))

    # 3 Ergebnisse
    karten = []
    for _, z in var.iterrows():
        f = k.farben.get(z["variante"], "#3DD6B5")
        karten.append(
            f"<div class='karte' style='--f:{f}'><b>{html.escape(z['variante'])}</b>"
            f"<div class='kz'><span>GWP</span><span>{z[spalte('gwp', 'summe')]:.1f} {GWP}</span></div>"
            f"<div class='kz'><span>PENRT</span><span>{z[spalte('penrt', 'summe')]:,.0f} {PENRT}"
            f"</span></div>".replace(",", " ")
            + f"<div class='kz'><span>Lebenszykluskosten</span><span>{z['lcc_summe_eur_m2']:.1f} "
              f"{EUR}</span></div>"
              f"<div class='kz'><span>U / Masse</span><span>{z['u_nachher_w_m2k']:.3f} W/(m²K) · "
              f"{z['masse_kg_m2']:.0f} kg/m²</span></div>"
            + (f"<div class='hinweis'>geschätzte Werte: {html.escape(z['geschaetzt'])}</div>"
               if z["geschaetzt"] else "") + "</div>")
    teile += ["<h2>3 Ergebnisse je m² Wand</h2>", f"<div class='karten'>{''.join(karten)}</div>"]
    for kr, (name, einheit) in KRITERIUM_NAMEN.items():
        teile += [f"<p><b>{name}</b> [{einheit}], Modul D getrennt</p>",
                  diagramm(gestapelt(var, kr, True, einheit))]

    # 4 Gesamtbewertung
    bew = k.bewertung()
    if bew is not None:
        g = k.gewichte
        tab = bew.assign(**{c: bew[c].map(lambda w: f"{w:.0f}") for c in
                            ("punkte_gwp", "punkte_penrt", "punkte_lcc", "punkte_gesamt")})
        tab = tab[["rang", "variante", "punkte_gwp", "punkte_penrt", "punkte_lcc", "punkte_gesamt"]]
        tab.columns = ["Rang", "Variante", "GWP [Punkte]", "PENRT [Punkte]", "Kosten [Punkte]",
                       "Gesamt [Punkte]"]
        teile += ["<h2>4 Gesamtbewertung</h2>",
                  f"<p>Punkte relativ zur besten Variante (beste = 100, 20 % schlechter = 80). "
                  f"Gewichte GWP / PENRT / Kosten = {g['gwp']:g} / {g['penrt']:g} / {g['lcc']:g}.</p>",
                  _tabelle(tab, set(tab.columns[2:]) | {"Rang"})]

    # 5 Optimum
    opt = k.optimierung()
    if opt is not None and not opt.optima.empty:
        tol = anteil_in_prozent(k.such.toleranz)
        ot = optimum_tabelle(opt.optima).T.reset_index().rename(columns={"index": "Größe"})
        teile += ["<h2 class='seitenumbruch'>5 Optimale Dämmdicke (Modus gleicher U-Wert)</h2>",
                  f"<p>Dicke der anpassbaren Schicht {m_in_cm(k.such.d_min_m):.0f}–"
                  f"{m_in_cm(k.such.d_max_m):.0f} cm variiert; Bereich = Summe höchstens "
                  f"{tol:g} % über dem Minimum.</p>", _tabelle(ot)]
        for kr, (name, einheit) in KRITERIUM_NAMEN.items():
            teile += [f"<p><b>Summe {name}</b> [{einheit}] über der Dicke, Punkt = Optimum</p>",
                      diagramm(optimum_vergleich(opt.verlauf, opt.optima, kr, k.farben, einheit,
                                                 hoehe=260))]
        for v, liste in opt.hinweise.items():
            teile += [f"<p class='hinweis'>{html.escape(v)}: {html.escape(h)}</p>" for h in liste]

    # 6 Robustheit
    sens = k.sensitivitaet()
    if sens is not None and not sens.ergebnis.empty:
        teile.append("<h2>6 Robustheit (Modus gleicher U-Wert)</h2><p>Jede Größe einzeln um die angegebene Spanne "
                     "verschoben. Gezeigt: die drei größten Hebel je Variante und Kriterium.</p>")
        zeilen = []
        for v in var["variante"]:
            for kr, (name, einheit) in KRITERIUM_NAMEN.items():
                h = hebel(sens, v, kr).head(3)
                for _, z in h.iterrows():
                    zeilen.append({"Variante": v, "Kriterium": name,
                                   "Größe (± Spanne)": f"{z['groesse']} (±{anteil_in_prozent(z['spanne']):.0f} %)",
                                   f"Änderung −": f"{z['minus']:+.1f} {einheit}",
                                   f"Änderung +": f"{z['plus']:+.1f} {einheit}"})
        teile.append(_tabelle(pd.DataFrame(zeilen), {"Änderung −", "Änderung +"}))
        geaendert = sens.rangwechsel[sens.rangwechsel["geaendert"]]
        if geaendert.empty:
            teile.append("<p><b>Rangfolge stabil:</b> In keinem Fall ändert sich die Reihenfolge "
                         "der Varianten.</p>")
        else:
            teile.append("<p><b>Rangfolge ändert sich in diesen Fällen:</b></p>" + _tabelle(
                geaendert[["groesse", "richtung", "kriterium", "rangfolge"]].rename(columns={
                    "groesse": "Größe", "richtung": "Richtung", "kriterium": "Kriterium",
                    "rangfolge": "neue Rangfolge"})))

    # 7 Hinweise
    hinweise = [f"{v}: {h}" for v, liste in erg.hinweise.items() for h in liste]
    hinweise += [f"{v}: {t}" for v, t in erg.fehler.items()]
    teile.append("<h2>7 Hinweise und Grenzen</h2><ul>" + "".join(
        f"<li>{html.escape(h)}</li>" for h in hinweise) + """
<li>Im Modus „gleiche Wanddicke“ sind die Varianten thermisch nicht gleichwertig; B6 ist nur
vereinfacht über Heizgradstunden abgebildet.</li>
<li>Inhomogene Schichten mit flächengemitteltem λ (vereinfacht), keine Wärmebrücken,
kein Gesamtgebäude.</li>
<li>Kosten: Herkunft und Status je Variante siehe Kennzeichnung „enthält geschätzte Werte“.</li>
<li>Kennwerte: ÖKOBAUDAT, Nutzungsdauern: BBSR; Quellen je Wert in daten/.</li></ul>""")
    teile.append("<div class='fuss'>LCE-Tool · TH Köln, Modul Life-Cycle-Engineering</div>")

    skripte = "".join(
        f"vegaEmbed('#{nr}', {json.dumps(spec)}, {{actions:false, renderer:'svg'}});"
        for nr, spec in diagramme)
    kopf = (f"<script src='https://cdn.jsdelivr.net/npm/vega@{alt.VEGA_VERSION}'></script>"
            f"<script src='https://cdn.jsdelivr.net/npm/vega-lite@{alt.VEGALITE_VERSION}'></script>"
            f"<script src='https://cdn.jsdelivr.net/npm/vega-embed@{alt.VEGAEMBED_VERSION}'></script>")
    return (f"<!doctype html><html lang='de'><head><meta charset='utf-8'>"
            f"<title>{html.escape(titel)}</title><style>{CSS}</style>{kopf}</head><body>"
            f"{''.join(teile)}<script>{skripte}</script></body></html>")
