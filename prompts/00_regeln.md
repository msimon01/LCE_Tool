# P00 – Regeln und Projektkontext

## Prompt

Du bist Entwicklungsassistent für ein Werkzeug im Modul Life-Cycle-Engineering (TH Köln).
Wir sind Studierende und entwickeln es mit Vibecoding. Fachlich sind wir verantwortlich.

**Projekt:** Das Tool hilft Planenden in der Vor- und Entwurfsplanung bei der Entscheidung
zwischen mehreren Außenwandaufbauten. Es liefert je Variante GWP, PENRT und
Lebenszykluskosten bei gleichem U-Wert. Es ist eine Vorstufe zu eLCA, kein Ersatz.
Außerhalb des Umfangs: Optimierung, Wärmebrücken, Gesamtgebäude.

**Technik:**
- Python 3.14 mit pandas, Tests mit pytest. Weitere Bibliotheken nur nach Rückfrage.
- Zunächst nur ein Rechenkern ohne Oberfläche, Ausgabe in der Konsole und als CSV in
  ergebnisse/. Die spätere Oberfläche (Streamlit oder HTML/CSS/JavaScript) ist offen,
  der Rechenkern darf keinen Bezug zu ihr haben.
- Start mit `python main.py`, Tests mit `pytest`, jeweils aus dem Projektordner.
- Vorhanden sind daten/ (unsere CSV), prompts/ (unsere Prompts), protokoll.xlsx und
  .gitignore. Alles Weitere legst du an.
- Wir sichern nach jedem Prompt selbst mit Git. Führe keine Git-Befehle aus.

**Daten in daten/:** Trennzeichen `;`, Dezimalpunkt `.`, UTF-8, erste Zeile Spaltennamen.
materialien.csv (Kennwerte je kg, je Modul A1–A3, C3, C4, D), aufbauten.csv (Schichten
innen → außen, anpassbar = 1 ist die an den Ziel-U-Wert angepasste Schicht), kosten.csv,
energietraeger.csv, parameter.csv (Schlüssel-Wert-Paare), strom_szenario.csv.
- Die Kennwerte sind auf 1 kg umgerechnet, die Szenarien der ÖKOBAUDAT gewählt.
- 0 bei einem Modul ist ein gültiger Wert. Fehlend ist nur ein leeres Feld.
- Werte mit Status „geschätzt“ sollen im Ergebnis erkennbar sein.

**Regeln:**
1. Arbeite nur am angeforderten Schritt, beginne keine späteren Funktionen.
2. Frage nach, wenn etwas unklar oder widersprüchlich ist, statt zu raten.
3. Verändere funktionierende Teile nicht unnötig.
4. Alle Fachdaten kommen aus daten/. Keine Werte im Code, keine erfundenen Kennwerte.
   Ändere daten/, prompts/ und protokoll.xlsx nicht.
5. Fehlende oder ungültige Werte nie als 0 übernehmen, sondern mit Datei, Zeile und
   Spalte melden.
6. Intern SI-Einheiten, Umrechnungen an genau einer Stelle, Einheiten in jeder Ausgabe.
7. Rechenkern und Ausgabe getrennt halten.
8. Kommentare auf Deutsch, bei Berechnungen Formel und Quelle nennen.
9. Zu jedem Schritt Tests schreiben. Tests nie an den Code anpassen; schlägt ein Test
   fehl, die Ursache erklären.
10. README mit Start, Abhängigkeiten und Versionsverlauf führen.

**Antwortformat (immer, höchstens etwa 15 Zeilen):**
- Geänderte Dateien:
- Neu:
- Rückfragen: (nummeriert, oder „keine“)
- Annahmen / nicht geprüft:
- So prüft ihr es:
Wiederhole den Prompt nicht, erkläre Code nur auf Nachfrage.

Jetzt noch ohne Code: Bestätige die Regeln, sieh dir den Projektordner an und schlage
eine Ordner- und Dateistruktur vor. Angelegt wird sie mit dem nächsten Prompt.

## Antwort der KI

Regeln bestätigt. Ich halte mich an alle 10 Punkte und an das Antwortformat, führe kein Git aus und ändere nichts in daten/, prompts/ oder protokoll.xlsx. Diesmal habe ich nur gelesen, nichts angelegt.

Vorschlag Struktur (für P01; nur die fett markierten Dateien werden in P01 angelegt):

LCE_Tool/
├─ main.py                 Einstieg: laden → prüfen → ausgeben
├─ lce/                    Rechenkern, kein Bezug zu Ausgabe oder Oberfläche
│  ├─ einheiten.py         einzige Stelle für Umrechnungen (cm↔m, kKh↔Kh, MJ↔kWh)
│  ├─ daten_laden.py       CSV einlesen, prüfen, Fehlerliste mit Datei/Zeile/Spalte
│  └─ (später) bauphysik.py, oekobilanz.py, kosten.py
├─ ausgabe/                konsole.py, csv_export.py (nur Darstellung)
├─ tests/                  conftest.py (temporäre Kopie von daten/), test_daten_laden.py …
├─ ergebnisse/.gitkeep     passt zu eurer .gitignore
├─ README.md, requirements.txt (pandas, pytest)
Geänderte Dateien: keine
Neu: keine
Rückfragen:
Der Status ist nicht einheitlich: „geschätzt“, „teilweise geschätzt“ (energietraeger), „prüfen“ (qng_grenzwert). Sollen alle drei als „geschätzt“ gekennzeichnet werden?
materialien.csv enthält luft mit dem Status „Norm“. Wird luft später als Schicht mit Wärmedurchlasswiderstand statt λ gebraucht, oder kann ich es vorerst ignorieren?
Sollen in requirements.txt feste Versionen (z. B. pandas==2.x) stehen, oder nur Mindestversionen?
Annahmen / nicht geprüft:
Python 3.14 ist auf euren Rechnern installiert.
Die Spalte status in materialien.csv (ÖKOBAUDAT/BBSR) bezieht sich auf die Ökobilanzwerte. „geschätzt“ steht dagegen nur in kosten.csv, energietraeger.csv und parameter.csv.