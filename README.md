# LCE-Tool – Variantenvergleich Außenwand

Werkzeug aus dem Modul Life-Cycle-Engineering (TH Köln). Vergleicht für die Vor- und
Entwurfsplanung mehrere Außenwandaufbauten bei gleichem U-Wert nach GWP, PENRT und
Lebenszykluskosten. Vorstufe zu eLCA, kein Ersatz.

## Start

Aus dem Projektordner:

```
pip install -r requirements.txt
python main.py      # lädt und prüft daten/, Übersicht in der Konsole
pytest              # alle Tests
```

## Abhängigkeiten

- Python 3.14
- pandas, pytest (siehe requirements.txt)

## Struktur

| Pfad | Inhalt |
|---|---|
| main.py | Einstieg |
| lce/ | Rechenkern ohne Bezug zur Ausgabe |
| lce/einheiten.py | einzige Stelle für Einheitenumrechnungen |
| lce/daten_laden.py | CSV einlesen und prüfen |
| lce/masse.py | flächenbezogene Masse je Schicht und Variante |
| ausgabe/ | Konsolenausgabe und CSV (Dezimalkomma, UTF-8 mit BOM) |
| tests/ | pytest-Tests, arbeiten mit temporären Kopien von daten/ |
| ergebnisse/ | erzeugte Ergebnisse (nicht versioniert) |
| daten/, prompts/, protokoll.xlsx | von uns gepflegt, vom Code nur gelesen |

## Versionsverlauf

| Prompt | Datum | Änderung |
|---|---|---|
| P00 | 12.11.2026 | Regeln, Strukturvorschlag |
| P01 | 12.11.2026 | Grundgerüst; alle CSV laden und prüfen (Pflichtspalten, leere Werte, Zahlen, Materialverweise, Anteile inhomogener Schichten, anpassbar, dicke_m); Konsolenübersicht |
| P01a | 12.11.2026 | Prüfung auf doppelte Schlüssel (IDs, Parameter, Jahre, Position je Variante) |
| P02 | 12.11.2026 | Flächenbezogene Masse je Schicht und Variante; erste CSV-Ausgabe ergebnisse/masse.csv; Schichtliste aus P01 in der Konsole entfernt (doppelt zur Massentabelle) |
