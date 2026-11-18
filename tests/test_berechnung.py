"""Rechentests mit Sollwerten aus dem Entwicklungsplan (Abschnitt 7) auf tests/testdaten/."""

from __future__ import annotations

import pandas as pd
import pytest

from lce.berechnung import berechne, standard_einstellungen
from lce.kosten import barwertfaktor, heizkosten
from lce.oekobilanz import austausch_anzahl, emissionsfaktor_strom
from lce.waermeschutz import Berechnungsfehler, lambda_schicht

SB = "Stahlbeton + EPS-WDVS"
HR = "Holzrahmen + Holzfaser"


@pytest.fixture(scope="module")
def ergebnis(testdaten):
    return berechne(testdaten, standard_einstellungen(testdaten))


def _v(ergebnis, variante):
    return ergebnis.varianten.set_index("variante").loc[variante]


# --- Wärmeschutz und Masse (P02) ------------------------------------------------

def test_wand_stahlbeton(ergebnis):
    z = _v(ergebnis, SB)
    assert z["u_vorher_w_m2k"] == pytest.approx(0.210, abs=5e-4)
    assert z["dicke_nachher_m"] == pytest.approx(0.1686, abs=5e-5)
    assert z["u_nachher_w_m2k"] == pytest.approx(0.200, abs=1e-9)
    assert z["masse_kg_m2"] == pytest.approx(508.1, abs=0.05)


def test_mischschicht_holzrahmen(testdaten, ergebnis):
    lam = testdaten["materialien.csv"].set_index("id")["lambda_W_mK"]
    assert lambda_schicht("kvh:0.12|glaswolle:0.88", lam) == pytest.approx(0.04728)
    assert _v(ergebnis, HR)["dicke_nachher_m"] == pytest.approx(0.1557, abs=5e-5)


def test_ziel_u_nicht_erreichbar(testdaten):
    erg = berechne(testdaten, standard_einstellungen(testdaten).mit(ziel_u_w_m2k=0.6))
    assert HR in erg.fehler and "nicht erreichbar" in erg.fehler[HR]
    assert HR not in set(erg.varianten["variante"])     # keine Zahlen für diese Variante
    assert SB in set(erg.varianten["variante"])         # andere Varianten laufen weiter


def test_luft_ohne_lambda_gibt_fehler(testdaten):
    lam = testdaten["materialien.csv"].set_index("id")["lambda_W_mK"]
    with pytest.raises(Berechnungsfehler):
        lambda_schicht("luft", lam)


# --- Ökobilanz (P03) ------------------------------------------------------------

def test_oekobilanz_stahlbeton(ergebnis):
    z = _v(ergebnis, SB)
    assert z["gwp_a1a3_kg_co2e_m2"] == pytest.approx(81.2, abs=0.05)
    assert z["gwp_c3_kg_co2e_m2"] == pytest.approx(18.5, abs=0.05)
    assert z["gwp_c4_kg_co2e_m2"] == pytest.approx(0.7, abs=0.05)
    assert z["gwp_b4_kg_co2e_m2"] == pytest.approx(3.9, abs=0.05)
    assert z["q_kwh_m2a"] == pytest.approx(15.8)
    assert z["gwp_b6_kg_co2e_m2"] == pytest.approx(191.5, abs=0.05)


def test_b4_kaufmaennisch(testdaten):
    erg = berechne(testdaten, standard_einstellungen(testdaten).mit(rundung="kaufmaennisch"))
    assert _v(erg, SB)["gwp_b4_kg_co2e_m2"] == 0


@pytest.mark.parametrize("t, nd, regel, n", [
    (50, 45, "aufrunden", 1), (50, 45, "kaufmaennisch", 0),
    (50, 50, "aufrunden", 0), (50, 100, "aufrunden", 0),
    (50, 25, "aufrunden", 1), (50, 20, "aufrunden", 2), (50, 20, "kaufmaennisch", 2),
    (50, 30, "kaufmaennisch", 1), (50, 35, "kaufmaennisch", 0),
])
def test_austausch_anzahl(t, nd, regel, n):
    assert austausch_anzahl(t, nd, regel) == n


