# E04 bis E06 – Erweiterungen Darstellung und Vergleichsmodus

Drei Prompts, nacheinander senden. Nach jedem Prompt Abnahme und Git-Commit, erst dann den nächsten.

---

# E04 – Kumulierter Verlauf über den Betrachtungszeitraum

## Prompt

**Änderung:** Wir wollen je Variante sehen, wie sich GWP und PENRT über den
Betrachtungszeitraum aufsummieren. Die Summe am Ende kennen wir schon. Jetzt soll
sichtbar werden, wann die Emissionen entstehen und wie die Unterschiede zwischen den
Varianten zustande kommen.

**Eingabe:** die vorhandenen Ergebnisse je Modul und Variante, die Nutzungsdauern aus
materialien.csv, strom_szenario.csv und die eingestellte Rundungsregel für die
Austauschhäufigkeit.

**Verhalten:**
- Jahr 0: Herstellung (A1–A3).
- Ersatz (B4) in dem Jahr, in dem die Schicht tatsächlich getauscht wird, also bei der
  Nutzungsdauer und ihren Vielfachen. Es sollen genau die Austausche sein, die heute
  schon in B4 stecken, auch wenn die Rundungsregel umgestellt wird.
- Betrieb (B6) Jahr für Jahr. Bei Strom gilt der Emissionsfaktor des jeweiligen Jahres
  aus dem Szenario.
- Rückbau (C3, C4) als eigener letzter Punkt nach dem letzten Jahr.
- D ist nicht Teil der Kurve, wird aber wie bisher getrennt ausgewiesen.
- Der vorhandene Schalter „Betrieb einbeziehen“ gilt auch hier.
- Kreuzen sich zwei Kurven, soll das Jahr des Schnittpunkts angezeigt werden.
- Neue Ansicht in der Oberfläche. Zusätzlich eine CSV mit einer Zeile je Variante und
  Jahr.

**Grenzen:** Die bisherigen Summen dürfen sich nicht ändern. Keine neuen Fachdaten.

**Test:**
1. Der letzte Wert jeder Kurve ist gleich der Summe aus der Übersicht, mit und ohne B6.
2. Holzrahmen + Holzfaser, ohne B6, Aufrunden: Jahr 0 rund −24,1 kg CO₂e/m², in Jahr 35
   eine Stufe von rund +0,9 (PE-Folie), in Jahr 45 rund +3,1 (Putz), beim Rückbau rund
   +49,8.
3. Dieselbe Variante mit kaufmännischer Rundung: keine Stufen in Jahr 35 und 45.
4. Mit B6 und Erdgas steigen alle drei Kurven gleich steil an, da der U-Wert gleich ist.

## Antwort der KI

(wörtlich einfügen)

---

# E05 – Punktwolke GWP gegen Kosten und Robustheits-Ampel

## Prompt

**Änderung:** Die Rangfolge und die gewichtete Gesamtbewertung zeigen nicht, wie die
Unterschiede zustande kommen, und die Gewichte sind subjektiv. Wir wollen deshalb zwei
neue Darstellungen.

**Eingabe:** die vorhandenen Ergebnisse je Variante und die vorhandene
Robustheitsprüfung.

**Verhalten:**
- Punktwolke: ein Punkt je Variante, waagerecht das GWP, senkrecht die
  Lebenszykluskosten. PENRT soll statt GWP wählbar sein. Der Schalter „Betrieb
  einbeziehen“ gilt auch hier.
- Eine Variante ist „übertroffen“, wenn eine andere in beiden Größen mindestens gleich
  gut und in mindestens einer besser ist. Nicht übertroffene Varianten sollen
  hervorgehoben werden.
- Ampel je Variante aus der Robustheitsprüfung. Geprüft wird jeder Fall, in dem eine
  Annahme auf ihren unteren oder oberen Wert gesetzt ist:
  - grün: in allen Fällen nicht übertroffen
  - gelb: nur in einem Teil der Fälle nicht übertroffen
  - rot: in keinem Fall nicht übertroffen
