"""Altair-Diagramme der Oberfläche (nur Darstellung)."""

from __future__ import annotations

import altair as alt
import pandas as pd

from ausgabe.beschriftung import LCC_NAMEN
from lce.einheiten import m_in_cm
from lce.oekobilanz import spalte
from lce.optimierung import verlauf_spalte
from oberflaeche.stil import (AKZENT, LCC_FARBEN, MISCHFARBE, MODULFARBEN, OPTIMUM_FARBEN,
                              kategoriefarbe)

MODULE_KURZ = {"a1a3": "A1–A3 Herstellung", "b4": "B4 Ersatz", "c3": "C3 Abfallbehandlung",
               "c4": "C4 Beseitigung", "b6": "B6 Betrieb"}


def _achse_variante(reihenfolge: list[str]) -> alt.Y:
    return alt.Y("variante:N", title=None, sort=reihenfolge,
                 axis=alt.Axis(labelLimit=320, labelFontSize=12, labelPadding=8))


def gestapelt(var: pd.DataFrame, kriterium: str, mit_betrieb: bool, einheit: str) -> alt.Chart:
    """Gestapelte Balken je Variante: Module (GWP/PENRT) bzw. Kostenanteile (LCC)."""
    if kriterium == "lcc":
        teile = {s: LCC_NAMEN[s] for s in LCC_FARBEN
                 if mit_betrieb or s != "lcc_heizung_eur_m2"}
        farben = [LCC_FARBEN[s] for s in teile]
    else:
        module = [m for m in MODULE_KURZ if mit_betrieb or m != "b6"]
        teile = {spalte(kriterium, m): MODULE_KURZ[m] for m in module}
        farben = [MODULFARBEN[m] for m in module]
    reihen = list(teile.values())
    lang = (var.set_index("variante")[list(teile)].rename(columns=teile).reset_index()
            .melt(id_vars="variante", var_name="Anteil", value_name="Wert"))
    lang["reihenfolge"] = lang["Anteil"].map({r: i for i, r in enumerate(reihen)})
    return alt.Chart(lang).mark_bar(cornerRadius=2, height={"band": 0.62}).encode(
        x=alt.X("sum(Wert):Q", title=einheit, axis=alt.Axis(grid=True, gridOpacity=0.15)),
        y=_achse_variante(list(var["variante"])),
        color=alt.Color("Anteil:N", sort=reihen, scale=alt.Scale(domain=reihen, range=farben),
                        legend=alt.Legend(orient="bottom", title=None, columns=3, labelLimit=0)),
        order=alt.Order("reihenfolge:Q"),
        tooltip=["variante", "Anteil", alt.Tooltip("Wert:Q", format=",.1f", title=einheit)],
    ).properties(height=alt.Step(46))


