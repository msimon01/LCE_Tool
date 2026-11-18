"""Optimale Dicke der anpassbaren Schicht (ökologisch und ökonomisch).

Die Dicke der ersten Schicht mit anpassbar = 1 wird von d_min bis d_max variiert
(Werte aus parameter.csv). Je Dicke ergeben sich
    Konstruktion  = A1–A3 + B4 + C3 + C4      bzw. Herstellung + Ersatz + Rückbau
    Betrieb       = B6                        bzw. Heizkosten
    Summe         = Konstruktion + Betrieb    (Modul D getrennt, nicht enthalten)
für die Kriterien GWP, PENRT und Lebenszykluskosten (LCC).

Optimum: Dicke mit der kleinsten Summe.
Optimaler Bereich: zusammenhängender Dickenbereich um das Optimum mit
    Summe ≤ Summe_min + Toleranz · |Summe_min|       (Toleranz z. B. 0,05 = 5 %)

Rechenweg (schnell, exakt für das Rechenmodell des Tools):
- Die Konstruktionsanteile wachsen linear mit d (Masse = d · Anteil · ρ, Kosten = fix + je_cm · d,
  N hängt nicht von d ab). Sie werden aus zwei vollständigen Berechnungen bei d_min und d_max
  linear interpoliert.
- Die Betriebsanteile sind proportional zu U (Q = U · Gt, E = Q/η):
  Betrieb(d) = Betrieb(d_min) · U(d) / U(d_min), U(d) = 1 / (R_fest + d/λ).
- Zwei weitere vollständige Berechnungen im Inneren prüfen das. Weichen sie ab, wird jede
  Rasterdicke vollständig gerechnet (Hinweis in der Ausgabe).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from lce.berechnung import Einstellungen, berechne_variante
from lce.daten_laden import parameter
from lce.einheiten import m_in_cm
from lce.waermeschutz import Berechnungsfehler, kennwerte_anpassbar, u_wert_bei_dicke

# Schlüssel in parameter.csv
OPTIMIERUNG_PARAMETER = ("optimierung_toleranz", "optimierung_d_min_m",
                         "optimierung_d_max_m", "optimierung_schritt_m")

# Kriterium → (Spalte Summe, Spalte Betrieb im Variantenergebnis, Einheit im Spaltennamen)
KRITERIEN: dict[str, tuple[str, str, str]] = {
    "gwp": ("gwp_summe_kg_co2e_m2", "gwp_b6_kg_co2e_m2", "kg_co2e_m2"),
    "penrt": ("penrt_summe_mj_m2", "penrt_b6_mj_m2", "mj_m2"),
    "lcc": ("lcc_summe_eur_m2", "lcc_heizung_eur_m2", "eur_m2"),
}

# relative Abweichung, ab der die lineare Zerlegung als nicht gültig gilt
PRUEFTOLERANZ = 1e-6


def verlauf_spalte(kriterium: str, teil: str) -> str:
    """z. B. gwp_konstruktion_kg_co2e_m2, lcc_betrieb_eur_m2."""
    return f"{kriterium}_{teil}_{KRITERIEN[kriterium][2]}"


@dataclass(frozen=True)
class Suchbereich:
    d_min_m: float
    d_max_m: float
    schritt_m: float
    toleranz: float

    def dicken(self) -> np.ndarray:
        """Raster d_min, d_min + Schritt, …, d_max (d_max immer enthalten)."""
        n = int(np.floor((self.d_max_m - self.d_min_m) / self.schritt_m + 1e-9))
        d = self.d_min_m + self.schritt_m * np.arange(n + 1)
        if d[-1] < self.d_max_m - 1e-12:
            d = np.append(d, self.d_max_m)
        return d


def suchbereich_aus_daten(daten: dict[str, pd.DataFrame]) -> Suchbereich:
    """Liest Toleranz und Dickenbereich aus parameter.csv. Fehlende Werte → Berechnungsfehler."""
    vorhanden = set(daten["parameter.csv"]["schluessel"])
    fehlend = [s for s in OPTIMIERUNG_PARAMETER if s not in vorhanden]
    if fehlend:
        raise Berechnungsfehler("parameter.csv: für die Optimierung fehlen " + ", ".join(fehlend))
    return pruefe_suchbereich(Suchbereich(
        d_min_m=parameter(daten, "optimierung_d_min_m"),
        d_max_m=parameter(daten, "optimierung_d_max_m"),
        schritt_m=parameter(daten, "optimierung_schritt_m"),
        toleranz=parameter(daten, "optimierung_toleranz"),
    ))


def pruefe_suchbereich(s: Suchbereich) -> Suchbereich:
    if s.d_min_m <= 0:
        raise Berechnungsfehler(f"optimierung_d_min_m muss größer als 0 sein, ist {s.d_min_m}")
    if s.d_max_m <= s.d_min_m:
        raise Berechnungsfehler("optimierung_d_max_m muss größer als optimierung_d_min_m sein")
    if s.schritt_m <= 0:
        raise Berechnungsfehler(f"optimierung_schritt_m muss größer als 0 sein, ist {s.schritt_m}")
    if s.toleranz < 0:
        raise Berechnungsfehler(f"optimierung_toleranz darf nicht negativ sein, ist {s.toleranz}")
    return s


@dataclass
class Optimierung:
    verlauf: pd.DataFrame                      # je Variante und Dicke
    optima: pd.DataFrame                       # je Variante und Kriterium
    fehler: dict[str, str] = field(default_factory=dict)
    hinweise: dict[str, list[str]] = field(default_factory=dict)


def _werte(z: dict) -> dict[str, tuple[float, float]]:
    """Kriterium → (Konstruktion, Betrieb) aus einem Variantenergebnis."""
    return {k: (z[s] - z[b], z[b]) for k, (s, b, _) in KRITERIEN.items()}


def _verlauf_voll(daten, einst, variante, dicken) -> pd.DataFrame:
    zeilen = []
    for d in dicken:
        z, _, _ = berechne_variante(daten, einst, variante, dicke_m=float(d))
        zeile = {"variante": variante, "dicke_m": float(d), "u_w_m2k": z["u_nachher_w_m2k"]}
        for k, (kon, betr) in _werte(z).items():
            zeile[verlauf_spalte(k, "konstruktion")] = kon
            zeile[verlauf_spalte(k, "betrieb")] = betr
            zeile[verlauf_spalte(k, "summe")] = kon + betr
        zeilen.append(zeile)
    return pd.DataFrame(zeilen)


def verlauf_variante(daten: dict[str, pd.DataFrame], einst: Einstellungen, variante: str,
                     such: Suchbereich) -> tuple[pd.DataFrame, str]:
    """Werte über der Dicke. Rückgabe: (Verlauf, Rechenweg "linear" oder "vollständig")."""
    dicken = such.dicken()
    if len(dicken) < 5:
        return _verlauf_voll(daten, einst, variante, dicken), "vollständig"

    aufbau = daten["aufbauten.csv"]
    aufbau = aufbau[aufbau["variante"] == variante].sort_values("position")
    r_fest, lam = kennwerte_anpassbar(aufbau, daten["materialien.csv"],
                                      parameter(daten, "rsi_m2k_w"), parameter(daten, "rse_m2k_w"))
    u = u_wert_bei_dicke(r_fest, lam, dicken)

    d_a, d_b = float(dicken[0]), float(dicken[-1])
    z_a, _, _ = berechne_variante(daten, einst, variante, dicke_m=d_a)
    z_b, _, _ = berechne_variante(daten, einst, variante, dicke_m=d_b)
    w_a, w_b = _werte(z_a), _werte(z_b)
    u_a = z_a["u_nachher_w_m2k"]

    def modell(k: str, d, u_d):
        kon = w_a[k][0] + (w_b[k][0] - w_a[k][0]) * (d - d_a) / (d_b - d_a)   # linear in d
        betr = w_a[k][1] * u_d / u_a                                           # proportional zu U
        return kon, betr

    # Prüfung an zwei inneren Rasterpunkten
    for i in (len(dicken) // 3, 2 * len(dicken) // 3):
        z_i, _, _ = berechne_variante(daten, einst, variante, dicke_m=float(dicken[i]))
        for k, (s, _, _) in KRITERIEN.items():
            kon, betr = modell(k, dicken[i], u[i])
            if abs(kon + betr - z_i[s]) > PRUEFTOLERANZ * max(1.0, abs(z_i[s])):
                return _verlauf_voll(daten, einst, variante, dicken), "vollständig"

    df = pd.DataFrame({"variante": variante, "dicke_m": dicken, "u_w_m2k": u})
    for k in KRITERIEN:
        kon, betr = modell(k, dicken, u)
        df[verlauf_spalte(k, "konstruktion")] = kon
        df[verlauf_spalte(k, "betrieb")] = betr
        df[verlauf_spalte(k, "summe")] = kon + betr
    return df, "linear"


def optimum(verlauf: pd.DataFrame, kriterium: str, toleranz: float) -> dict:
    """Minimum und optimaler Bereich (zusammenhängend um das Minimum) eines Kriteriums."""
    f = verlauf[verlauf_spalte(kriterium, "summe")].to_numpy()
    d = verlauf["dicke_m"].to_numpy()
    u = verlauf["u_w_m2k"].to_numpy()
    i = int(np.argmin(f))
    grenze = f[i] + toleranz * abs(f[i])          # Summe ≤ Summe_min + Toleranz · |Summe_min|
    von = i
    while von > 0 and f[von - 1] <= grenze:
        von -= 1
    bis = i
    while bis < len(f) - 1 and f[bis + 1] <= grenze:
        bis += 1
    return {
        "kriterium": kriterium,
        "dicke_opt_m": float(d[i]), "u_opt_w_m2k": float(u[i]), "wert_opt": float(f[i]),
        "grenze": float(grenze),
        "dicke_von_m": float(d[von]), "dicke_bis_m": float(d[bis]),
        "u_von_w_m2k": float(u[bis]), "u_bis_w_m2k": float(u[von]),
        "am_rand": i == 0 or i == len(f) - 1,
        "bereich_am_rand": von == 0 or bis == len(f) - 1,
    }


def optimiere(daten: dict[str, pd.DataFrame], einst: Einstellungen,
              varianten: list[str] | None = None,
              such: Suchbereich | None = None) -> Optimierung:
    """Optimale Dicken für alle (oder die gewählten) Varianten.

    Zum Vergleich wird der Wert bei der Dicke für den Ziel-U-Wert angegeben.
    """
    such = such or suchbereich_aus_daten(daten)
    alle = list(dict.fromkeys(daten["aufbauten.csv"]["variante"]))
    auswahl = [v for v in alle if varianten is None or v in varianten]
    verlaeufe, optima, fehler, hinweise = [], [], {}, {}
    for v in auswahl:
        try:
            verlauf, weg = verlauf_variante(daten, einst, v, such)
            try:
                z_ziel, _, _ = berechne_variante(daten, einst, v)
            except Berechnungsfehler:
                z_ziel = None                     # Ziel-U nicht erreichbar: kein Vergleichswert
        except Berechnungsfehler as e:
            fehler[v] = str(e)
            continue
        h = []
        if weg == "vollständig":
            h.append("jede Dicke vollständig gerechnet (lineare Zerlegung nicht anwendbar)")
        for k, (s, _, _) in KRITERIEN.items():
            o = {"variante": v, **optimum(verlauf, k, such.toleranz)}
            if z_ziel is not None:
                o["dicke_ziel_u_m"] = z_ziel["dicke_nachher_m"]
                o["wert_ziel_u"] = z_ziel[s]
                # Mehraufwand bei Ziel-U gegenüber Optimum, bezogen auf |Minimum|
                o["mehr_bei_ziel_u_anteil"] = (z_ziel[s] - o["wert_opt"]) / abs(o["wert_opt"])
                o["ziel_u_im_bereich"] = (o["dicke_von_m"] - 1e-9 <= z_ziel["dicke_nachher_m"]
                                          <= o["dicke_bis_m"] + 1e-9)
            if o["am_rand"]:
                h.append(f"{k.upper()}: Optimum liegt am Rand des Suchbereichs "
                         f"({m_in_cm(o['dicke_opt_m']):.1f} cm), Suchbereich prüfen")
            optima.append(o)
        verlaeufe.append(verlauf)
        if h:
            hinweise[v] = h
    return Optimierung(
        verlauf=pd.concat(verlaeufe, ignore_index=True) if verlaeufe else pd.DataFrame(),
        optima=pd.DataFrame(optima), fehler=fehler, hinweise=hinweise,
    )
