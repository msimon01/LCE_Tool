"""Tests zu E05: nicht übertroffene Varianten und Robustheits-Ampel."""

from __future__ import annotations

import pandas as pd
import pytest

from lce.abwaegung import GELB, GRUEN, ROT, ampel, nicht_uebertroffen, punktwolke
from lce.berechnung import berechne, standard_einstellungen
from lce.sensitivitaet import Sensitivitaet, untersuche


def _df(**werte):
    return pd.DataFrame([{"variante": v, "x": x, "y": y} for v, (x, y) in werte.items()])


def test_1_beide_nicht_uebertroffen():
    n = nicht_uebertroffen(_df(A=(100, 200), B=(120, 150)), "x", "y")
    assert n["A"] and n["B"]


def test_2_c_von_a_uebertroffen():
    df = _df(A=(100, 200), B=(120, 150), C=(130, 210))
    n = nicht_uebertroffen(df, "x", "y")
    assert n["A"] and n["B"] and not n["C"]
    from lce.abwaegung import uebertroffen_von
    # Prompt E05: „C ist übertroffen (von A)“. B (120, 150) ist ebenfalls in beiden Größen besser
    # als C (130, 210) und übertrifft C daher auch; geprüft wird, dass A dabei ist.
    assert set(uebertroffen_von(df, "x", "y")["C"]) == {"A", "B"}


def test_3_gleiche_werte_beide_nicht_uebertroffen():
    n = nicht_uebertroffen(_df(A=(100, 200), B=(100, 200)), "x", "y")
    assert n["A"] and n["B"]


def test_gleich_in_einer_besser_in_anderer_uebertrifft():
    n = nicht_uebertroffen(_df(A=(100, 200), B=(100, 190)), "x", "y")
    assert n["B"] and not n["A"]


@pytest.mark.parametrize("oeko", ["gwp", "penrt"])
def test_4_originaldaten_mit_betrieb(testdaten, oeko):
    var = berechne(testdaten, standard_einstellungen(testdaten)).varianten
    w = punktwolke(var, oeko, mit_betrieb=True).set_index("variante")["nicht_uebertroffen"]
    assert w["Holzrahmen + Holzfaser"]
    assert not w["Stahlbeton + EPS-WDVS"]
    assert not w["Hochlochziegel + Mineralwolle-WDVS"]


def test_punktwolke_ohne_betrieb(testdaten):
    var = berechne(testdaten, standard_einstellungen(testdaten)).varianten.set_index("variante")
    w = punktwolke(var.reset_index(), "gwp", mit_betrieb=False).set_index("variante")
    v = "Stahlbeton + EPS-WDVS"
    assert w.loc[v, "x"] == pytest.approx(var.loc[v, "gwp_summe_kg_co2e_m2"] - var.loc[v, "gwp_b6_kg_co2e_m2"])
    assert w.loc[v, "y"] == pytest.approx(var.loc[v, "lcc_summe_eur_m2"] - var.loc[v, "lcc_heizung_eur_m2"])


def _sens(faelle):
    """Synthetische Robustheit: faelle = {fallname: {variante: (oeko, lcc)}}."""
    zeilen = []
    for fall, werte in faelle.items():
        for v, (o, c) in werte.items():
            for kr, w in (("gwp", o), ("lcc", c)):
                zeilen.append({"variante": v, "groesse": fall, "richtung": "+", "spanne": 0.2,
                               "kriterium": kr, "wert": w, "wert_ohne_betrieb": w})
    return Sensitivitaet(pd.DataFrame(zeilen), pd.DataFrame(), {})


def test_ampel_gruen_gelb_rot():
    s = _sens({"F1": {"A": (100, 200), "B": (120, 150), "C": (130, 210)},
               "F2": {"A": (100, 200), "B": (90, 150), "C": (130, 210)}})
    a = ampel(s, "gwp", True).set_index("variante")
    assert a.loc["A", "ampel"] == GELB              # in F2 von B übertroffen
    assert a.loc["B", "ampel"] == GRUEN
    assert a.loc["C", "ampel"] == ROT
    assert any("F2" in f and "B" in f for f in a.loc["A", "kipp_faelle"])
    assert a.loc["A", "nicht_uebertroffen_in"] == 1 and a.loc["A", "faelle"] == 2


def test_ampel_originaldaten(testdaten):
    s = untersuche(testdaten, standard_einstellungen(testdaten))
    a = ampel(s, "gwp", True).set_index("variante")
    assert a.loc["Holzrahmen + Holzfaser", "ampel"] == GRUEN
    assert a.loc["Holzrahmen + Holzfaser", "faelle"] == 18


def test_ergebnisse_unveraendert(testdaten):
    # E05 ändert keine Rechenergebnisse: Sollwert aus P04 weiterhin
    var = berechne(testdaten, standard_einstellungen(testdaten)).varianten.set_index("variante")
    assert var.loc["Stahlbeton + EPS-WDVS", "lcc_summe_eur_m2"] == pytest.approx(772.4, abs=0.05)
