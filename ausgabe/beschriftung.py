"""Anzeigenamen mit Einheit für Ergebnisspalten (Konsole und Oberfläche)."""

from __future__ import annotations

from lce.einheiten import m_in_cm

GWP = "kg CO₂e/m²"
PENRT = "MJ/m²"
EUR = "€/m²"

MODULNAMEN = {"a1a3": "A1–A3 Herstellung", "b4": "B4 Ersatz", "c3": "C3 Abfallbehandlung",
              "c4": "C4 Beseitigung", "b6": "B6 Betrieb", "summe": "Summe (ohne D)",
              "d": "D Gutschrift (getrennt)"}

LCC_NAMEN = {"lcc_herstellung_eur_m2": "Herstellung", "lcc_ersatz_eur_m2": "Ersatz",
             "lcc_rueckbau_eur_m2": "Rückbau", "lcc_heizung_eur_m2": "Heizung",
             "lcc_summe_eur_m2": "Summe"}

# Spalte → (Anzeigename, Nachkommastellen)
VARIANTEN_SPALTEN: dict[str, tuple[str, int]] = {
    "vergleichsmodus": ("Vergleichsmodus", 0),
    "u_vorher_w_m2k": ("U vorher [W/(m²K)]", 3),
    "u_nachher_w_m2k": ("U nachher [W/(m²K)]", 3),
    "angepasste_schicht": ("angepasste Schicht", 0),
    "dicke_vorher_cm": ("Dicke vorher [cm]", 2),
    "dicke_nachher_cm": ("Dicke nachher [cm]", 2),
    "wanddicke_cm": ("Wanddicke [cm]", 1),
    "masse_kg_m2": ("Masse [kg/m²]", 1),
    "q_kwh_m2a": ("Wärmeverlust Q [kWh/(m²a)]", 2),
    "e_kwh_m2a": ("Endenergie E [kWh/(m²a)]", 2),
    **{f"gwp_{m}_kg_co2e_m2": (f"GWP {n} [{GWP}]", 1) for m, n in MODULNAMEN.items()},
    **{f"penrt_{m}_mj_m2": (f"PENRT {n} [{PENRT}]", 0) for m, n in MODULNAMEN.items()},
    **{s: (f"LCC {n} [{EUR}]", 1) for s, n in LCC_NAMEN.items()},
    "kosten_unvollstaendig": ("Kosten unvollständig", 0),
    "geschaetzt": ("enthält geschätzte Werte", 0),
}

SCHICHT_SPALTEN: dict[str, tuple[str, int]] = {
    "position": ("Pos.", 0),
    "schicht": ("Schicht", 0),
    "material": ("Material", 0),
    "anteil": ("Anteil [-]", 2),
    "dicke_vorher_cm": ("Dicke Katalog [cm]", 2),
    "dicke_cm": ("Dicke [cm]", 2),
    "lambda_schicht_W_mK": ("λ Schicht [W/(mK)]", 4),
    "r_schicht_m2k_w": ("R Schicht [m²K/W]", 3),
    "rohdichte_kg_m3": ("Rohdichte [kg/m³]", 2),
    "masse_kg_m2": ("Masse [kg/m²]", 2),
    "nutzungsdauer_a": ("Nutzungsdauer [a]", 0),
    "austausch_n": ("Austausche N [-]", 0),
    **{f"gwp_{m}_kg_co2e_m2": (f"GWP {m.upper().replace('A1A3', 'A1–A3')} [{GWP}]", 2)
       for m in ("a1a3", "b4", "c3", "c4", "d")},
    **{f"penrt_{m}_mj_m2": (f"PENRT {m.upper().replace('A1A3', 'A1–A3')} [{PENRT}]", 1)
       for m in ("a1a3", "b4", "c3", "c4", "d")},
    "lcc_herstellung_eur_m2": (f"Herstellung [{EUR}]", 2),
    "lcc_ersatz_eur_m2": (f"Ersatz Barwert [{EUR}]", 2),
    "lcc_rueckbau_eur_m2": (f"Rückbau Barwert [{EUR}]", 2),
    "status_oekobilanz": ("Status Ökobilanz", 0),
    "kosten_geschaetzt": ("Kosten geschätzt", 0),
    "kosten_fehlen": ("Kosten fehlen", 0),
}


def mit_cm(df):
    """Ergänzt cm-Spalten für die Anzeige (Umrechnung über lce.einheiten)."""
    df = df.copy()
    for m_spalte in ("dicke_vorher_m", "dicke_nachher_m", "wanddicke_m", "dicke_m"):
        if m_spalte in df.columns:
            df[m_spalte.replace("_m", "_cm", 1) if m_spalte != "dicke_m" else "dicke_cm"] = \
                df[m_spalte].map(lambda w: m_in_cm(w) if w is not None and w == w else w)
    return df


def anzeige(df, spalten: dict[str, tuple[str, int]], index: str | None = None):
    """Wählt Spalten aus, rundet nach Vorgabe und setzt Anzeigenamen."""
    df = mit_cm(df)
    vorhanden = [s for s in spalten if s in df.columns]
    out = df[([index] if index else []) + vorhanden].copy()
    for s in vorhanden:
        stellen = spalten[s][1]
        if out[s].dtype.kind == "f":
            out[s] = out[s].round(stellen)
    out = out.rename(columns={s: spalten[s][0] for s in vorhanden})
    if index:
        out = out.set_index(index)
    return out


KRITERIUM_NAMEN = {"gwp": ("GWP", GWP), "penrt": ("PENRT", PENRT), "lcc": ("Lebenszykluskosten", EUR)}


def optimum_tabelle(optima):
    """Je Variante eine Zeile, je Kriterium Optimum, Bereich und Vergleich mit Ziel-U (gerundet)."""
    import pandas as pd

    from lce.einheiten import anteil_in_prozent

    zeilen = []
    for v, gruppe in optima.groupby("variante", sort=False):
        z = {"Variante": v}
        for _, o in gruppe.iterrows():
            name, einheit = KRITERIUM_NAMEN[o["kriterium"]]
            z[f"{name}: Optimum [cm]"] = round(m_in_cm(o["dicke_opt_m"]), 1)
            rand = " (Rand)" if o["bereich_am_rand"] else ""
            z[f"{name}: Bereich [cm]"] = (f"{m_in_cm(o['dicke_von_m']):.1f} – "
                                          f"{m_in_cm(o['dicke_bis_m']):.1f}{rand}")
            z[f"{name}: Minimum [{einheit}]"] = round(o["wert_opt"], 1)
            if "dicke_ziel_u_m" in o and o["dicke_ziel_u_m"] == o["dicke_ziel_u_m"]:
                z[f"{name}: Mehr bei Ziel-U [%]"] = round(anteil_in_prozent(o["mehr_bei_ziel_u_anteil"]), 1)
        if "dicke_ziel_u_m" in gruppe and gruppe["dicke_ziel_u_m"].notna().any():
            z["Dicke bei Ziel-U [cm]"] = round(m_in_cm(gruppe["dicke_ziel_u_m"].iloc[0]), 1)
        zeilen.append(z)
    return pd.DataFrame(zeilen).set_index("Variante")
