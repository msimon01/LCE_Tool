"""Tests zu P02: flächenbezogene Masse."""

from __future__ import annotations

import pandas as pd
import pytest

from ausgabe.csv_export import SPALTEN_MASSE, schreibe_masse_csv
from lce.daten_laden import lade_daten
from lce.masse import masse_je_bestandteil, masse_je_schicht, masse_je_variante


def _materialien(**rohdichten: float) -> pd.DataFrame:
    return pd.DataFrame({"id": list(rohdichten), "rohdichte_kg_m3": list(rohdichten.values())})


def _aufbau(material: str, dicke_m: float) -> pd.DataFrame:
    return pd.DataFrame([{"variante": "V", "position": 1, "schicht": "S",
                          "material": material, "dicke_m": dicke_m, "anpassbar": 0}])


@pytest.fixture
def originaldaten(datenkopie):
    erg = lade_daten(datenkopie)
    assert erg.ok
    return erg.daten


def test_1_einheit_kg_je_m2():
    best = masse_je_bestandteil(_aufbau("m", 0.20), _materialien(m=500.0))
    assert best["masse_kg_m2"].sum() == pytest.approx(100.0)


def test_2_inhomogene_schicht():
    best = masse_je_bestandteil(_aufbau("kvh:0.12|glaswolle:0.88", 0.20),
                                _materialien(kvh=529.0, glaswolle=26.25))
    teil = best.set_index("material")["masse_kg_m2"]
    assert teil["kvh"] == pytest.approx(12.696)
    assert teil["glaswolle"] == pytest.approx(4.62)
    schicht = masse_je_schicht(best)
    assert len(schicht) == 1
    assert schicht["masse_kg_m2"].iloc[0] == pytest.approx(17.316)


def test_3_stahlbeton_eps(originaldaten):
    best = masse_je_bestandteil(originaldaten["aufbauten.csv"], originaldaten["materialien.csv"])
    assert masse_je_variante(best)["Stahlbeton + EPS-WDVS"] == pytest.approx(507.9)


def test_4_holzrahmen(originaldaten):
    best = masse_je_bestandteil(originaldaten["aufbauten.csv"], originaldaten["materialien.csv"])
    assert masse_je_variante(best)["Holzrahmen + Holzfaser"] == pytest.approx(60.665)


def test_5_csv_lesbar_und_summen_stimmen(originaldaten, tmp_path):
    best = masse_je_bestandteil(originaldaten["aufbauten.csv"], originaldaten["materialien.csv"])
    pfad = schreibe_masse_csv(best, tmp_path / "ergebnisse")
    assert pfad.name == "masse.csv" and pfad.is_file()
    assert pfad.read_bytes().startswith(b"\xef\xbb\xbf")          # UTF-8 mit BOM
    csv = pd.read_csv(pfad, sep=";", decimal=",", encoding="utf-8-sig")
    assert list(csv.columns) == SPALTEN_MASSE
    summen = csv.groupby("variante")["masse_kg_m2"].sum()
    assert summen["Stahlbeton + EPS-WDVS"] == pytest.approx(507.9)
    assert summen["Holzrahmen + Holzfaser"] == pytest.approx(60.665)
    # eine Zeile je Bestandteil: 14 Schichten, davon eine mit 2 Bestandteilen
    assert len(csv) == 15


def test_csv_wird_ueberschrieben(originaldaten, tmp_path):
    best = masse_je_bestandteil(originaldaten["aufbauten.csv"], originaldaten["materialien.csv"])
    schreibe_masse_csv(best, tmp_path)
    schreibe_masse_csv(best, tmp_path)
    csv = pd.read_csv(tmp_path / "masse.csv", sep=";", decimal=",", encoding="utf-8-sig")
    assert len(csv) == 15


def test_schichtreihenfolge_bleibt_innen_nach_aussen(originaldaten):
    best = masse_je_bestandteil(originaldaten["aufbauten.csv"], originaldaten["materialien.csv"])
    for _, g in masse_je_schicht(best).groupby("variante", sort=False):
        assert list(g["position"]) == sorted(g["position"])
