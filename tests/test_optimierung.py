"""Tests zur optimalen Dämmdicke (tests/testdaten/ enthält die Optimierungsparameter)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lce.berechnung import berechne_variante, standard_einstellungen
from lce.optimierung import (KRITERIEN, Suchbereich, _verlauf_voll, optimiere, optimum,
                             pruefe_suchbereich, suchbereich_aus_daten, verlauf_spalte)
from lce.waermeschutz import Berechnungsfehler

SB = "Stahlbeton + EPS-WDVS"
HR = "Holzrahmen + Holzfaser"


@pytest.fixture(scope="module")
def einst(testdaten):
    return standard_einstellungen(testdaten)


@pytest.fixture(scope="module")
def opt(testdaten, einst):
    return optimiere(testdaten, einst)


def test_suchbereich_aus_parameter(testdaten):
    s = suchbereich_aus_daten(testdaten)
    d = s.dicken()
    assert d[0] == pytest.approx(0.02) and d[-1] == pytest.approx(0.60)
    assert np.diff(d) == pytest.approx(np.full(len(d) - 1, 0.005))
    assert s.toleranz == pytest.approx(0.05)


def test_d_max_immer_enthalten():
    d = Suchbereich(0.02, 0.105, 0.01, 0.05).dicken()
    assert d[-1] == pytest.approx(0.105)


def test_fehlende_parameter_werden_gemeldet(testdaten):
    daten = dict(testdaten)
    p = testdaten["parameter.csv"]
    daten["parameter.csv"] = p[p["schluessel"] != "optimierung_toleranz"]
    with pytest.raises(Berechnungsfehler, match="optimierung_toleranz"):
        suchbereich_aus_daten(daten)


@pytest.mark.parametrize("s", [Suchbereich(0, 0.6, 0.01, 0.05), Suchbereich(0.3, 0.2, 0.01, 0.05),
                               Suchbereich(0.02, 0.6, 0, 0.05), Suchbereich(0.02, 0.6, 0.01, -0.1)])
def test_ungueltiger_suchbereich(s):
    with pytest.raises(Berechnungsfehler):
        pruefe_suchbereich(s)


def test_optimum_und_bereich_synthetisch():
    # f(d) = (d − 0,30)² + 1 → Minimum 1 bei 0,30; Bereich f ≤ 1,05 ↔ |d − 0,30| ≤ √0,05 = 0,2236
    d = np.round(np.arange(0.02, 0.6001, 0.01), 10)
    f = (d - 0.30) ** 2 + 1
    v = pd.DataFrame({"dicke_m": d, "u_w_m2k": 1 / d, verlauf_spalte("gwp", "summe"): f})
    o = optimum(v, "gwp", 0.05)
    assert o["dicke_opt_m"] == pytest.approx(0.30)
    assert o["wert_opt"] == pytest.approx(1.0)
    assert o["dicke_von_m"] == pytest.approx(0.08) and o["dicke_bis_m"] == pytest.approx(0.52)
    assert not o["am_rand"]
    o0 = optimum(v, "gwp", 0.0)
    assert o0["dicke_von_m"] == o0["dicke_bis_m"] == pytest.approx(0.30)


@pytest.mark.parametrize("variante", [SB, HR])
def test_schnelles_modell_gleich_vollstaendiger_rechnung(testdaten, einst, opt, variante):
    verlauf = opt.verlauf[opt.verlauf["variante"] == variante].reset_index(drop=True)
    stichprobe = verlauf.iloc[[1, 17, 50, 88, 115]]
    voll = _verlauf_voll(testdaten, einst, variante, stichprobe["dicke_m"].to_numpy())
    for k in KRITERIEN:
        for teil in ("konstruktion", "betrieb", "summe"):
            s = verlauf_spalte(k, teil)
            assert stichprobe[s].to_numpy() == pytest.approx(voll[s].to_numpy(), rel=1e-9)
    assert variante not in opt.hinweise or not any("vollständig" in h for h in opt.hinweise[variante])


def test_verlauf_physikalisch(opt):
    v = opt.verlauf[opt.verlauf["variante"] == SB]
    assert v["u_w_m2k"].is_monotonic_decreasing
    assert v[verlauf_spalte("gwp", "betrieb")].is_monotonic_decreasing      # mehr Dämmung, weniger B6
    assert v[verlauf_spalte("gwp", "konstruktion")].is_monotonic_increasing  # mehr EPS, mehr graue Emissionen
    assert v[verlauf_spalte("lcc", "konstruktion")].is_monotonic_increasing


def test_optimum_innen_und_besser_als_ziel_u(opt):
    o = opt.optima.set_index(["variante", "kriterium"])
    for k in KRITERIEN:
        z = o.loc[(SB, k)]
        assert not z["am_rand"]
        assert z["dicke_von_m"] <= z["dicke_opt_m"] <= z["dicke_bis_m"]
        assert z["wert_opt"] <= z["wert_ziel_u"]
        assert z["mehr_bei_ziel_u_anteil"] >= 0


def test_optimum_stimmt_mit_einzelrechnung(testdaten, einst, opt):
    z = opt.optima.set_index(["variante", "kriterium"]).loc[(SB, "lcc")]
    einzel, _, _ = berechne_variante(testdaten, einst, SB, dicke_m=z["dicke_opt_m"])
    assert einzel["lcc_summe_eur_m2"] == pytest.approx(z["wert_opt"], rel=1e-9)


def test_rand_hinweis(opt):
    o = opt.optima.set_index(["variante", "kriterium"]).loc[(HR, "gwp")]
    assert bool(o["am_rand"]) is True
    assert any("Rand" in h for h in opt.hinweise[HR])


def test_variante_ohne_anpassbare_schicht(testdaten, einst):
    daten = dict(testdaten)
    auf = testdaten["aufbauten.csv"].copy()
    auf.loc[auf["variante"] == SB, "anpassbar"] = 0
    daten["aufbauten.csv"] = auf
    erg = optimiere(daten, einst, [SB, HR])
    assert SB in erg.fehler and "anpassbar" in erg.fehler[SB]
    assert HR in set(erg.optima["variante"])


def test_csv_enthaelt_optimum(testdaten, einst, opt, tmp_path):
    from ausgabe.csv_export import schreibe_ergebnisse
    from lce.berechnung import berechne
    pfade = schreibe_ergebnisse(berechne(testdaten, einst), einst, tmp_path, opt)
    namen = {p.name for p in pfade}
    assert {"optimum.csv", "optimum_verlauf.csv"} <= namen
    csv = pd.read_csv(tmp_path / "optimum.csv", sep=";", decimal=",", encoding="utf-8-sig")
    assert len(csv) == 3 * 3
