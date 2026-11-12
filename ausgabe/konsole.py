"""Konsolenausgabe. Nur Darstellung, keine Berechnung."""

from __future__ import annotations

from lce.daten_laden import Ladeergebnis, zaehle_geschaetzt
from lce.einheiten import m_in_cm


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
    print("\nFlächenbezogene Masse, Schichten innen → außen (Dicken unverändert aus aufbauten.csv):")
    for variante, gruppe in schichten.groupby("variante", sort=False):
        print(f"  {variante}")
        for _, s in gruppe.iterrows():
            print(f"    {s['position']:>2}  {s['schicht']:<36}{s['material']:<26}"
                  f"{m_in_cm(s['dicke_m']):>7.2f} cm{s['masse_kg_m2']:>10.1f} kg/m²")
        print(f"    {'Summe':<73}{summen[variante]:>10.1f} kg/m²")


def zeige_datei(pfad) -> None:
    print(f"\nGeschrieben: {pfad}")
