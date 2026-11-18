"""Seite Methode & Hilfe."""

from __future__ import annotations

import streamlit as st

from oberflaeche.stil import kopf

kopf("Methode & Hilfe", "Vorstufe zu eLCA, kein Ersatz. Ohne Wärmebrücken, ohne Gesamtgebäude.")

t1, t2, t3 = st.tabs(["Bedienung", "Rechenweg", "Grenzen"])
with t1:
    st.markdown("""
1. **Vergleich bei:** *gleichem U-Wert* (Standard, thermisch gleichwertig) oder *gleicher
   Wanddicke* (Geometrie vorgegeben, U-Wert ergibt sich; thermisch nicht gleichwertig,
   B6 vereinfacht). Optimum und Robustheit rechnen immer bei gleichem U-Wert.
   **Seitenleiste:** Ziel-U-Wert, Energieträger und Varianten wählen. Weitere Randbedingungen
   und der Suchbereich für das Optimum stehen unter *Erweitert*. Das **?** zeigt Bedeutung,
   Einheit und Quelle.
2. **Übersicht:** Kennzahlen je Variante; der Prozentwert ist der Abstand zur besten Variante.
   Die **Gesamtbewertung** fasst GWP, PENRT und Kosten nach den Gewichten in der Seitenleiste
   zusammen (beste Variante je Kriterium = 100 Punkte, 20 % schlechter = 80 Punkte).
3. **Verlauf über die Zeit:** kumuliertes GWP bzw. PENRT von der Herstellung (Bau) über
   Ersatz und Betrieb bis zum Rückbau; Schnittpunkte der Varianten werden angezeigt.
   **Zielkonflikt:** GWP bzw. PENRT gegen Kosten; nicht übertroffene Varianten sind groß
   dargestellt, die Ampel zeigt, ob das in allen Robustheitsfällen so bleibt.
   **Optimale Dämmdicke:** Minimum und optimaler Bereich je Kriterium.
4. **Robustheit:** Jede unsichere Eingangsgröße wird einzeln verschoben (Spannen in
   parameter.csv). Das Tornado-Diagramm zeigt die größten Hebel; oben steht, ob die
   Rangfolge der Varianten stabil bleibt.
5. **Aufbauten:** Schichten ändern oder neue Varianten anlegen (neuer Name in *Variante*).
6. **Projekt, Bericht & Export:** Arbeitsstand als Projektdatei sichern und wieder laden,
   Bericht erstellen (im Browser mit Strg + P als PDF speichern), Ergebnisse als CSV.
""")
with t2:
    st.markdown(r"""
| Schritt | Formel |
|---|---|
| U-Wert (DIN EN ISO 6946) | $U = 1/(R_{si} + \sum d/\lambda + R_{se})$ |
| Inhomogene Schicht (vereinfacht) | $\lambda = \sum \text{Anteil}\cdot\lambda_i$ |
| Dämmdicke | $d = \lambda\,(1/U_{Ziel} - R_{si} - R_{se} - \sum R_{übrige})$ |
| Masse | $m = d \cdot \text{Anteil} \cdot \rho$ |
| A1–A3, C3, C4, D | $m \cdot$ Kennwert je kg |
| Austausch, B4 | $N = T/ND - 1$ (gerundet), $B4 = N \cdot (A1\text{–}A3 + C3 + C4)$ |
| Betrieb B6 | $Q = U \cdot G_t$, $E = Q/\eta$, GWP $= \sum_t E \cdot EF(t)$, PENRT $= \sum_t E \cdot f_{p,nren} \cdot 3{,}6$ |
| Barwertfaktor | $BWF(t) = ((1+p)/(1+i))^t$ |
| Lebenszykluskosten | Herstellung + Ersatz ($K_H + K_A$ je Austausch, abgezinst) + Rückbau ($K_A$ im Jahr $T$) + Heizung |
| Optimum | Minimum der Summe über der Dicke; Bereich: Summe ≤ Minimum + Toleranz · \|Minimum\| |
| Gesamtbewertung | $P_k = 100\,(1 - (W - W_{best})/|W_{best}|) \ge 0$, Gesamt $= \sum g_k P_k / \sum g_k$ |
| Robustheit | je Größe Faktor $(1 \pm s)$, alle anderen Werte unverändert (one-at-a-time) |

Summen = A1–A3 + B4 + C3 + C4 + B6. Modul D wird getrennt ausgewiesen (nur Erstaufbau).
""")
with t3:
    st.markdown("""
- Inhomogene Schichten mit flächengemitteltem λ statt Normverfahren: U etwas zu günstig.
- Luftschichten werden noch nicht unterstützt.
- Kosten sind überwiegend Schätzwerte (Status „geschätzt“).
- Strom: Emissionsfaktor nach strom_szenario.csv, Primärenergiefaktor konstant.
- Optimum ohne konstruktive Grenzen (zugelassene Dicken, Flächenverlust): Suchbereich passend wählen.
""")
