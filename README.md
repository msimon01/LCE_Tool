# LCE-Tool – Variantenvergleich Außenwand

Werkzeug aus dem Modul Life-Cycle-Engineering (TH Köln). Vergleicht für die Vor- und
Entwurfsplanung mehrere Außenwandaufbauten bei gleichem U-Wert nach GWP, PENRT und
Lebenszykluskosten und ermittelt je Variante die optimale Dämmdicke. Vorstufe zu eLCA, kein Ersatz.

## Start

Einmalig im Projektordner: `pip install -r requirements.txt`

| Was | Wie |
|---|---|
| Oberfläche | Doppelklick auf **start.bat** (macOS: start.command), öffnet http://localhost:8501 |
| Oberfläche von Hand | `python -m streamlit run app.py` |
| Konsole + CSV | `python main.py` (schreibt ergebnisse/*.csv) |
| Tests | `pytest` |

## Abhängigkeiten

- Python 3.11 bis 3.14 (getestet mit 3.11, 3.12 und 3.14; der Code nutzt nichts, was es nur in
  3.14 gibt – die Untergrenze 3.11 kommt von numpy 2.3.5)
- feste Versionen in requirements.txt: streamlit, pandas, numpy, altair, pytest

## Struktur

| Pfad | Inhalt |
|---|---|
| app.py | Oberfläche (Streamlit): Daten laden, Seitenleiste, Navigation |
| seiten/ | Seiten der Oberfläche: Übersicht, Verlauf über die Zeit, Zielkonflikt, Optimale Dämmdicke, Robustheit, Details, Aufbauten, Projekt/Bericht/Export, Hilfe |
| oberflaeche/ | gemeinsamer Zustand, Diagramme (Altair), Farben und Stil, Projektdatei, HTML-Bericht, Zugangsschutz |
| main.py | Konsolenstart |
| lce/ | Rechenkern ohne Bezug zu Ausgabe oder Oberfläche |
| lce/einheiten.py | einzige Stelle für Einheitenumrechnungen |
| lce/daten_laden.py | CSV einlesen und prüfen |
| lce/waermeschutz.py | U-Wert, Anpassung der Dämmdicke an den Ziel-U-Wert |
| lce/masse.py | flächenbezogene Masse |
| lce/oekobilanz.py | GWP/PENRT A1–A3, B4, C3, C4, D, Betrieb B6 |
| lce/kosten.py | Lebenszykluskosten als Barwert |
| lce/berechnung.py | Gesamtablauf je Variante, Einstellungen |
| lce/optimierung.py | optimale Dicke der anpassbaren Schicht (GWP, PENRT, LCC) |
| lce/sensitivitaet.py | Robustheit: Eingangsgrößen einzeln ± Spanne, Hebel und Rangfolge |
| lce/verlauf.py | kumulierter Verlauf GWP/PENRT je Jahr, Schnittpunkte der Varianten |
| lce/abwaegung.py | Zielkonflikt: nicht übertroffene Varianten, Robustheits-Ampel |
| lce/bewertung.py | gewichtete Gesamtbewertung (Punkte relativ zur besten Variante) |
| ausgabe/ | Konsole, CSV (Dezimalkomma, UTF-8 mit BOM), Anzeigenamen mit Einheiten |
| tests/ | pytest; tests/testdaten/ ist eine feste Kopie von daten/ für die Sollwerte |
| ergebnisse/ | erzeugte CSV (nicht versioniert) |
| .streamlit/config.toml | Streamlit-Einstellungen und dunkles Design (Farben, Rundungen) |
| daten/, prompts/, validierung/, protokoll.xlsx | von uns gepflegt, vom Code nur gelesen |

## Festlegungen

- Standard-Energieträger = erste Zeile in energietraeger.csv (Erdgas). Strom: Emissionsfaktor
  aus strom_szenario.csv linear interpoliert, nach dem letzten Stützjahr konstant.
- Austauschhäufigkeit: Aufrunden (Standard) oder kaufmännisch runden, wählbar.
- Modul D nur für den Erstaufbau, immer getrennt; Summen = A1–A3 + B4 + C3 + C4 + B6.
- Kosten aus kosten.csv je cm bei 100 % Anteil, bei inhomogenen Schichten mit dem Anteil gewichtet.
- Aufbauten lassen sich in der Oberfläche bearbeiten (nur Sitzung) und als CSV herunterladen.
- Optimum: Dicke der ersten anpassbaren Schicht wird von `optimierung_d_min_m` bis
  `optimierung_d_max_m` in Schritten von `optimierung_schritt_m` variiert (parameter.csv).
  Optimaler Bereich = Summe ≤ Minimum + `optimierung_toleranz` · |Minimum|, zusammenhängend um
  das Minimum. Konstruktionsanteile linear in d, Betriebsanteile proportional zu U; das wird je
  Variante an zwei Zwischenpunkten gegen die vollständige Rechnung geprüft, sonst wird jede
  Dicke vollständig gerechnet. Fehlen die Parameter, läuft alles andere normal weiter.

- Robustheit: Spannen `sensitivitaet_*` in parameter.csv; Kosten, Energiepreis, Zins/Preissteigerung,
  Nutzungsdauern ±20 %, Kennwerte, Energiefaktoren, Heizgradstunden ±10 %. Ziel-U bleibt fest.
- Gesamtbewertung: Gewichte `bewertung_gewicht_*` in parameter.csv, in der Seitenleiste änderbar.
- Projektdatei (.json): Aufbauten, Auswahl, Randbedingungen, Suchbereich, Gewichte; daten/ unverändert.
- Bericht: HTML-Seite, im Browser als PDF drucken; Diagramme brauchen beim Öffnen Internet (Vega-Lite).

- Verlauf: Jahr 0 = A1–A3, B4 im Austauschjahr k · ND (gleiche Austauschzahl wie im Ergebnis),
  B6 je Jahr (Strom mit Faktor des Jahres), Rückbau C3 + C4 als Punkt nach dem letzten Jahr,
  D nicht in der Kurve. Letzter Punkt = Summe der Übersicht. Schnittpunkte linear interpoliert.

- Zielkonflikt: „übertroffen“ = eine andere Variante ist in beiden Größen (GWP bzw. PENRT und
  Lebenszykluskosten) mindestens gleich gut und in einer besser. Ampel aus allen Fällen der
  Robustheitsprüfung (je Annahme unterer und oberer Wert): grün = immer, gelb = teilweise,
  rot = nie nicht übertroffen. Gewichtete Gesamtbewertung unverändert.
- Vergleichsmodus „gleiche Wanddicke“ (`ziel_wanddicke_m` in parameter.csv): die anpassbare
  Schicht füllt die Zielwanddicke, der U-Wert ergibt sich daraus (DIN EN ISO 6946).
  **Die Varianten sind in diesem Modus thermisch nicht gleichwertig, und B6 ist nur vereinfacht
  über die Heizgradstunden abgebildet** (Q = U · Gt, keine Gebäudebilanz). Nicht erreichbare
  Zielwanddicke = Fehler für die Variante. Optimale Dämmdicke und Robustheit (und damit die
  Ampel) rechnen immer im Modus „gleicher U-Wert“. Der Modus steht in jeder Ausgabe
  (Spalte `vergleichsmodus`, einstellungen.csv, Seitentitel, Bericht, Konsole).

## Online-Bereitstellung (Streamlit Community Cloud)

Ziel: Die Oberfläche läuft ohne Installation im Browser (Link bzw. QR-Code, auch auf dem Handy).

**Startdatei:** `app.py` · **Python:** 3.12 (beim Bereitstellen unter „Advanced settings“
wählen; lässt sich danach nur durch Löschen und Neuanlegen der App ändern) · **Pakete:**
`requirements.txt` (feste Versionen, laufen mit Python 3.11 bis 3.14).

**Was auf GitHub gehört:**
`app.py`, `main.py`, `lce/`, `ausgabe/`, `oberflaeche/`, `seiten/`, `daten/`, `tests/`,
`requirements.txt`, `pytest.ini`, `.streamlit/config.toml`, `README.md`, `.gitignore`,
`start.bat`, `start.command`. Ob `prompts/`, `protokoll.xlsx` und `validierung/` mit hochgeladen
werden, entscheiden wir (bei einem öffentlichen Repository sind sie für alle sichtbar).

**Was nicht auf GitHub gehört** (steht in `.gitignore`):
`ergebnisse/*` (wird erzeugt), `__pycache__/`, `.pytest_cache/`, `.venv/`, `Claude outputs/`,
`.streamlit/secrets.toml`, lizenzierte Unterlagen (Normen als PDF, BKI-Daten). Werden die
Kosten später durch BKI-Werte ersetzt, dürfen diese nicht in ein öffentliches Repository.

**Verhalten auf dem Server:**
- Pfade werden immer relativ zum Projektordner gebildet (`Path(__file__)`), der Startordner
  spielt keine Rolle.
- Die Oberfläche speichert nichts auf dem Server. Ergebnisse (CSV), Bericht (HTML) und
  Projektdatei (JSON) gibt es zum Herunterladen. Der Knopf „in ergebnisse/ speichern“
  erscheint nur, wenn der Ordner beschreibbar ist (lokal). `python main.py` schreibt wie bisher
  nach `ergebnisse/` (Validierung).
- Jede Person hat eine eigene Sitzung: geänderte Aufbauten und Einstellungen gelten nur dort.
- Rechnungen werden zwischengespeichert (`st.cache_data`, je Funktion höchstens 64 Einträge,
  2 h): gleiche Eingaben werden nicht neu gerechnet, auch nicht für andere Nutzer. Optimum und
  Robustheit laufen nur, wenn ihre Seite (bzw. Zielkonflikt oder Bericht) geöffnet wird.

**Zweig „praesentation“:** Die Online-Version läuft aus einem eigenen Branch `praesentation`.
Gearbeitet wird auf `main`; `praesentation` wird nur nach bestandener Abnahme (alle Tests grün,
Prompt abgenommen und im Protokoll) auf den Stand von `main` gebracht. So ändert sich die
verlinkte Version nicht während der Entwicklung.

**Später einmalig einrichten (nicht Teil dieses Schritts):**
1. Repository auf GitHub anlegen und den Projektordner hochladen (`main`).
2. Branch `praesentation` aus `main` anlegen.
3. Auf share.streamlit.io mit dem GitHub-Konto anmelden → „Create app“ → Repository,
   Branch `praesentation`, Datei `app.py`, unter „Advanced settings“ Python 3.12 wählen.
4. Die vergebene Adresse als Link bzw. QR-Code weitergeben.

## Zugangsschutz und geschützte Kosten (Secrets)

Lizenzierte Werte (z. B. BKI-Kosten) dürfen nicht in das öffentliche Repository. Dafür nutzt
das Tool Streamlit-Secrets; beides ist optional:

- **Passwort** (`[zugang] passwort`): Die Oberfläche zeigt zuerst nur eine Passwortabfrage.
  Link und QR-Code bleiben gleich, wer das Passwort kennt, kommt hinein. Die Anmeldung gilt
  für die Sitzung im Browser. Es ist ein gemeinsames Passwort, keine persönliche Anmeldung.
- **Kosten** (`[daten] kosten_csv`): Inhalt einer Kosten-CSV im Format von `daten/kosten.csv`.
  Ist er gesetzt, nutzt die Oberfläche diese Kosten statt `daten/kosten.csv`, mit derselben
  Prüfung wie beim Laden der Datei. Die Kosten-Tabelle wird dann auf der Seite
  „Projekt, Bericht & Export“ nicht angezeigt. Die Ergebnisse (und deren CSV-Downloads)
  enthalten die daraus gerechneten Kosten weiterhin – deshalb zusammen mit dem Passwort nutzen.
- `daten/kosten.csv` im Repository enthält nur eigene Schätzwerte; `main.py` und die Tests
  verwenden diese Datei.

**Einrichten online:** share.streamlit.io → App → **⋮ → Settings → Secrets** → Inhalt nach
der Vorlage `.streamlit/secrets.toml.beispiel` einfügen → **Save**. Die App startet neu.
**Lokal testen:** die Vorlage als `.streamlit/secrets.toml` kopieren und ausfüllen
(steht in `.gitignore`, wird nie hochgeladen). Was einmal in einem öffentlichen Repository
committet wurde, bleibt in der Versionsgeschichte – lizenzierte Werte daher nie in `daten/`.

## Versionsverlauf

| Prompt | Datum | Änderung |
|---|---|---|
| P00 | 12.11.2026 | Regeln, Strukturvorschlag |
| P01 | 12.11.2026 | Grundgerüst; alle CSV laden und prüfen (Pflichtspalten, leere Werte, Zahlen, Materialverweise, Anteile inhomogener Schichten, anpassbar, dicke_m); Konsolenübersicht |
| P01a | 12.11.2026 | Prüfung auf doppelte Schlüssel (IDs, Parameter, Jahre, Position je Variante) |
| P02 | 12.11.2026 | Flächenbezogene Masse je Schicht und Variante; erste CSV-Ausgabe ergebnisse/masse.csv; Schichtliste aus P01 in der Konsole entfernt (doppelt zur Massentabelle) |
| P03–P05 | 13.11.2026 | Wärmeschutz (Dämmdicke auf Ziel-U), Ökobilanz inkl. B4/B6, Lebenszykluskosten, Streamlit-Oberfläche, start.bat; Rechentests auf tests/testdaten/ |
| E01 | 13.11.2026 | Optimale Dämmdicke je Variante (GWP, PENRT, Lebenszykluskosten) mit optimalem Bereich; Reiter „Optimum“, optimum.csv, optimum_verlauf.csv |
| E02 | 13.11.2026 | Oberfläche neu: dunkles Design, Seiten statt Reiter, Kennzahl-Karten mit Abstand zur besten Variante, Rangliste, Wandschnitt, Optimum-Seite mit Variantenvergleich, Hinweise gebündelt |
| E03 | 13.11.2026 | Robustheit (Tornado, Rangfolge), Gesamtbewertung mit Gewichten, Projekt speichern/laden, Bericht als druckfertige HTML-Seite |
| E04 | 16.11.2026 | Kumulierter Verlauf GWP/PENRT über den Betrachtungszeitraum mit Schnittpunkten; Seite „Verlauf über die Zeit“, verlauf.csv; Schalter „Betrieb einbeziehen“ gilt seitenübergreifend |
| E05 | 16.11.2026 | Seite „Zielkonflikt“: Punktwolke GWP/PENRT gegen Lebenszykluskosten, nicht übertroffene Varianten, Robustheits-Ampel |
| E06 | 16.11.2026 | Vergleichsmodus „gleiche Wanddicke“ mit Zielwanddicke, U-Wert je Variante, Rangfolge beider Modi; Modus in allen Ausgaben gekennzeichnet |
| E07 | 18.11.2026 | Vorbereitung Online-Bereitstellung: feste Paketversionen (Python 3.11–3.14), Speichern nur optional, Zwischenspeicher für Rechnungen, Handy-Darstellung, README-Abschnitt Online-Bereitstellung |
| E08 | 18.11.2026 | Passwortschutz der Oberfläche und Kosten aus Streamlit-Secret (für lizenzierte Werte), Vorlage .streamlit/secrets.toml.beispiel |
