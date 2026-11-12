# P02 – Masse

## Prompt

**Änderung:** Berechne die flächenbezogene Masse je Schicht und je Variante. Die Dicken
kommen unverändert aus aufbauten.csv; die Anpassung an den Ziel-U-Wert folgt später.
Gib das Ergebnis erstmals auch als CSV-Datei aus.

**Eingabe:** die in P01 geladenen und geprüften Daten (dicke_m aus aufbauten.csv,
rohdichte_kg_m3 aus materialien.csv).

**Verhalten:**
- Masse je Schicht: m = d · Anteil · ρ in kg/m². Homogene Schicht: Anteil = 1.
  Inhomogene Schicht: je Bestandteil eine Teilmasse, die Schichtmasse ist ihre Summe.
- Masse je Variante = Summe aller Schichten.
- Rechnung im Rechenkern (eigenes Modul), Ausgabe nur in ausgabe/.
- Intern ungerundet; gerundet wird nur in der Ausgabe.
- Konsole: je Variante Position, Schicht, Material, Dicke in cm, Masse in kg/m²
  (1 Nachkommastelle), darunter die Summe.
- CSV ergebnisse/masse.csv: eine Zeile je Schicht bzw. je Bestandteil einer inhomogenen
  Schicht mit variante, position, schicht, material, anteil, dicke_m, rohdichte_kg_m3,
  masse_kg_m2. Trennzeichen `;`, Dezimalkomma, UTF-8 mit BOM, damit Excel die Datei
  direkt richtig öffnet. Die Datei wird bei jedem Lauf überschrieben.

**Grenzen:** Kein U-Wert, keine Dämmdickenanpassung, keine Ökobilanz. Keine Werte im Code.

**Test:**
1. 1 m² mit d = 0,20 m und ρ = 500 kg/m³ → 100 kg/m² (nicht 10 000, nicht 0,1).
2. Inhomogene Schicht d = 0,20 m, kvh 0,12 (ρ 529) und glaswolle 0,88 (ρ 26,25)
   → 12,696 + 4,62 = 17,316 kg/m².
3. Originaldaten, Stahlbeton + EPS-WDVS → 507,9 kg/m².
4. Originaldaten, Holzrahmen + Holzfaser → 60,665 kg/m².
5. masse.csv entsteht, ist mit Dezimalkomma lesbar, und die Summe je Variante stimmt mit
   Test 3 und 4 überein.

## Antwort der KI

P02 ist umgesetzt. python main.py gibt die Masse je Schicht und Variante aus und schreibt ergebnisse/masse.csv. Alle 39 Tests laufen grün, daten/ ist unverändert.

Geänderte Dateien:
main.py: ruft jetzt Masseberechnung, Ausgabe und CSV auf
ausgabe/konsole.py: neue Funktionen zeige_masse und zeige_datei
README.md
Neu: lce/masse.py, ausgabe/csv_export.py, tests/test_masse.py
Ergebnis (Originaldaten):
Variante	Masse
Stahlbeton + EPS-WDVS	507,9 kg/m²
Hochlochziegel + Mineralwolle-WDVS	155,5 kg/m²
Holzrahmen + Holzfaser	60,665 kg/m² (Konsole: 60,7 kg/m²)
Rückfragen:
Die Schichtenliste aus P01 und die neue Massentabelle zeigen in der Konsole fast dasselbe. Soll ich die Liste aus P01 entfernen?
Annahmen / nicht geprüft:
In der CSV stehen die Zahlen mit 10 signifikanten Stellen statt ungerundet, damit kein Gleitkommarauschen wie 12,696000000000002 erscheint.
Eine inhomogene Schicht zeigt in der Konsole die Originalangabe kvh:0.12|glaswolle:0.88, in der CSV dagegen eine Zeile je Bestandteil.
Den Ordner ergebnisse/ legt das Programm selbst an, falls er fehlt.
So prüft ihr es: Startet pytest und python main.py und öffnet dann ergebnisse/masse.csv per Doppelklick in Excel. Die Zahlen sollten mit Komma in eigenen Spalten stehen. Eine Summe könnt ihr von Hand nachrechnen: 0,015·900 + 0,20·2362 + 0,16·25 + 0,01·1800 = 507,9 kg/m².

# Antwort

Entferne die Liste aus P01.


# Antwort der KI

Die Schichtliste aus P01 ist entfernt. Die Konsole zeigt jetzt Zeilen je Datei, die Anzahl „geschätzt“ und die Massentabelle. Alle 39 Tests laufen grün.

Geänderte Dateien:
ausgabe/konsole.py: der Block mit der Schichtliste ist entfernt.
README.md: Eintrag P02 ergänzt.
Neu: keine
Rückfragen: keine
Annahmen / nicht geprüft:
Die Massentabelle heißt jetzt „Schichten innen → außen“, damit die Reihenfolge weiter erkennbar ist.
Der Hinweis „(anpassbar)“ fehlt jetzt in der Konsole. Sagt Bescheid, falls er in die Massentabelle soll.
So prüft ihr es: Startet python main.py. Die Schichten erscheinen nur noch einmal, in der Massentabelle. Danach pytest laufen lassen.