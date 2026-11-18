# P03 – Wärmeschutz

## Prompt

Nächster Schritt ist der Wärmeschutz. Damit wir die Varianten fair vergleichen können,
sollen alle denselben U-Wert haben.

Das Tool soll für jede Variante den U-Wert nach DIN EN ISO 6946 berechnen, einmal mit den
Dicken aus aufbauten.csv und einmal nach der Anpassung. Angepasst wird die Schicht mit
anpassbar = 1: Ihre Dicke soll so gewählt werden, dass genau der Ziel-U-Wert erreicht
wird. Ziel-U, Rsi und Rse stehen in parameter.csv.

Für die Mischschicht aus KVH und Glaswolle rechnen wir vereinfacht mit einem nach
Volumenanteilen gemittelten λ. Die Anteile bleiben beim Anpassen gleich. Das ist eine
bewusste Vereinfachung, sie soll im Code und im README als solche erkennbar sein.

Die Masse aus P02 soll danach mit der angepassten Dicke gerechnet werden. Wir wollen in
der Ausgabe sehen: U vorher, U nachher, alte und neue Dicke der angepassten Schicht und
die neue Masse. Liegt der Ziel-U-Wert über dem GEG-Referenzwert, soll ein Hinweis
erscheinen. Kann der Ziel-U-Wert mit der Schicht nicht erreicht werden, soll das als
Fehler gemeldet werden und nicht still weitergerechnet werden.

Zum Testen haben wir von Hand gerechnet (Ziel-U 0,20 W/(m²K)):
- Stahlbeton + EPS-WDVS: U vorher 0,210 W/(m²K), EPS danach 16,86 cm, Masse 508,1 kg/m²
- Holzrahmen + Holzfaser: gemitteltes λ der Gefachschicht 0,04728 W/(mK), Gefach danach 15,57 cm

Keine Ökobilanz und keine Kosten in diesem Schritt.

## Antwort der KI