def optimum_zerlegung(verlauf: pd.DataFrame, k: str, o: pd.Series, teil_namen: tuple[str, str],
                      einheit: str, farbe: str = AKZENT, hoehe: int = 380) -> alt.LayerChart:
    """Konstruktion, Betrieb und Summe über der Dicke; Optimum, Bereich und Ziel-U markiert."""
    namen = {verlauf_spalte(k, "konstruktion"): teil_namen[0],
             verlauf_spalte(k, "betrieb"): teil_namen[1],
             verlauf_spalte(k, "summe"): "Summe"}
    df = verlauf.assign(dicke_cm=verlauf["dicke_m"].map(m_in_cm))
    lang = df[["dicke_cm", *namen]].rename(columns=namen).melt(
        id_vars="dicke_cm", var_name="Anteil", value_name="Wert")
    reihen = list(namen.values())
    farben = [OPTIMUM_FARBEN["konstruktion"], OPTIMUM_FARBEN["betrieb"], farbe]
    y_unten = min(0.0, float(lang["Wert"].min()))
    y_oben = 2.0 * abs(float(o["wert_opt"])) if o["wert_opt"] != 0 else float(lang["Wert"].max())
    bereich = pd.DataFrame({"von": [m_in_cm(o["dicke_von_m"])], "bis": [m_in_cm(o["dicke_bis_m"])]})
    ebenen = [
        alt.Chart(bereich).mark_rect(opacity=0.13, color=farbe).encode(x="von:Q", x2="bis:Q"),
        alt.Chart(lang).mark_line(clip=True).encode(
            x=alt.X("dicke_cm:Q", title="Dicke der anpassbaren Schicht [cm]"),
            y=alt.Y("Wert:Q", title=einheit, scale=alt.Scale(domain=[y_unten, y_oben]),
                    axis=alt.Axis(gridOpacity=0.15)),
            color=alt.Color("Anteil:N", sort=reihen, scale=alt.Scale(domain=reihen, range=farben),
                            legend=alt.Legend(orient="bottom", title=None, labelLimit=300)),
            strokeWidth=alt.condition(alt.datum.Anteil == "Summe", alt.value(3.5), alt.value(2)),
            tooltip=[alt.Tooltip("dicke_cm:Q", title="Dicke [cm]", format=".1f"), "Anteil",
                     alt.Tooltip("Wert:Q", title=einheit, format=",.1f")]),
        alt.Chart(pd.DataFrame({"x": [m_in_cm(o["dicke_opt_m"])], "y": [o["wert_opt"]]}))
        .mark_point(size=110, filled=True, color=farbe).encode(x="x:Q", y="y:Q"),
    ]
    if "dicke_ziel_u_m" in o and o["dicke_ziel_u_m"] == o["dicke_ziel_u_m"]:
        ebenen.append(alt.Chart(pd.DataFrame({"x": [m_in_cm(o["dicke_ziel_u_m"])]}))
                      .mark_rule(color="#8B96A5", strokeDash=[5, 4]).encode(x="x:Q"))
    return alt.layer(*ebenen).properties(height=hoehe)


def optimum_vergleich(verlauf: pd.DataFrame, optima: pd.DataFrame, k: str, farben: dict[str, str],
                      einheit: str, hoehe: int = 380) -> alt.LayerChart:
    """Summenkurven aller Varianten, Optimum je Variante als Punkt."""
    s = verlauf_spalte(k, "summe")
    df = verlauf[["variante", "dicke_m", s]].assign(dicke_cm=verlauf["dicke_m"].map(m_in_cm))
    varianten = list(dict.fromkeys(df["variante"]))
    skala = alt.Scale(domain=varianten, range=[farben[v] for v in varianten])
    opt = optima[optima["kriterium"] == k].assign(dicke_cm=lambda d: d["dicke_opt_m"].map(m_in_cm))
    y_oben = 2.0 * float(opt["wert_opt"].abs().max())
    y_unten = min(0.0, float(df[s].min()))
    linien = alt.Chart(df).mark_line(clip=True, strokeWidth=2.5).encode(
        x=alt.X("dicke_cm:Q", title="Dicke der anpassbaren Schicht [cm]"),
        y=alt.Y(f"{s}:Q", title=einheit, scale=alt.Scale(domain=[y_unten, y_oben]),
                axis=alt.Axis(gridOpacity=0.15)),
        color=alt.Color("variante:N", scale=skala,
                        legend=alt.Legend(orient="bottom", title=None, labelLimit=300, columns=1)),
        tooltip=["variante", alt.Tooltip("dicke_cm:Q", title="Dicke [cm]", format=".1f"),
                 alt.Tooltip(f"{s}:Q", title=einheit, format=",.1f")])
    punkte = alt.Chart(opt).mark_point(size=110, filled=True, stroke="#0E1218", strokeWidth=1.5) \
        .encode(x="dicke_cm:Q", y="wert_opt:Q", color=alt.Color("variante:N", scale=skala,
                                                                 legend=None))
    return alt.layer(linien, punkte).properties(height=hoehe)


