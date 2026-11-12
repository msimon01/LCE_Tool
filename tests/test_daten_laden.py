"""Tests zu P01: Daten laden und prüfen."""

from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import (ORIGINALDATEN, PROJEKTORDNER, entferne_spalte, ersetze_text,
                      setze_wert, _lies_zeilen, _schreib_zeilen)
from lce.daten_laden import Meldung, lade_daten, zaehle_geschaetzt, zerlege_material
from lce.einheiten import m_in_cm


def _finde(fehler: list[Meldung], datei: str, zeile=None, spalte=None) -> list[Meldung]:
    return [m for m in fehler
            if m.datei == datei
            and (zeile is None or m.zeile == zeile)
            and (spalte is None or m.spalte == spalte)]


# --- Pflichttests aus P01 ----------------------------------------------------

def test_1_originaldaten_ohne_fehler(datenkopie):
    erg = lade_daten(datenkopie)
    assert erg.fehler == []
    assert erg.ok and erg.daten is not None
    assert set(erg.daten) == {"materialien.csv", "aufbauten.csv", "kosten.csv",
                              "energietraeger.csv", "parameter.csv", "strom_szenario.csv"}


def test_2_leere_rohdichte_stahlbeton(datenkopie):
    pfad = datenkopie / "materialien.csv"
    assert _lies_zeilen(pfad)[1].startswith("stahlbeton;")
    setze_wert(pfad, 2, "rohdichte_kg_m3", "")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "materialien.csv", 2, "rohdichte_kg_m3")
    assert len(treffer) == 1 and "leer" in treffer[0].grund
    # kein Ergebnis, also insbesondere keine Rohdichte 0
    assert erg.daten is None


def test_3_dicke_keine_zahl(datenkopie):
    setze_wert(datenkopie / "aufbauten.csv", 3, "dicke_m", "abc")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "aufbauten.csv", 3, "dicke_m")
    assert len(treffer) == 1 and "abc" in treffer[0].grund
    assert erg.daten is None


def test_4_unbekanntes_material_in_aufbauten(datenkopie):
    setze_wert(datenkopie / "aufbauten.csv", 2, "material", "gibtsnicht")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "aufbauten.csv", 2, "material")
    assert len(treffer) == 1 and "gibtsnicht" in treffer[0].grund
    assert erg.daten is None


def test_5_pflichtspalte_fehlt(datenkopie):
    entferne_spalte(datenkopie / "materialien.csv", "lambda_W_mK")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "materialien.csv", spalte="lambda_W_mK")
    assert len(treffer) == 1 and "Pflichtspalte fehlt" in treffer[0].grund
    assert erg.daten is None


def test_6_anteile_inhomogene_schicht_falsch(datenkopie):
    ersetze_text(datenkopie / "aufbauten.csv", "kvh:0.12|glaswolle:0.88", "kvh:0.12|glaswolle:0.80")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "aufbauten.csv", spalte="material")
    assert len(treffer) == 1 and "0.9200" in treffer[0].grund
    assert erg.daten is None


# --- Weitere Prüfregeln aus P01 ----------------------------------------------

def test_alle_fehler_werden_gesammelt(datenkopie):
    setze_wert(datenkopie / "materialien.csv", 2, "rohdichte_kg_m3", "")
    setze_wert(datenkopie / "aufbauten.csv", 3, "dicke_m", "abc")
    setze_wert(datenkopie / "aufbauten.csv", 4, "anpassbar", "2")
    erg = lade_daten(datenkopie)
    assert len(erg.fehler) == 3


def test_datei_fehlt(datenkopie):
    (datenkopie / "kosten.csv").unlink()
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "kosten.csv")) == 1
    assert "fehlt" in erg.fehler[0].grund


def test_dezimalkomma_ist_nicht_lesbar(datenkopie):
    setze_wert(datenkopie / "parameter.csv", 2, "wert", "0,5")
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "parameter.csv", 2, "wert")) == 1


@pytest.mark.parametrize("wert", ["2", "0.5", "-1"])
def test_anpassbar_nur_0_oder_1(datenkopie, wert):
    setze_wert(datenkopie / "aufbauten.csv", 2, "anpassbar", wert)
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "aufbauten.csv", 2, "anpassbar")) == 1


@pytest.mark.parametrize("wert", ["0", "-0.1"])
def test_dicke_muss_groesser_null_sein(datenkopie, wert):
    setze_wert(datenkopie / "aufbauten.csv", 2, "dicke_m", wert)
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "aufbauten.csv", 2, "dicke_m")) == 1


def test_unbekanntes_material_in_kosten(datenkopie):
    setze_wert(datenkopie / "kosten.csv", 2, "material_id", "gibtsnicht")
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "kosten.csv", 2, "material_id")) == 1


