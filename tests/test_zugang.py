"""Tests zu E08: Passwortschutz und Kosten aus einem Streamlit-Secret."""

from __future__ import annotations

import pytest

from conftest import PROJEKTORDNER, TESTDATEN
from lce.daten_laden import lies_csv_text, lies_rohdaten, pruefe_rohdaten

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(PROJEKTORDNER / "app.py")
KOSTEN_ORIGINAL = (PROJEKTORDNER / "daten" / "kosten.csv").read_text(encoding="utf-8-sig")


def _app(**secrets) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    for bereich, werte in secrets.items():
        at.secrets[bereich] = werte
    return at.run()


# --- Passwort ---------------------------------------------------------------------

def test_ohne_passwort_direkt_offen():
    at = _app()
    assert not at.exception
    assert "772.4" in [m.value for m in at.metric]


def test_passwort_sperrt_inhalt():
    at = _app(zugang={"passwort": "lce2026"})
    assert not at.exception
    assert len(at.metric) == 0                         # keine Ergebnisse vor der Anmeldung
    assert at.text_input[0].label == "Passwort"


def test_falsches_passwort():
    at = _app(zugang={"passwort": "lce2026"})
    at.text_input[0].input("falsch").run()
    assert any("falsch" in e.value for e in at.error)
    assert len(at.metric) == 0


def test_richtiges_passwort_und_seitenwechsel():
    at = _app(zugang={"passwort": "lce2026"})
    at.text_input[0].input("lce2026").run()
    assert "772.4" in [m.value for m in at.metric]
    at.switch_page("seiten/optimum.py").run()          # Anmeldung gilt für die ganze Sitzung
    assert not at.exception and len(at.metric) > 0


def test_eingabe_wird_nicht_gespeichert():
    at = _app(zugang={"passwort": "lce2026"})
    at.text_input[0].input("lce2026").run()
    assert at.session_state["_zugang_eingabe"] == ""


# --- Kosten aus Secret ------------------------------------------------------------

def test_kosten_aus_secret_werden_verwendet():
    # Stahlbeton je cm doppelt so teuer → Herstellung + 20 cm · 9,5 €/(cm·m²) = +190 €/m²
    geaendert = KOSTEN_ORIGINAL.replace("stahlbeton;0;9.5;", "stahlbeton;0;19.0;", 1)
    assert geaendert != KOSTEN_ORIGINAL
    at = _app(daten={"kosten_csv": geaendert})
    assert not at.exception
    werte = [m.value for m in at.metric]
    assert "772.4" not in werte and "962.4" in werte
    assert at.session_state["kosten_quelle"] == "Secret"


def test_kosten_secret_nicht_als_tabelle_sichtbar():
    at = _app(daten={"kosten_csv": KOSTEN_ORIGINAL})
    at.switch_page("seiten/export.py").run()
    assert not at.exception
    titel = [e.label for e in at.expander]
    assert not any(t.startswith("kosten.csv") for t in titel)
    assert any(t.startswith("materialien.csv") for t in titel)


def test_fehlerhaftes_kosten_secret_wird_gemeldet():
    kaputt = KOSTEN_ORIGINAL.replace("stahlbeton;0;9.5;", "stahlbeton;0;abc;", 1)
    at = _app(daten={"kosten_csv": kaputt})
    assert not at.exception
    assert any("kosten.csv" in e.value and "abc" in e.value for e in at.error)


def test_lies_csv_text_mit_einrueckung():
    text = "\n".join("    " + z for z in KOSTEN_ORIGINAL.splitlines())   # wie eingerückt im TOML
    df = lies_csv_text(text)
    assert list(df.columns)[0] == "material_id"
    assert len(df) == len(KOSTEN_ORIGINAL.strip().splitlines()) - 1


def test_kosten_text_durchlaeuft_dieselbe_pruefung():
    roh, fehler = lies_rohdaten(TESTDATEN)
    kopf, erste, *rest = KOSTEN_ORIGINAL.strip().splitlines()
    felder = erste.split(";")
    felder[2] = ""                                                     # kosten_je_cm leer
    roh["kosten.csv"] = lies_csv_text("\n".join([kopf, ";".join(felder), *rest]))
    erg = pruefe_rohdaten(roh, fehler)
    assert any(m.datei == "kosten.csv" and m.zeile == 2 and m.spalte == "kosten_je_cm_eur_m2"
               for m in erg.fehler)
