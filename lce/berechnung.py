"""Gesamtablauf je Variante: Wärmeschutz → Masse → Ökobilanz → Kosten.

Zwei Vergleichsmodi (E06):
- „gleicher U-Wert“ (Standard): die anpassbare Schicht wird auf den Ziel-U-Wert angepasst,
  alle Varianten sind thermisch gleichwertig.
- „gleiche Wanddicke“: die anpassbare Schicht wird so dick, dass die Wand die Zielwanddicke
  erreicht; der U-Wert ergibt sich daraus. Die Varianten sind dann thermisch NICHT
  gleichwertig, und B6 ist nur vereinfacht über die Heizgradstunden abgebildet
  (Q = U · Gt, ohne Gebäudebilanz, Gewinne oder Wärmebrücken).

Kein Bezug zu Konsole oder Oberfläche. Alle Werte ungerundet.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from lce.daten_laden import PFLICHTPARAMETER, STATUS_GESCHAETZT, parameter
from lce.kosten import SPALTEN_LCC, heizkosten, kosten_schichten
from lce.masse import masse_je_bestandteil
from lce.oekobilanz import (INDIKATOREN, RUNDUNG_AUFRUNDEN, betrieb_b6, oekobilanz_schichten,
                            spalte)
from lce.waermeschutz import Berechnungsfehler, dicke_fuer_wanddicke, passe_an

MODULE_SUMME = ("a1a3", "b4", "c3", "c4", "b6")   # Summe Lebenszyklus, D getrennt

MODUS_U_WERT = "u_wert"
MODUS_WANDDICKE = "wanddicke"
MODI = {MODUS_U_WERT: "gleicher U-Wert", MODUS_WANDDICKE: "gleiche Wanddicke"}


@dataclass(frozen=True)
class Einstellungen:
    """Randbedingungen einer Berechnung. Standardwerte kommen aus daten/."""

    ziel_u_w_m2k: float
    zeitraum_a: int
    startjahr: int
    heizgradstunden_kkh: float
    zins: float
    preissteigerung_bau: float
    preissteigerung_energie: float
    energietraeger_id: str
    rundung: str = RUNDUNG_AUFRUNDEN
    modus: str = MODUS_U_WERT
    ziel_wanddicke_m: float | None = None

    def mit(self, **aenderungen) -> "Einstellungen":
        return replace(self, **aenderungen)

    @property
    def modus_text(self) -> str:
        """z. B. „gleiche Wanddicke 36.0 cm“ – zur eindeutigen Kennzeichnung jeder Ausgabe."""
        from lce.einheiten import m_in_cm

        if self.modus == MODUS_WANDDICKE:
            return f"{MODI[self.modus]} {m_in_cm(self.ziel_wanddicke_m):.1f} cm"
        return f"{MODI[MODUS_U_WERT]} {self.ziel_u_w_m2k:.3f} W/(m²K)"


def standard_einstellungen(daten: dict[str, pd.DataFrame]) -> Einstellungen:
    """Werte aus parameter.csv; Standard-Energieträger = erste Zeile in energietraeger.csv."""
    return Einstellungen(
        ziel_u_w_m2k=parameter(daten, "ziel_u_w_m2k"),
        zeitraum_a=int(parameter(daten, "zeitraum_a")),
        startjahr=int(parameter(daten, "startjahr")),
        heizgradstunden_kkh=parameter(daten, "heizgradstunden_kkh"),
        zins=parameter(daten, "zins"),
        preissteigerung_bau=parameter(daten, "preissteigerung_bau"),
        preissteigerung_energie=parameter(daten, "preissteigerung_energie"),
        energietraeger_id=str(daten["energietraeger.csv"]["id"].iloc[0]),
        ziel_wanddicke_m=(parameter(daten, "ziel_wanddicke_m")
                          if "ziel_wanddicke_m" in set(daten["parameter.csv"]["schluessel"]) else None),
    )


@dataclass
class Ergebnis:
    varianten: pd.DataFrame                      # eine Zeile je Variante
    schichten: pd.DataFrame                      # eine Zeile je Schicht-Bestandteil
    fehler: dict[str, str] = field(default_factory=dict)        # Variante → Fehlertext
    hinweise: dict[str, list[str]] = field(default_factory=dict)  # Variante → Hinweise


def _geschaetzte_parameter(daten: dict[str, pd.DataFrame]) -> bool:
    p = daten["parameter.csv"]
    benutzt = p[p["schluessel"].isin(PFLICHTPARAMETER)]
    return bool(benutzt["status"].astype(str).str.lower().str.contains(STATUS_GESCHAETZT).any()) \
        if "status" in p.columns else False


def berechne_variante(daten: dict[str, pd.DataFrame], einst: Einstellungen, variante: str,
                      dicke_m: float | None = None) -> tuple[dict, pd.DataFrame, list[str]]:
    """Rechnet eine Variante. Löst Berechnungsfehler aus, wenn sie nicht rechenbar ist.

    dicke_m: Dicke der anpassbaren Schicht vorgeben statt sie auf den Ziel-U-Wert anzupassen.
    """
    mat = daten["materialien.csv"]
    aufbau = daten["aufbauten.csv"]
    aufbau = aufbau[aufbau["variante"] == variante].sort_values("position")
    rsi = parameter(daten, "rsi_m2k_w")
    rse = parameter(daten, "rse_m2k_w")
    geg_u = parameter(daten, "geg_referenz_u")

    # 1 Wärmeschutz
    if einst.modus not in MODI:
        raise Berechnungsfehler(f"unbekannter Vergleichsmodus '{einst.modus}'")
    if dicke_m is None and einst.modus == MODUS_WANDDICKE:
        if einst.ziel_wanddicke_m is None:
            raise Berechnungsfehler("Zielwanddicke fehlt (parameter.csv: ziel_wanddicke_m)")
        # E06: anpassbare Schicht auf Zielwanddicke, U-Wert ergibt sich daraus
        dicke_m = dicke_fuer_wanddicke(aufbau, einst.ziel_wanddicke_m)
    ws = passe_an(aufbau, mat, einst.ziel_u_w_m2k, rsi, rse, dicke_vorgabe_m=dicke_m)
    hinweise = list(ws.hinweise)
    if ws.u_nachher_w_m2k > geg_u + 1e-9:
        hinweise.append(f"U = {ws.u_nachher_w_m2k:.3f} W/(m²K) liegt über dem GEG-Referenzwert "
                        f"{geg_u:.2f} W/(m²K)")

    # 2 Masse mit angepasster Dicke
    best = masse_je_bestandteil(ws.schichten, mat)
    best["dicke_vorher_m"] = best["position"].map(ws.schichten.set_index("position")["dicke_vorher_m"])
    best["lambda_schicht_W_mK"] = best["position"].map(ws.schichten.set_index("position")["lambda_W_mK"])
    best["r_schicht_m2k_w"] = best["position"].map(ws.schichten.set_index("position")["r_m2k_w"])

    # 3 Ökobilanz Konstruktion
    oeko = oekobilanz_schichten(best, mat, einst.zeitraum_a, einst.rundung)
    oeko["status_oekobilanz"] = oeko["material"].map(mat.set_index("id")["status"])

    # 4 Kosten Konstruktion
    sch = kosten_schichten(oeko, daten["kosten.csv"], einst.zeitraum_a,
                           einst.zins, einst.preissteigerung_bau)

    # 5 Betrieb B6 und Heizkosten
    et = daten["energietraeger.csv"].set_index("id")
    if einst.energietraeger_id not in et.index:
        raise Berechnungsfehler(f"Energieträger '{einst.energietraeger_id}' fehlt in energietraeger.csv")
    traeger = et.loc[einst.energietraeger_id]
    b6 = betrieb_b6(ws.u_nachher_w_m2k, einst.heizgradstunden_kkh, traeger, einst.zeitraum_a,
                    einst.startjahr, daten["strom_szenario.csv"])
    heizung = heizkosten(b6["e_kwh_m2a"], float(traeger["preis_eur_kwh"]), einst.zeitraum_a,
                         einst.zins, einst.preissteigerung_energie)

    # Zusammenfassung
    z: dict = {
        "variante": variante,
        "vergleichsmodus": einst.modus_text,
        "u_vorher_w_m2k": ws.u_vorher_w_m2k,
        "u_nachher_w_m2k": ws.u_nachher_w_m2k,
        "angepasste_schicht": ws.angepasste_schicht,
        "dicke_vorher_m": ws.dicke_vorher_m,
        "dicke_nachher_m": ws.dicke_nachher_m,
        "wanddicke_m": float(ws.schichten["dicke_m"].sum()),
        "masse_kg_m2": float(sch["masse_kg_m2"].sum()),
        "q_kwh_m2a": b6["q_kwh_m2a"],
        "e_kwh_m2a": b6["e_kwh_m2a"],
    }
    for ind in INDIKATOREN:
        for mod in ("a1a3", "b4", "c3", "c4"):
            z[spalte(ind, mod)] = float(sch[spalte(ind, mod)].sum())
        z[spalte(ind, "b6")] = b6[spalte(ind, "b6")]
        z[spalte(ind, "summe")] = sum(z[spalte(ind, m)] for m in MODULE_SUMME)
        z[spalte(ind, "d")] = float(sch[spalte(ind, "d")].sum())
    for s in SPALTEN_LCC:
        z[s] = float(sch[s].sum(skipna=True))
    z["lcc_heizung_eur_m2"] = heizung
    z["lcc_summe_eur_m2"] = sum(z[s] for s in SPALTEN_LCC) + heizung
    z["kosten_unvollstaendig"] = bool(sch["kosten_fehlen"].any())

    geschaetzt = []
    if sch["status_oekobilanz"].astype(str).str.lower().str.contains(STATUS_GESCHAETZT).any():
        geschaetzt.append("Ökobilanz")
    if sch["kosten_geschaetzt"].any():
        geschaetzt.append("Kosten")
    if STATUS_GESCHAETZT in str(traeger.get("status", "")).lower():
        geschaetzt.append("Energieträger")
    if _geschaetzte_parameter(daten):
        geschaetzt.append("Parameter")
    z["geschaetzt"] = ", ".join(geschaetzt)
    if z["kosten_unvollstaendig"]:
        fehlend = sorted(set(sch.loc[sch["kosten_fehlen"], "material"]))
        hinweise.append("Kosten unvollständig: keine Kosten für " + ", ".join(fehlend))

    sch.insert(0, "variante", sch.pop("variante"))
    sch.insert(1, "vergleichsmodus", einst.modus_text)
    return z, sch, hinweise


def berechne(daten: dict[str, pd.DataFrame], einst: Einstellungen,
             varianten: list[str] | None = None) -> Ergebnis:
    """Rechnet alle (oder die gewählten) Varianten. Fehler einer Variante stoppen die anderen nicht."""
    alle = list(dict.fromkeys(daten["aufbauten.csv"]["variante"]))
    auswahl = [v for v in alle if varianten is None or v in varianten]
    zeilen, schichten, fehler, hinweise = [], [], {}, {}
    for v in auswahl:
        try:
            z, sch, h = berechne_variante(daten, einst, v)
        except Berechnungsfehler as e:
            fehler[v] = str(e)
            continue
        zeilen.append(z)
        schichten.append(sch)
        if h:
            hinweise[v] = h
    return Ergebnis(
        varianten=pd.DataFrame(zeilen),
        schichten=pd.concat(schichten, ignore_index=True) if schichten else pd.DataFrame(),
        fehler=fehler, hinweise=hinweise,
    )


def rangfolge(varianten: pd.DataFrame, spalte_wert: str) -> list[str]:
    """Varianten aufsteigend nach einem Kennwert (kleiner = besser)."""
    return list(varianten.sort_values(spalte_wert, kind="stable")["variante"])
