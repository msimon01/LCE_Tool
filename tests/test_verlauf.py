"""Tests zu E04: kumulierter Verlauf über den Betrachtungszeitraum."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lce.berechnung import berechne, standard_einstellungen
from lce.verlauf import austauschjahr, kurve, schnittpunkte, verlauf, verlauf_spalte

HR = "Holzrahmen + Holzfaser"


def _verlauf(daten, einst):
    erg = berechne(daten, einst)
    v, fehler = verlauf(daten, einst, ergebnis=erg)
    assert not fehler
    return erg, v


@pytest.mark.parametrize("rundung", ["aufrunden", "kaufmaennisch"])
@pytest.mark.parametrize("traeger", ["gas", "waermepumpe"])
def test_1_letzter_wert_gleich_summe(testdaten, rundung, traeger):
    einst = standard_einstellungen(testdaten).mit(rundung=rundung, energietraeger_id=traeger)
    erg, v = _verlauf(testdaten, einst)
    ende = v[v["zeitpunkt"] == einst.zeitraum_a + 1].set_index("variante")
    var = erg.varianten.set_index("variante")
    for ind, einheit in (("gwp", "kg_co2e_m2"), ("penrt", "mj_m2")):
        summe = var[f"{ind}_summe_{einheit}"]
        ohne_b6 = summe - var[f"{ind}_b6_{einheit}"]
        assert kurve(ende.reset_index(), ind, True).to_numpy() == pytest.approx(summe.to_numpy())
        assert kurve(ende.reset_index(), ind, False).to_numpy() == pytest.approx(ohne_b6.to_numpy())


def _stufen_holzrahmen(testdaten, rundung):
    _, v = _verlauf(testdaten, standard_einstellungen(testdaten).mit(rundung=rundung))
    k = v[v["variante"] == HR].set_index("zeitpunkt")[verlauf_spalte("gwp", "konstruktion_kum")]
    return k, k.diff().fillna(k)


def test_2_holzrahmen_aufrunden(testdaten):
    k, stufe = _stufen_holzrahmen(testdaten, "aufrunden")
    assert k[0] == pytest.approx(-24.1, abs=0.05)
    assert stufe[35] == pytest.approx(0.9, abs=0.05)        # PE-Folie, ND 35 a
    assert stufe[45] == pytest.approx(3.1, abs=0.05)        # Außenputz, ND 45 a
    assert stufe[51] == pytest.approx(49.8, abs=0.1)        # Rückbau C3 + C4
    sonst = stufe.drop(index=[0, 35, 45, 51])
    assert np.allclose(sonst, 0)                            # sonst keine Stufen


def test_3_holzrahmen_kaufmaennisch_ohne_stufen(testdaten):
    _, stufe = _stufen_holzrahmen(testdaten, "kaufmaennisch")
    assert stufe[35] == pytest.approx(0) and stufe[45] == pytest.approx(0)


def test_4_mit_b6_gleich_steil(testdaten):
    _, v = _verlauf(testdaten, standard_einstellungen(testdaten))
    b6 = v.pivot(index="zeitpunkt", columns="variante", values=verlauf_spalte("gwp", "betrieb"))
    jahre = b6.loc[1:50]
    assert (jahre.max(axis=1) - jahre.min(axis=1)).abs().max() == pytest.approx(0, abs=1e-9)
    assert (jahre > 0).all().all()


def test_strom_faktor_je_jahr(testdaten):
    _, v = _verlauf(testdaten, standard_einstellungen(testdaten).mit(energietraeger_id="waermepumpe"))
    b6 = v[v["variante"] == HR].set_index("zeitpunkt")[verlauf_spalte("gwp", "betrieb")]
    assert b6[1] > b6[10] > b6[30]                          # Strom wird sauberer
    assert b6[30] == pytest.approx(b6[50])                  # nach 2050 konstant


@pytest.mark.parametrize("k, nd, t, jahr", [(1, 45, 50, 45), (1, 35, 50, 35), (2, 20, 50, 40),
                                            (1, 37.5, 50, 38), (3, 20, 50, 50)])
def test_austauschjahr(k, nd, t, jahr):
    assert austauschjahr(k, nd, t) == jahr


def _synthetisch(a, b):
    zeit = np.arange(len(a))
    return pd.concat([pd.DataFrame({"variante": "A", "zeitpunkt": zeit, "art": "Nutzung",
                                    verlauf_spalte("gwp", "summe_kum"): a}),
                      pd.DataFrame({"variante": "B", "zeitpunkt": zeit, "art": "Nutzung",
                                    verlauf_spalte("gwp", "summe_kum"): b})])


def test_schnittpunkt_interpoliert():
    # A: 0, 10, 20, 30; B: 15, 15, 15, 15 → Schnitt bei 1,5
    s = schnittpunkte(_synthetisch([0, 10, 20, 30], [15, 15, 15, 15]), "gwp", True)
    assert len(s) == 1
    assert s.iloc[0]["zeitpunkt"] == pytest.approx(1.5)
    assert s.iloc[0]["vorher_besser"] == "A" and s.iloc[0]["nachher_besser"] == "B"


def test_beruehrung_ohne_kreuzung_ist_kein_schnitt():
    s = schnittpunkte(_synthetisch([0, 15, 10, 5], [15, 15, 15, 15]), "gwp", True)
    assert s.empty


def test_schnitt_beim_rueckbau():
    # Zeitpunkte 0 … 3, T = 2: Wechsel zwischen 2 und 3 = Rückbau
    s = schnittpunkte(_synthetisch([0, 1, 2, 30], [5, 5, 5, 6]), "gwp", True)
    assert bool(s.iloc[0]["beim_rueckbau"]) is True


def test_csv_verlauf(testdaten, tmp_path):
    from ausgabe.csv_export import schreibe_ergebnisse
    einst = standard_einstellungen(testdaten)
    erg, v = _verlauf(testdaten, einst)
    schreibe_ergebnisse(erg, einst, tmp_path, verlauf=v)
    csv = pd.read_csv(tmp_path / "verlauf.csv", sep=";", decimal=",", encoding="utf-8-sig")
    assert len(csv) == 3 * (einst.zeitraum_a + 2)        # je Variante Jahr 0 … T und Rückbau
    assert {"variante", "zeitpunkt", "kalenderjahr", "art"} <= set(csv.columns)
