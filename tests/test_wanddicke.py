"""Tests zu E06: Vergleich bei gleicher Wanddicke (Handrechnung 0,36 m, Erdgas, 50 Jahre)."""

from __future__ import annotations

import json

import pytest

from lce.berechnung import MODUS_WANDDICKE, berechne, standard_einstellungen
from lce.verlauf import verlauf

SB = "Stahlbeton + EPS-WDVS"
HLZ = "Hochlochziegel + Mineralwolle-WDVS"
HR = "Holzrahmen + Holzfaser"


@pytest.fixture(scope="module")
def einst_w(testdaten):
    e = standard_einstellungen(testdaten)
    assert e.ziel_wanddicke_m == pytest.approx(0.36)            # aus parameter.csv
    return e.mit(modus=MODUS_WANDDICKE)


@pytest.fixture(scope="module")
def erg_w(testdaten, einst_w):
    return berechne(testdaten, einst_w)


@pytest.mark.parametrize("variante, dicke_cm, u, b6", [
    (SB, 13.5, 0.246, 235.5),        # Test 1
    (HLZ, 16.0, 0.197, 188.3),       # Test 2
    (HR, 26.43, 0.137, 131.2),       # Test 3
])
def test_1_bis_3_handrechnung(erg_w, variante, dicke_cm, u, b6):
    z = erg_w.varianten.set_index("variante").loc[variante]
    assert z["dicke_nachher_m"] * 100 == pytest.approx(dicke_cm, abs=0.005)
    assert z["u_nachher_w_m2k"] == pytest.approx(u, abs=5e-4)
    assert z["gwp_b6_kg_co2e_m2"] == pytest.approx(b6, abs=0.05)
    assert z["wanddicke_m"] == pytest.approx(0.36)


def test_4_nicht_erreichbar(testdaten, einst_w):
    erg = berechne(testdaten, einst_w.mit(ziel_wanddicke_m=0.20))
    assert SB in erg.fehler and "nicht erreichbar" in erg.fehler[SB]
    assert SB not in set(erg.varianten["variante"])             # nicht still weitergerechnet
    assert HR in set(erg.varianten["variante"])                 # andere Varianten laufen weiter


def test_4b_anpassbare_schicht_genau_null(testdaten, einst_w):
    # Hochlochziegel: übrige Schichten 1,5 + 17,5 + 1,0 = 20,0 cm → Dämmung wäre 0 cm
    erg = berechne(testdaten, einst_w.mit(ziel_wanddicke_m=0.20))
    assert HLZ in erg.fehler


def test_5_modus_u_wert_unveraendert(testdaten):
    z = berechne(testdaten, standard_einstellungen(testdaten)).varianten.set_index("variante").loc[SB]
    assert z["u_nachher_w_m2k"] == pytest.approx(0.200, abs=1e-9)
    assert z["lcc_summe_eur_m2"] == pytest.approx(772.4, abs=0.05)
    assert z["vergleichsmodus"].startswith("gleicher U-Wert")


def test_geg_hinweis_bei_duenner_wand(testdaten, einst_w):
    erg = berechne(testdaten, einst_w.mit(ziel_wanddicke_m=0.30))  # EPS 7,5 cm → U > 0,28
    assert any("GEG" in h for h in erg.hinweise.get(SB, []))


def test_modus_in_ausgaben(testdaten, einst_w, erg_w, tmp_path):
    from ausgabe.csv_export import schreibe_ergebnisse
    v, _ = verlauf(testdaten, einst_w, ergebnis=erg_w)
    schreibe_ergebnisse(erg_w, einst_w, tmp_path, verlauf=v)
    for name in ("varianten.csv", "schichten.csv", "verlauf.csv"):
        text = (tmp_path / name).read_text(encoding="utf-8-sig")
        assert "gleiche Wanddicke 36.0 cm" in text, name
    assert "wanddicke" in (tmp_path / "einstellungen.csv").read_text(encoding="utf-8-sig")


def test_verlauf_im_modus_wanddicke(testdaten, einst_w, erg_w):
    v, fehler = verlauf(testdaten, einst_w, ergebnis=erg_w)
    assert not fehler
    ende = v[v["zeitpunkt"] == einst_w.zeitraum_a + 1].set_index("variante")
    soll = erg_w.varianten.set_index("variante")["gwp_summe_kg_co2e_m2"]
    assert ende["gwp_summe_kum_kg_co2e_m2"].to_numpy() == pytest.approx(soll.loc[ende.index].to_numpy())


def test_alte_projektdatei_ohne_modus(testdaten):
    from oberflaeche.projekt import projekt_json, projekt_lesen
    from oberflaeche.zustand import aufbauten_fuer_editor
    e = standard_einstellungen(testdaten)
    daten = json.loads(projekt_json(e, [], aufbauten_fuer_editor(testdaten["aufbauten.csv"]), None, None))
    for feld in ("modus", "ziel_wanddicke_m"):
        daten["einstellungen"].pop(feld)
    p = projekt_lesen(json.dumps(daten))
    assert p["einstellungen"].modus == "u_wert"
