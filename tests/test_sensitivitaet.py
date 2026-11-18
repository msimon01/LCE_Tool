"""Tests zur Robustheit (Sensitivität)."""

from __future__ import annotations

import pytest

from lce.berechnung import standard_einstellungen
from lce.sensitivitaet import GROESSEN, hebel, spannen_aus_daten, untersuche
from lce.waermeschutz import Berechnungsfehler

SB = "Stahlbeton + EPS-WDVS"


@pytest.fixture(scope="module")
def sens(testdaten):
    return untersuche(testdaten, standard_einstellungen(testdaten))


def _abw(sens, groesse, richtung, kriterium, variante=SB):
    df = sens.ergebnis
    z = df[(df.variante == variante) & (df.groesse == groesse) & (df.richtung == richtung)
           & (df.kriterium == kriterium)]
    return float(z["abweichung"].iloc[0])


def test_spannen_aus_parameter(testdaten):
    s = spannen_aus_daten(testdaten)
    assert s["sensitivitaet_kosten"] == pytest.approx(0.20)
    assert s["sensitivitaet_kennwerte"] == pytest.approx(0.10)


def test_fehlende_spanne_wird_gemeldet(testdaten):
    daten = dict(testdaten)
    p = testdaten["parameter.csv"]
    daten["parameter.csv"] = p[p["schluessel"] != "sensitivitaet_wirtschaft"]
    with pytest.raises(Berechnungsfehler, match="sensitivitaet_wirtschaft"):
        spannen_aus_daten(daten)


def test_vollstaendig(sens):
    assert not sens.fehler
    # 3 Varianten × Größen × 2 Richtungen × 3 Kriterien
    assert len(sens.ergebnis) == 3 * len(GROESSEN) * 2 * 3


def test_richtungen_plausibel(sens):
    # Energiepreis wirkt nur auf Kosten, und zwar gleichsinnig
    assert _abw(sens, "Energiepreis", "+", "lcc") > 0 > _abw(sens, "Energiepreis", "−", "lcc")
    assert _abw(sens, "Energiepreis", "+", "gwp") == pytest.approx(0)
    # Kennwerte +10 % → GWP der Konstruktion steigt, Kosten unverändert
    assert _abw(sens, "GWP-/PENRT-Kennwerte Baustoffe", "+", "gwp") > 0
    assert _abw(sens, "GWP-/PENRT-Kennwerte Baustoffe", "+", "lcc") == pytest.approx(0)
    # höherer Zins → kleinere Barwerte
    assert _abw(sens, "Zins", "+", "lcc") < 0
    # mehr Heizgradstunden → mehr Betrieb
    assert _abw(sens, "Heizgradstunden", "+", "gwp") > 0


def test_kennwerte_linear(sens, testdaten):
    # GWP-Summe = Konstruktion (∝ Kennwerte) + B6: +10 % Kennwerte → +10 % der Konstruktion
    from lce.berechnung import berechne
    z = berechne(testdaten, standard_einstellungen(testdaten)).varianten.set_index("variante").loc[SB]
    konstruktion = z["gwp_summe_kg_co2e_m2"] - z["gwp_b6_kg_co2e_m2"]
    assert _abw(sens, "GWP-/PENRT-Kennwerte Baustoffe", "+", "gwp") == pytest.approx(0.1 * konstruktion)


def test_hebel_sortiert(sens):
    h = hebel(sens, SB, "lcc")
    assert list(h["spannweite"]) == sorted(h["spannweite"], reverse=True)
    assert set(h.columns) >= {"groesse", "minus", "plus", "spanne"}


def test_rangfolge(sens):
    assert set(sens.basis_rangfolge) == {"gwp", "penrt", "lcc"}
    assert sens.rangwechsel["geaendert"].dtype == bool