def wandschnitt(schichten: pd.DataFrame, materialien: pd.DataFrame,
                reihenfolge: list[str]) -> alt.Chart:
    """Maßstäblicher Wandschnitt je Variante (innen links → außen rechts), Farbe nach Kategorie."""
    kat = materialien.set_index("id")["kategorie"].astype(str)
    zusatz: dict[str, str] = {}
    zeilen = []
    for v, gruppe in schichten.groupby("variante", sort=False):
        x = 0.0
        for _, z in gruppe.sort_values("position").iterrows():
            d = m_in_cm(float(z["dicke_m"]))
            ids = [t.split(":")[0].strip() for t in str(z["material"]).split("|")]
            kategorie = kat.get(ids[0], "?") if len(ids) == 1 else " / ".join(
                dict.fromkeys(kat.get(i, "?") for i in ids))
            zeilen.append({"variante": v, "von": x, "bis": x + d, "dicke_cm": d,
                           "schicht": z["schicht"], "material": z["material"],
                           "kategorie": kategorie})
            x += d
    df = pd.DataFrame(zeilen)
    kategorien = list(dict.fromkeys(df["kategorie"]))
    farben = [MISCHFARBE if " / " in k else kategoriefarbe(k, zusatz) for k in kategorien]
    return alt.Chart(df).mark_bar(stroke="#0E1218", strokeWidth=1.2, height={"band": 0.7}).encode(
        x=alt.X("von:Q", title="innen → außen [cm]", axis=alt.Axis(gridOpacity=0.12)),
        x2="bis:Q",
        y=_achse_variante(reihenfolge),
        color=alt.Color("kategorie:N", scale=alt.Scale(domain=kategorien, range=farben),
                        legend=alt.Legend(orient="bottom", title=None, columns=6)),
        tooltip=["variante", "schicht", "material",
                 alt.Tooltip("dicke_cm:Q", title="Dicke [cm]", format=".2f")],
    ).properties(height=alt.Step(52))


