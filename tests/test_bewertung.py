"""Tests zur Gesamtbewertung."""

from __future__ import annotations

import pandas as pd
import pytest

from lce.berechnung import berechne, standard_einstellungen
from lce.bewertung import bewerte, gewichte_aus_daten, punkte
from lce.waermeschutz import Berechnungsfehler


def test_punkte_relativ_zur_besten():
    p = punkte(pd.Series([100.0, 120.0, 250.0]))
    assert list(p) == pytest.approx([100.0, 80.0, 0.0])        # 150 % schlechter → 0, nicht negativ


def test_punkte_mit_negativem_bestwert():
    p = punkte(pd.Series([-10.0, -5.0]))
    assert list(p) == pytest.approx([100.0, 50.0])


def _var(gwp, penrt, lcc):
    return pd.DataFrame({"variante": ["A", "B"], "gwp_summe_kg_co2e_m2": gwp,
                         "penrt_summe_mj_m2": penrt, "lcc_summe_eur_m2": lcc})


def test_gewichtung():
    var = _var([100, 120], [1000, 1000], [600, 300])        # A bei GWP besser, B bei Kosten
    nur_gwp = bewerte(var, {"gwp": 1, "penrt": 0, "lcc": 0}).set_index("variante")
    assert nur_gwp.loc["A", "rang"] == 1 and nur_gwp.loc["B", "punkte_gesamt"] == pytest.approx(80)
    nur_lcc = bewerte(var, {"gwp": 0, "penrt": 0, "lcc": 1}).set_index("variante")
    assert nur_lcc.loc["B", "rang"] == 1 and nur_lcc.loc["A", "punkte_gesamt"] == pytest.approx(0)
    gleich = bewerte(var, {"gwp": 1, "penrt": 1, "lcc": 1}).set_index("variante")
    assert gleich.loc["A", "punkte_gesamt"] == pytest.approx((100 + 100 + 0) / 3)
    assert gleich.loc["B", "punkte_gesamt"] == pytest.approx((80 + 100 + 100) / 3)


@pytest.mark.parametrize("g", [{"gwp": 0, "penrt": 0, "lcc": 0}, {"gwp": -1, "penrt": 1, "lcc": 1}])
def test_ungueltige_gewichte(g):
    with pytest.raises(Berechnungsfehler):
        bewerte(_var([1, 2], [1, 2], [1, 2]), g)


def test_mit_testdaten(testdaten):
    erg = berechne(testdaten, standard_einstellungen(testdaten))
    b = bewerte(erg.varianten, gewichte_aus_daten(testdaten))
    assert b.iloc[0]["variante"] == "Holzrahmen + Holzfaser"       # bei allen drei Kriterien beste
    assert b.iloc[0]["punkte_gesamt"] == pytest.approx(100)
    assert list(b["rang"]) == [1, 2, 3]
