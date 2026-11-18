"""Tests zur Projektdatei."""

from __future__ import annotations

import json

import pytest

from lce.berechnung import standard_einstellungen
from oberflaeche.projekt import Projektfehler, projekt_json, projekt_lesen
from oberflaeche.zustand import aufbauten_fuer_editor


def test_speichern_und_laden(testdaten):
    e = standard_einstellungen(testdaten).mit(ziel_u_w_m2k=0.15, rundung="kaufmaennisch")
    auf = aufbauten_fuer_editor(testdaten["aufbauten.csv"])
    auf.loc[0, "dicke_cm"] = 2.5
    text = projekt_json(e, ["Stahlbeton + EPS-WDVS"], auf, {"gwp": 2, "penrt": 1, "lcc": 1},
                        {"d_min_m": 0.02, "d_max_m": 0.4, "schritt_m": 0.01, "toleranz": 0.05})
    p = projekt_lesen(text)
    assert p["einstellungen"] == e
    assert p["auswahl"] == ["Stahlbeton + EPS-WDVS"]
    assert p["gewichte"]["gwp"] == 2
    assert p["suchbereich"]["d_max_m"] == 0.4
    assert p["aufbauten"].loc[0, "dicke_cm"] == 2.5
    assert len(p["aufbauten"]) == len(auf)


@pytest.mark.parametrize("text", ["kein json", json.dumps({"format": "anderes"}),
                                  json.dumps({"format": "LCE-Tool-Projekt", "version": 99}),
                                  json.dumps({"format": "LCE-Tool-Projekt", "version": 1,
                                              "einstellungen": {"zins": 0.01}})])
def test_ungueltige_datei(text):
    with pytest.raises(Projektfehler):
        projekt_lesen(text)