def tornado(h: pd.DataFrame, einheit: str, farbe_minus: str = "#5B9BF0",
            farbe_plus: str = "#E86A92") -> alt.Chart:
    """Tornado-Diagramm: Abweichung zum Basisfall bei − und + Spanne, größter Hebel oben."""
    reihen = list(h["groesse"])
    lang = pd.concat([
        h.assign(Fall=lambda d: "− " + d["spanne"].map(lambda s: f"{s:.0%}"), wert=h["minus"],
                 richtung="weniger"),
        h.assign(Fall=lambda d: "+ " + d["spanne"].map(lambda s: f"{s:.0%}"), wert=h["plus"],
                 richtung="mehr"),
    ])
    balken = alt.Chart(lang).mark_bar(cornerRadius=2, height={"band": 0.6}).encode(
        x=alt.X("wert:Q", title=f"Änderung gegenüber Basisfall [{einheit}]",
                axis=alt.Axis(gridOpacity=0.15)),
        y=alt.Y("groesse:N", title=None, sort=reihen, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("richtung:N", scale=alt.Scale(domain=["weniger", "mehr"],
                                                       range=[farbe_minus, farbe_plus]),
                        legend=alt.Legend(orient="bottom", title="Eingangsgröße")),
        tooltip=[alt.Tooltip("groesse:N", title="Größe"), "Fall",
                 alt.Tooltip("wert:Q", title=einheit, format="+,.1f")])
    null = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#8B96A5").encode(x="x:Q")
    return alt.layer(balken, null).properties(height=alt.Step(34))


def kumuliert(df: pd.DataFrame, wert: str, farben: dict[str, str], einheit: str, zeitraum_a: int,
              kreuzungen: pd.DataFrame | None = None, hoehe: int = 420) -> alt.LayerChart:
    """Kumulierter Verlauf je Variante über die Zeitpunkte 0 (Bau) … T + 1 (Rückbau)."""
    varianten = list(dict.fromkeys(df["variante"]))
    skala = alt.Scale(domain=varianten, range=[farben[v] for v in varianten])
    rueckbau = zeitraum_a + 1
    beschriftung = (f"datum.value == 0 ? 'Bau' : datum.value == {rueckbau} ? 'Rückbau' : "
                    f"datum.value")
    x = alt.X("zeitpunkt:Q", title="Jahr der Nutzung",
              scale=alt.Scale(domain=[0, rueckbau], nice=False),
              axis=alt.Axis(labelExpr=beschriftung, values=sorted({0, rueckbau, *range(10, rueckbau, 10)}),
                            gridOpacity=0.12))
    # step-after: ein Austausch im Jahr t erscheint als senkrechte Stufe bei t
    linien = alt.Chart(df).mark_line(strokeWidth=2.6, interpolate="step-after").encode(
        x=x, y=alt.Y(f"{wert}:Q", title=einheit, axis=alt.Axis(gridOpacity=0.15)),
        color=alt.Color("variante:N", scale=skala,
                        legend=alt.Legend(orient="bottom", title=None, labelLimit=300)),
        tooltip=["variante", alt.Tooltip("zeitpunkt:Q", title="Zeitpunkt"), "art",
                 alt.Tooltip(f"{wert}:Q", title=einheit, format=",.1f")])
    punkte = alt.Chart(df[df["art"] != "Nutzung"]).mark_point(filled=True, size=55).encode(
        x="zeitpunkt:Q", y=f"{wert}:Q", color=alt.Color("variante:N", scale=skala, legend=None))
    ebenen = [linien, punkte]
    if kreuzungen is not None and not kreuzungen.empty:
        k = kreuzungen.assign(text=kreuzungen["zeitpunkt"].map(
            lambda z: "Schnitt beim Rückbau" if z > zeitraum_a else f"Schnitt Jahr {z:.1f}"))
        ebenen.append(alt.Chart(k).mark_rule(color="#C9D1D9", strokeDash=[4, 4]).encode(x="zeitpunkt:Q"))
        ebenen.append(alt.Chart(k).mark_text(align="left", dx=4, dy=-6, color="#C9D1D9",
                                             fontSize=11).encode(x="zeitpunkt:Q", y=alt.value(12),
                                                                 text="text:N"))
    return alt.layer(*ebenen).properties(height=hoehe)


def zielkonflikt(df: pd.DataFrame, farben_punkt: dict[str, str], farben_variante: dict[str, str],
                 x_titel: str, y_titel: str, hoehe: int = 440) -> alt.LayerChart:
    """Punktwolke: x = GWP oder PENRT, y = Lebenszykluskosten. Punktfarbe = Ampel,
    Ring = Variantenfarbe, nicht übertroffene Varianten groß und durch eine Linie verbunden."""
    d = df.assign(punktfarbe=df["variante"].map(farben_punkt),
                  ringfarbe=df["variante"].map(farben_variante),
                  status=df["nicht_uebertroffen"].map({True: "nicht übertroffen",
                                                      False: "übertroffen"}),
                  groesse=df["nicht_uebertroffen"].map({True: 420, False: 170}))
    pad_x = (d["x"].max() - d["x"].min()) * 0.15 or abs(d["x"].max()) * 0.1 or 1
    pad_y = (d["y"].max() - d["y"].min()) * 0.15 or abs(d["y"].max()) * 0.1 or 1
    x = alt.X("x:Q", title=x_titel, scale=alt.Scale(domain=[d["x"].min() - pad_x, d["x"].max() + pad_x],
                                                   zero=False), axis=alt.Axis(gridOpacity=0.15))
    y = alt.Y("y:Q", title=y_titel, scale=alt.Scale(domain=[d["y"].min() - pad_y, d["y"].max() + pad_y],
                                                   zero=False), axis=alt.Axis(gridOpacity=0.15))
    front = d[d["nicht_uebertroffen"]].sort_values("x")
    ebenen = []
    if len(front) > 1:
        ebenen.append(alt.Chart(front).mark_line(strokeDash=[6, 4], color="#8B96A5").encode(x=x, y=y))
    ebenen += [
        alt.Chart(d).mark_point(filled=True, opacity=1, strokeWidth=3).encode(
            x=x, y=y, size=alt.Size("groesse:Q", legend=None, scale=None),
            fill=alt.Fill("punktfarbe:N", scale=None), stroke=alt.Stroke("ringfarbe:N", scale=None),
            tooltip=["variante", "status", alt.Tooltip("x:Q", title=x_titel, format=",.1f"),
                     alt.Tooltip("y:Q", title=y_titel, format=",.1f")]),
        alt.Chart(d).mark_text(align="left", dx=16, dy=-2, fontSize=12, color="#E6EDF3").encode(
            x=x, y=y, text="variante:N"),
    ]
    return alt.layer(*ebenen).properties(height=hoehe)
