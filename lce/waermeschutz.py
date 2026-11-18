"""Wärmeschutz: U-Wert und Anpassung der Dämmdicke an den Ziel-U-Wert.

Quelle der Formeln: DIN EN ISO 6946
    R_Schicht = d / λ                               [m²K/W]
    U = 1 / (Rsi + Σ R_Schicht + Rse)               [W/(m²K)]
Inhomogene Schicht (vereinfacht, Entwicklungsplan Abschnitt 2/5):
    λ = Σ Anteil · λ_Bestandteil   (kein Normverfahren mit oberem/unterem Grenzwert)
Dämmdicke (erste Schicht mit anpassbar = 1):
    d = λ · (1/U_Ziel − Rsi − Rse − Σ R der übrigen Schichten)
Für die Optimierung kann die Dicke stattdessen vorgegeben werden (dicke_vorgabe_m).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lce.daten_laden import zerlege_material


class Berechnungsfehler(Exception):
    """Fachlicher Fehler in einer Variante (z. B. Ziel-U nicht erreichbar)."""


def lambda_schicht(material: str, lambda_je_material: pd.Series) -> float:
    """λ der Schicht in W/(mK); inhomogen: λ = Σ Anteil · λ_i."""
    lam = 0.0
    for mat_id, anteil in zerlege_material(material):
        lam_i = float(lambda_je_material[mat_id])
        if lam_i <= 0:
            raise Berechnungsfehler(
                f"λ von '{mat_id}' ist {lam_i}; für diese Schicht lässt sich kein "
                f"Wärmedurchlasswiderstand d/λ berechnen (Luftschichten werden noch nicht unterstützt)"
            )
        lam += anteil * lam_i
    return lam


@dataclass
class Waermeschutz:
    """Ergebnis der Anpassung einer Variante."""

    schichten: pd.DataFrame        # je Schicht: dicke_vorher_m, dicke_m, lambda, R
    u_vorher_w_m2k: float
    u_nachher_w_m2k: float
    angepasste_position: int | None
    angepasste_schicht: str
    dicke_vorher_m: float | None
    dicke_nachher_m: float | None
    hinweise: list[str]


def _u_wert(r_summe: float, rsi: float, rse: float) -> float:
    """U = 1 / (Rsi + Σ R + Rse), DIN EN ISO 6946."""
    return 1.0 / (rsi + r_summe + rse)


def passe_an(aufbau: pd.DataFrame, materialien: pd.DataFrame,
             ziel_u: float, rsi: float, rse: float,
             dicke_vorgabe_m: float | None = None) -> Waermeschutz:
    """Berechnet U vorher, passt die erste anpassbare Schicht auf ziel_u an, U nachher.

    aufbau: Schichten einer Variante (geprüft, innen → außen).
    dicke_vorgabe_m: wenn gesetzt, erhält die anpassbare Schicht genau diese Dicke
    (ziel_u wird dann nicht verwendet).
    Löst Berechnungsfehler aus, wenn der Ziel-U-Wert nicht erreichbar ist.
    """
    if dicke_vorgabe_m is None and ziel_u <= 0:
        raise Berechnungsfehler(f"Ziel-U-Wert muss größer als 0 sein, ist {ziel_u}")
    lam_mat = materialien.set_index("id")["lambda_W_mK"]
    s = aufbau.copy()
    s["dicke_vorher_m"] = s["dicke_m"].astype(float)
    s["lambda_W_mK"] = [lambda_schicht(m, lam_mat) for m in s["material"]]
    s["r_m2k_w"] = s["dicke_vorher_m"] / s["lambda_W_mK"]          # R = d / λ
    u_vorher = _u_wert(s["r_m2k_w"].sum(), rsi, rse)

    hinweise: list[str] = []
    anpassbar = s.index[s["anpassbar"] == 1].tolist()
    if not anpassbar:
        if dicke_vorgabe_m is not None:
            raise Berechnungsfehler("keine Schicht mit anpassbar = 1, Dicke lässt sich nicht variieren")
        hinweise.append("keine Schicht mit anpassbar = 1, Dicken unverändert")
        return Waermeschutz(s, u_vorher, u_vorher, None, "", None, None, hinweise)
    if len(anpassbar) > 1:
        hinweise.append("mehrere Schichten mit anpassbar = 1, nur die erste (innen) wird angepasst")

    i = anpassbar[0]
    r_uebrige = s["r_m2k_w"].drop(index=i).sum()
    if dicke_vorgabe_m is not None:
        if dicke_vorgabe_m <= 0:
            raise Berechnungsfehler(f"vorgegebene Dicke muss größer als 0 sein, ist {dicke_vorgabe_m}")
        d_neu = float(dicke_vorgabe_m)
        s.at[i, "dicke_m"] = d_neu
        s["r_m2k_w"] = s["dicke_m"].astype(float) / s["lambda_W_mK"]
        return Waermeschutz(s, u_vorher, _u_wert(s["r_m2k_w"].sum(), rsi, rse),
                            int(s.at[i, "position"]), str(s.at[i, "schicht"]),
                            float(s.at[i, "dicke_vorher_m"]), d_neu, hinweise)
    # d = λ · (1/U_Ziel − Rsi − Rse − Σ R der übrigen Schichten)
    r_benoetigt = 1.0 / ziel_u - rsi - rse - r_uebrige
    if r_benoetigt <= 0:
        u_ohne = _u_wert(r_uebrige, rsi, rse)
        raise Berechnungsfehler(
            f"Ziel-U {ziel_u:.3f} W/(m²K) nicht erreichbar: schon ohne die Schicht "
            f"'{s.at[i, 'schicht']}' ist U = {u_ohne:.3f} W/(m²K)"
        )
    d_neu = s.at[i, "lambda_W_mK"] * r_benoetigt
    s.at[i, "dicke_m"] = d_neu
    s["r_m2k_w"] = s["dicke_m"].astype(float) / s["lambda_W_mK"]
    u_nachher = _u_wert(s["r_m2k_w"].sum(), rsi, rse)
    return Waermeschutz(s, u_vorher, u_nachher, int(s.at[i, "position"]), str(s.at[i, "schicht"]),
                        float(s.at[i, "dicke_vorher_m"]), float(d_neu), hinweise)


def u_wert_bei_dicke(r_fest_m2k_w: float, lambda_w_mk: float, dicke_m):
    """U(d) = 1 / (R_fest + d/λ); R_fest = Rsi + Rse + Σ R der übrigen Schichten.
    Funktioniert auch mit numpy-Arrays für d."""
    return 1.0 / (r_fest_m2k_w + dicke_m / lambda_w_mk)


def kennwerte_anpassbar(aufbau: pd.DataFrame, materialien: pd.DataFrame,
                        rsi: float, rse: float) -> tuple[float, float]:
    """(R_fest, λ) der ersten anpassbaren Schicht für u_wert_bei_dicke()."""
    lam_mat = materialien.set_index("id")["lambda_W_mK"]
    anpassbar = aufbau[aufbau["anpassbar"] == 1]
    if anpassbar.empty:
        raise Berechnungsfehler("keine Schicht mit anpassbar = 1, Dicke lässt sich nicht variieren")
    i = anpassbar.index[0]
    r_uebrige = sum(float(z["dicke_m"]) / lambda_schicht(z["material"], lam_mat)
                    for j, z in aufbau.iterrows() if j != i)
    return rsi + rse + r_uebrige, lambda_schicht(aufbau.at[i, "material"], lam_mat)


def dicke_fuer_wanddicke(aufbau: pd.DataFrame, ziel_wanddicke_m: float) -> float:
    """Dicke der ersten anpassbaren Schicht, damit die Wand die Zielwanddicke erreicht (E06):
        d = Wanddicke_Ziel − Σ d der übrigen Schichten
    Löst Berechnungsfehler aus, wenn die übrigen Schichten schon so dick oder dicker sind
    (die anpassbare Schicht würde 0 oder negativ). Der U-Wert ergibt sich danach aus
    passe_an(..., dicke_vorgabe_m=d) wie bisher nach DIN EN ISO 6946.
    """
    from lce.einheiten import m_in_cm

    if ziel_wanddicke_m <= 0:
        raise Berechnungsfehler(f"Zielwanddicke muss größer als 0 sein, ist {ziel_wanddicke_m}")
    anpassbar = aufbau.index[aufbau["anpassbar"] == 1].tolist()
    if not anpassbar:
        raise Berechnungsfehler("keine Schicht mit anpassbar = 1, Wanddicke lässt sich nicht einstellen")
    uebrige = float(aufbau["dicke_m"].astype(float).drop(index=anpassbar[0]).sum())
    d = ziel_wanddicke_m - uebrige
    if d <= 1e-9:                         # 0 oder negativ (Gleitkommarauschen inbegriffen)
        raise Berechnungsfehler(
            f"Zielwanddicke {m_in_cm(ziel_wanddicke_m):.1f} cm nicht erreichbar: die übrigen "
            f"Schichten sind zusammen schon {m_in_cm(uebrige):.1f} cm dick, die anpassbare Schicht "
            f"würde {m_in_cm(d):.1f} cm")
    return d
