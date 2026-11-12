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

    print("\nAufbauten (Schichten innen → außen):")
    for variante, schichten in daten["aufbauten.csv"].groupby("variante", sort=False):
        print(f"  {variante}")
        for _, s in schichten.iterrows():
            marke = "  (anpassbar)" if s["anpassbar"] == 1 else ""
            print(f"    {s['position']:>2}  {s['schicht']:<36}{s['material']:<26}"
                  f"{m_in_cm(s['dicke_m']):>7.2f} cm{marke}")

    print("\nEinträge mit Status „geschätzt“:")
    for datei, anzahl in zaehle_geschaetzt(daten).items():
        print(f"  {datei:<22}{anzahl:>4}")

    if ergebnis.hinweise:
        print(f"\nHinweise ({len(ergebnis.hinweise)}):")
        for meldung in ergebnis.hinweise:
            print(f"  - {meldung}")
