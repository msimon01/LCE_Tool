"""Konsolenausgabe. Nur Darstellung, keine Berechnung."""

from __future__ import annotations

import pandas as pd

from ausgabe.beschriftung import SCHICHT_SPALTEN, VARIANTEN_SPALTEN, anzeige, optimum_tabelle
from lce.daten_laden import Ladeergebnis, zaehle_geschaetzt
from lce.einheiten import anteil_in_prozent, m_in_cm


def zeige_fehler(ergebnis: Ladeergebnis) -> None:
    print(f"FEHLER beim Laden der Daten ({len(ergebnis.fehler)}):")
    for meldung in ergebnis.fehler:
        print(f"  - {meldung}")


def zeige_uebersicht(ergebnis: Ladeergebnis) -> None:
    daten = ergebnis.daten
    assert daten is not None

    print("Daten geladen und geprüft: keine Fehler.\n")
    print("Zeilen je Datei:")
    for datei, df in daten.items():
        print(f"  {datei:<22}{len(df):>4}")
    print()
    print("Einträge mit Status „geschätzt“:")
    for datei, anzahl in zaehle_geschaetzt(daten).items():
        print(f"  {datei:<22}{anzahl:>4}")

    if ergebnis.hinweise:
        print(f"\nHinweise ({len(ergebnis.hinweise)}):")
        for meldung in ergebnis.hinweise:
            print(f"  - {meldung}")


def zeige_masse(schichten, summen) -> None:
    """Masse je Schicht und Variante, 1 Nachkommastelle (nur hier gerundet)."""
    print("\nFlächenbezogene Masse, Schichten innen → außen:")
    for variante, gruppe in schichten.groupby("variante", sort=False):
        print(f"  {variante}")
        for _, s in gruppe.iterrows():
            print(f"    {s['position']:>2}  {s['schicht']:<36}{s['material']:<26}"
                  f"{m_in_cm(s['dicke_m']):>7.2f} cm{s['masse_kg_m2']:>10.1f} kg/m²")
        print(f"    {'Summe':<73}{summen[variante]:>10.1f} kg/m²")


def zeige_einstellungen(einst, energietraeger_name: str, rundung_name: str) -> None:
    print("\nRandbedingungen:")
    print(f"  Vergleichsmodus          {einst.modus_text}")
    print(f"  Ziel-U-Wert              {einst.ziel_u_w_m2k:.3f} W/(m²K)")
    print(f"  Betrachtungszeitraum     {einst.zeitraum_a} a ab {einst.startjahr}")
    print(f"  Heizgradstunden          {einst.heizgradstunden_kkh:g} kKh/a")
    print(f"  Zins / Preisst. Bau / Energie  {einst.zins:.2%} / {einst.preissteigerung_bau:.2%} "
          f"/ {einst.preissteigerung_energie:.2%} pro Jahr")
    print(f"  Energieträger            {energietraeger_name}")
    print(f"  Austauschhäufigkeit      {rundung_name}")


def _tabelle(df: pd.DataFrame) -> str:
    with pd.option_context("display.width", 200, "display.max_columns", 50,
                           "display.max_colwidth", 40):
        return df.to_string()


def zeige_ergebnis(ergebnis) -> None:
    for v, text in ergebnis.fehler.items():
        print(f"\nFEHLER in Variante „{v}“: {text}")
    if ergebnis.varianten.empty:
        return

    vergleich = anzeige(ergebnis.varianten, VARIANTEN_SPALTEN, index="variante").T
    print("\nVariantenvergleich (je m² Wand, über den Betrachtungszeitraum):")
    print(_tabelle(vergleich))

    print("\nDetails je Schicht:")
    for v, gruppe in ergebnis.schichten.groupby("variante", sort=False):
        print(f"\n  {v}")
        weglassen = ("dicke_vorher_cm", "lambda_schicht_W_mK", "r_schicht_m2k_w", "rohdichte_kg_m3",
                     "status_oekobilanz", "kosten_geschaetzt", "kosten_fehlen")
        spalten = {k: w for k, w in SCHICHT_SPALTEN.items()
                   if not k.startswith("penrt_") and k not in weglassen}
        print(_tabelle(anzeige(gruppe, spalten).set_index("Pos.")))

    for v, liste in ergebnis.hinweise.items():
        for h in liste:
            print(f"\nHinweis „{v}“: {h}")


def zeige_optimierung(optimierung, such=None, fehlertext: str | None = None) -> None:
    """Optimale Dicke der anpassbaren Schicht je Variante und Kriterium."""
    print("\nOptimale Dicke der anpassbaren Schicht:")
    if fehlertext:
        print(f"  nicht berechnet: {fehlertext}")
        return
    print(f"  Suchbereich {m_in_cm(such.d_min_m):.1f} – {m_in_cm(such.d_max_m):.1f} cm, "
          f"Schritt {m_in_cm(such.schritt_m):.1f} cm; Bereich = höchstens "
          f"{anteil_in_prozent(such.toleranz):g} % "
          f"über dem Minimum")
    for v, text in optimierung.fehler.items():
        print(f"  FEHLER „{v}“: {text}")
    if not optimierung.optima.empty:
        print(_tabelle(optimum_tabelle(optimierung.optima).T))
    for v, liste in optimierung.hinweise.items():
        for h in liste:
            print(f"  Hinweis „{v}“: {h}")


def zeige_dateien(pfade) -> None:
    print("\nGeschrieben:")
    for p in pfade:
        print(f"  {p}")