def test_material_ohne_kosten_nur_hinweis(datenkopie):
    pfad = datenkopie / "kosten.csv"
    zeilen = _lies_zeilen(pfad)
    entfernt = zeilen.pop(1).split(";")[0]
    _schreib_zeilen(pfad, zeilen)
    erg = lade_daten(datenkopie)
    assert erg.ok
    assert any("Kosten unvollständig" in h.grund and entfernt in h.grund for h in erg.hinweise)


def test_null_ist_gueltiger_wert(datenkopie):
    erg = lade_daten(datenkopie)
    luft = erg.daten["materialien.csv"].set_index("id").loc["luft"]
    assert luft["gwp_a1a3_kg"] == 0.0


def test_zusatzspalten_bleiben_erhalten(datenkopie):
    erg = lade_daten(datenkopie)
    assert "oekobaudat_uuid" in erg.daten["materialien.csv"].columns


def test_schichten_nach_position_sortiert(datenkopie):
    pfad = datenkopie / "aufbauten.csv"
    zeilen = _lies_zeilen(pfad)
    zeilen[1], zeilen[4] = zeilen[4], zeilen[1]   # Schichtreihenfolge in der Datei vertauschen
    _schreib_zeilen(pfad, zeilen)
    erg = lade_daten(datenkopie)
    for _, gruppe in erg.daten["aufbauten.csv"].groupby("variante"):
        assert list(gruppe["position"]) == sorted(gruppe["position"])


def test_zaehle_geschaetzt(datenkopie):
    erg = lade_daten(datenkopie)
    anzahl = zaehle_geschaetzt(erg.daten)
    assert anzahl["kosten.csv"] > 0


# --- Hilfsfunktionen ---------------------------------------------------------

def test_zerlege_material():
    assert zerlege_material("eps") == [("eps", 1.0)]
    assert zerlege_material("kvh:0.12|glaswolle:0.88") == [("kvh", 0.12), ("glaswolle", 0.88)]
    with pytest.raises(ValueError):
        zerlege_material("kvh:0.12|glaswolle")
    with pytest.raises(ValueError):
        zerlege_material("kvh:abc|glaswolle:0.88")


def test_m_in_cm():
    assert m_in_cm(0.16) == pytest.approx(16.0)


# --- Programmstart -----------------------------------------------------------

def test_main_laeuft_mit_originaldaten():
    lauf = subprocess.run([sys.executable, "main.py"], cwd=PROJEKTORDNER,
                          capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "keine Fehler" in lauf.stdout


def test_originaldaten_unveraendert_nach_tests():
    # Sicherheitsnetz: daten/ wird von keinem Test beschrieben
    assert (ORIGINALDATEN / "materialien.csv").read_text(encoding="utf-8-sig").splitlines()[1] \
        .split(";")[3] != ""


# --- Doppelte Schlüssel (Ergänzung P01) --------------------------------------

@pytest.mark.parametrize("datei, spalte, quelle, ziel", [
    ("materialien.csv", "id", 2, 3),
    ("kosten.csv", "material_id", 2, 3),
    ("energietraeger.csv", "id", 2, 3),
    ("parameter.csv", "schluessel", 2, 3),
    ("strom_szenario.csv", "jahr", 2, 3),
])
def test_doppelte_id(datenkopie, datei, spalte, quelle, ziel):
    pfad = datenkopie / datei
    kopf = _lies_zeilen(pfad)[0].split(";")
    wert = _lies_zeilen(pfad)[quelle - 1].split(";")[kopf.index(spalte)]
    setze_wert(pfad, ziel, spalte, wert)
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, datei, ziel, spalte)
    assert len(treffer) == 1
    assert f"Zeilen {quelle} und {ziel}" in treffer[0].grund
    assert erg.daten is None


def test_doppelte_jahreszahl_auch_als_dezimalzahl(datenkopie):
    setze_wert(datenkopie / "strom_szenario.csv", 3, "jahr", "2026.0")
    erg = lade_daten(datenkopie)
    assert len(_finde(erg.fehler, "strom_szenario.csv", 3, "jahr")) == 1


def test_doppelte_position_innerhalb_variante(datenkopie):
    # Zeile 3 (Stahlbeton, Position 2) bekommt Position 1 wie Zeile 2
    setze_wert(datenkopie / "aufbauten.csv", 3, "position", "1")
    erg = lade_daten(datenkopie)
    treffer = _finde(erg.fehler, "aufbauten.csv", 3, "position")
    assert len(treffer) == 1 and "Zeilen 2 und 3" in treffer[0].grund
    assert "Stahlbeton + EPS-WDVS" in treffer[0].grund


def test_gleiche_position_in_verschiedenen_varianten_erlaubt(datenkopie):
    # Originaldaten: jede Variante hat Position 1 → kein Fehler
    erg = lade_daten(datenkopie)
    assert _finde(erg.fehler, "aufbauten.csv", spalte="position") == []
