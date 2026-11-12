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