def test_strom_szenario_interpoliert():
    s = pd.DataFrame({"jahr": [2030, 2040], "emissionsfaktor_kg_kwh": [0.2, 0.1]})
    assert emissionsfaktor_strom(2035, s) == pytest.approx(0.15)
    assert emissionsfaktor_strom(2020, s) == pytest.approx(0.2)   # davor konstant
    assert emissionsfaktor_strom(2060, s) == pytest.approx(0.1)   # danach konstant


def test_d_getrennt_nicht_in_summe(ergebnis):
    z = _v(ergebnis, SB)
    summe = sum(z[f"gwp_{m}_kg_co2e_m2"] for m in ("a1a3", "b4", "c3", "c4", "b6"))
    assert z["gwp_summe_kg_co2e_m2"] == pytest.approx(summe)
    assert z["gwp_d_kg_co2e_m2"] != 0


# --- Kosten (P04) ---------------------------------------------------------------

def test_kosten_stahlbeton(ergebnis):
    z = _v(ergebnis, SB)
    assert z["lcc_herstellung_eur_m2"] == pytest.approx(325.7, abs=0.05)
    assert z["lcc_rueckbau_eur_m2"] == pytest.approx(101.7, abs=0.05)
    assert z["lcc_heizung_eur_m2"] == pytest.approx(293.8, abs=0.05)
    assert z["lcc_summe_eur_m2"] == pytest.approx(772.4, abs=0.05)


def test_kosten_ersatz_stahlbeton(ergebnis):
    # Sollwert Entwicklungsplan: 51,2 €/m². Handrechnung: Außenputz ND 45 a, 1 Austausch
    # im Jahr 45: (K_H 35 + K_A 6) · (1,02/1,015)^45 = 41 · 1,24748 = 51,15 €/m².
    # Abweichung 0,05 → Sollwert bitte mit der Excel-Handrechnung klären.
    assert _v(ergebnis, SB)["lcc_ersatz_eur_m2"] == pytest.approx(51.15, abs=0.01)


def test_barwertfaktor():
    assert barwertfaktor(0, 0.02, 0.015) == 1
    assert barwertfaktor(1, 0.02, 0.015) == pytest.approx(1.02 / 1.015)


def test_heizkosten_ohne_preissteigerung_und_zins():
    assert heizkosten(10, 0.1, 50, 0.0, 0.0) == pytest.approx(50.0)


def test_kosten_unvollstaendig(testdaten):
    daten = dict(testdaten)
    daten["kosten.csv"] = testdaten["kosten.csv"][testdaten["kosten.csv"]["material_id"] != "eps"]
    erg = berechne(daten, standard_einstellungen(daten))
    z = _v(erg, SB)
    assert bool(z["kosten_unvollstaendig"]) is True
    assert any("Kosten unvollständig" in h for h in erg.hinweise[SB])


def test_geschaetzt_gekennzeichnet(ergebnis):
    assert "Kosten" in _v(ergebnis, SB)["geschaetzt"]


# --- Ausgabe --------------------------------------------------------------------

def test_csv_gleich_ergebnis(ergebnis, testdaten, tmp_path):
    from ausgabe.csv_export import schreibe_ergebnisse
    schreibe_ergebnisse(ergebnis, standard_einstellungen(testdaten), tmp_path)
    csv = pd.read_csv(tmp_path / "varianten.csv", sep=";", decimal=",", encoding="utf-8-sig")
    assert csv.set_index("variante").loc[SB, "lcc_summe_eur_m2"] == pytest.approx(772.4, abs=0.05)
    assert {"varianten.csv", "schichten.csv", "masse.csv", "einstellungen.csv"} <= \
        {p.name for p in tmp_path.iterdir()}
