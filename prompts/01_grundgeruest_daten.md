# P01 – Grundgerüst und Daten laden

## Prompt

**Änderung:** Lege die Struktur nach deinem Vorschlag aus P00 an (Programmdateien, Tests,
Ausgabeordner, README). Lies alle CSV-Dateien aus daten/ ein und prüfe sie. Es wird noch
nichts berechnet.

**Eingabe:** Pflichtspalten (alle weiteren Spalten einlesen und behalten, dürfen leer sein):

| Datei | Pflichtspalten | davon Zahlen |
|---|---|---|
| materialien.csv | id, name, rohdichte_kg_m3, lambda_W_mK, gwp_a1a3_kg, gwp_c3_kg, gwp_c4_kg, gwp_d_kg, penrt_a1a3_mj_kg, penrt_c3_mj_kg, penrt_c4_mj_kg, penrt_d_mj_kg, nutzungsdauer_a, status | alle außer id, name, status |
| aufbauten.csv | variante, position, schicht, material, dicke_m, anpassbar | position, dicke_m, anpassbar |
| kosten.csv | material_id, kosten_fix_eur_m2, kosten_je_cm_eur_m2, abbruch_fix_eur_m2, abbruch_je_cm_eur_m2, status | alle außer material_id, status |
| energietraeger.csv | id, name, wirkungsgrad, emissionsfaktor_kg_kwh, primaerenergiefaktor_nren, preis_eur_kwh, strom | alle außer id, name |
| parameter.csv | schluessel, wert | wert |
| strom_szenario.csv | jahr, emissionsfaktor_kg_kwh | beide |

- material in aufbauten.csv kann eine inhomogene Schicht sein, z. B. `kvh:0.12|glaswolle:0.88`
  (Volumenanteile, Summe 1).
- Die Schichten einer Variante stehen innen → außen, sortiert nach position.

**Verhalten:** `python main.py` lädt und prüft alle Dateien.
- Daten in Ordnung: Übersicht in der Konsole mit Anzahl Zeilen je Datei, je Variante die
  Schichten mit Material und Dicke in cm, Anzahl der Einträge mit Status „geschätzt“.
- Fehler: alle Fehler auflisten (nicht nur den ersten), je Fehler Datei, Zeile (wie im
  Editor, Kopfzeile = 1), Spalte und Grund. Danach keine weitere Ausgabe.
- Fehler sind: Datei fehlt; Pflichtspalte fehlt; Pflichtwert leer; Zahl nicht lesbar;
  Material aus aufbauten.csv oder kosten.csv fehlt in materialien.csv; Anteile einer
  inhomogenen Schicht ergeben nicht 1 (Toleranz 0,001); anpassbar nicht 0 oder 1;
  dicke_m nicht größer als 0.
- Material ohne Eintrag in kosten.csv: kein Fehler, sondern Hinweis „Kosten unvollständig“.

**Grenzen:** Keine Berechnungen, keine Oberfläche, keine Fachwerte im Code, daten/ nicht
verändern.

**Test:** pytest-Tests mit temporären Kopien der Daten (nicht mit daten/ selbst):
1. Originaldaten → keine Fehler.
2. Leere Rohdichte bei stahlbeton → Meldung mit materialien.csv, Zeile 2, Spalte
   rohdichte_kg_m3; kein Ergebnis mit 0.
3. „abc“ statt Zahl in dicke_m → Meldung mit Datei, Zeile, Spalte.
4. Unbekanntes Material in aufbauten.csv → Meldung.
5. Pflichtspalte fehlt → Meldung mit Datei und Spalte.
6. Inhomogene Schicht mit Anteilen 0.12 und 0.80 → Meldung.
Erkläre zum Schluss, wie wir Test 2 von Hand nachstellen können.

## Antwort der KI