- Bei Gelb soll erkennbar sein, welche Annahme das Ergebnis kippen lässt.
- Die Farbe der Ampel soll auch der Punkt in der Punktwolke tragen.

**Grenzen:** Die gewichtete Gesamtbewertung bleibt vorerst unverändert. Keine neuen
Fachdaten, keine Änderung an den Rechenergebnissen.

**Test:**
1. A (GWP 100, Kosten 200) und B (120, 150): beide nicht übertroffen.
2. Zusätzlich C (130, 210): C ist übertroffen (von A).
3. Zwei Varianten mit genau gleichen Werten: beide nicht übertroffen.
4. Mit den Originaldaten und Betrieb ist Holzrahmen + Holzfaser nicht übertroffen,
   die beiden anderen sind übertroffen.

## Antwort der KI

(wörtlich einfügen)

---

# E06 – Vergleich bei gleicher Wanddicke

## Prompt

**Änderung:** Bisher vergleichen wir bei gleichem U-Wert. In der Praxis ist oft die
Geometrie vorgegeben, also die Außenwanddicke. Wir wollen einen zweiten Vergleichsmodus
„gleiche Wanddicke“ und sehen, wie sich das Ergebnis dadurch verschiebt.

**Eingabe:** neuer Schlüssel ziel_wanddicke_m in parameter.csv (von uns ergänzt,
Startwert 0,36 m), sonst die vorhandenen Daten.

**Verhalten:**
- Im Modus „gleiche Wanddicke“ wird die Schicht mit anpassbar = 1 so dick, dass die
  gesamte Wand die Zielwanddicke erreicht. Der U-Wert ergibt sich daraus, nach DIN EN
  ISO 6946 wie bisher.
- Der Betrieb (B6) wird mit diesem U-Wert gerechnet, weiterhin vereinfacht über die
  Heizgradstunden. Alles andere bleibt gleich.
- Die Zielwanddicke soll in der Oberfläche änderbar sein. Der Modus muss in jeder
  Ausgabe eindeutig erkennbar sein, damit die beiden Modi nicht verwechselt werden.
- Je Variante den sich ergebenden U-Wert anzeigen. Liegt er über dem Referenzwert aus
  parameter.csv, soll ein Hinweis erscheinen.
- Kann die Zielwanddicke nicht erreicht werden, weil die übrigen Schichten schon dicker
  sind oder die anpassbare Schicht zu dünn würde, soll das als Fehler gemeldet werden
  und die Variante nicht still weitergerechnet werden.
- Wir wollen die Rangfolge beider Modi nebeneinander sehen. Der kumulierte Verlauf aus
  E04 soll auch in diesem Modus funktionieren.
- Im Code und im README soll stehen, dass die Varianten in diesem Modus thermisch nicht
  gleichwertig sind und B6 nur vereinfacht abgebildet ist.

**Grenzen:** Optimale Dämmdicke und Robustheit bleiben vorerst im Modus „gleicher
U-Wert“. Falls das zu Widersprüchen führt, frage nach.

**Test:** Handrechnung für eine Zielwanddicke von 0,36 m, Erdgas, 50 Jahre:
1. Stahlbeton + EPS-WDVS: EPS 13,5 cm, U ≈ 0,246 W/(m²K), B6 ≈ 235,5 kg CO₂e/m²
2. Hochlochziegel + Mineralwolle-WDVS: Steinwolle 16,0 cm, U ≈ 0,197 W/(m²K),
   B6 ≈ 188,3 kg CO₂e/m²
3. Holzrahmen + Holzfaser: Gefach 26,43 cm, U ≈ 0,137 W/(m²K), B6 ≈ 131,2 kg CO₂e/m²
4. Zielwanddicke 0,20 m: Stahlbeton + EPS-WDVS wird als nicht erreichbar gemeldet.
5. Im Modus „gleicher U-Wert“ bleiben alle bisherigen Ergebnisse unverändert.

## Antwort der KI

(wörtlich einfügen)