Ich lege die Struktur an und schreibe Lader, Prüfung, Konsolenausgabe und Tests.
P01 ist umgesetzt. `python main.py` lädt und prüft alle sechs Dateien und meldet keine Fehler. Die 24 Tests laufen grün, daten/ ist danach unverändert.

* Geänderte Dateien: keine
* Neu: main.py, lce/__init__.py, lce/einheiten.py, lce/daten_laden.py, ausgabe/__init__.py, ausgabe/konsole.py, tests/conftest.py, tests/test_daten_laden.py, pytest.ini, requirements.txt, README.md, ergebnisse/.gitkeep
* Rückfragen:
   1. Eure Antworten zu P00 stehen noch aus. Ich habe deshalb vorläufig so entschieden:
      * „teilweise geschätzt“ zählt als geschätzt, „prüfen“ nicht.
      * `luft` wird geprüft, aber noch nicht gesondert behandelt.
      * requirements.txt nennt nur Mindestversionen.
   2. Sollen doppelte IDs (z. B. ein Material zweimal in materialien.csv) als Fehler gelten? Bisher wird das nicht geprüft.
* Annahmen / nicht geprüft:
   * Ich habe mit Python 3.10, pandas 2.3.3 und pytest 9.2 getestet, nicht mit 3.14.
   * Die Toleranz 0,001 steht als Prüfkonstante im Code, weil sie aus dem Prompt kommt und kein Fachwert ist.
   * In materialien.csv hat kein Eintrag den Status „geschätzt“, deshalb zeigt die Übersicht dort 0.
* So prüft ihr es: `pip install -r requirements.txt`, dann `python main.py` und `pytest`.

Test 2 von Hand nachstellen:

1. Öffnet daten/materialien.csv in einem Texteditor, nicht in Excel.
2. Löscht in Zeile 2 (stahlbeton) den Wert `2362` nach dem dritten `;`, sodass dort `;;` steht.
3. Startet `python main.py`. Erwartet wird die Meldung `materialien.csv, Zeile 2, Spalte rohdichte_kg_m3: Pflichtwert leer`, danach keine weitere Ausgabe.
4. Setzt den Wert danach wieder ein oder stellt die Datei mit Git zurück.


# Antwort

Ja, doppelte IDs sind ein Fehler (materialien.csv: id, kosten.csv: material_id, energietraeger.csv: id, parameter.csv: schluessel, strom_szenario.csv: jahr; aufbauten.csv: position doppelt innerhalb einer Variante). Meldung mit Datei, beiden Zeilen und Spalte. Ergänze einen Test dazu. Zu Rückfrage 1: einverstanden.


# Antwort der KI

Die Prüfung auf doppelte Schlüssel ist eingebaut. Alle 32 Tests laufen grün, und mit den Originaldaten meldet python main.py weiterhin keine Fehler.

Geänderte Dateien:
lce/daten_laden.py: Liste der eindeutigen Spalten und eine Prüffunktion dafür
tests/test_daten_laden.py: 8 neue Testfälle
README.md: Versionsverlauf P01a
Neu: keine
Rückfragen: keine
Annahmen / nicht geprüft:
Die Meldung steht an der zweiten Zeile, nennt aber beide, z. B. materialien.csv, Zeile 3, Spalte id: 'stahlbeton' doppelt (Zeilen 2 und 3).
Bei dreifachem Vorkommen verweisen Meldung 2 und 3 jeweils auf das erste Vorkommen.
Jahr und Position werden als Zahl verglichen. „2026“ und „2026.0“ gelten also als doppelt.
Die Position wird nur innerhalb einer Variante verglichen. Gleiche Positionen in verschiedenen Varianten sind erlaubt.
So prüft ihr es: Startet pytest. Zum Nachstellen von Hand ändert ihr in einer Kopie von materialien.csv in Zeile 3 betonstein zu stahlbeton und startet python main.py. Dann erscheinen zwei Meldungen:
die doppelte ID
als Folgefehler: betonstein aus kosten.csv fehlt jetzt in materialien.csv