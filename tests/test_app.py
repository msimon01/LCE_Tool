"""Rauchtest der Oberfläche mit Streamlit AppTest (ohne Browser)."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from conftest import ORIGINALDATEN, PROJEKTORDNER  # noqa: E402

APP = str(PROJEKTORDNER / "app.py")
SEITEN = ["seiten/uebersicht.py", "seiten/verlauf.py", "seiten/zielkonflikt.py", "seiten/optimum.py", "seiten/robustheit.py", "seiten/details.py",
          "seiten/aufbauten.py", "seiten/export.py", "seiten/hilfe.py"]


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    return at


def test_app_startet_und_zeigt_werte_wie_rechenkern(app):
    werte = [m.value for m in app.metric]
    assert "772.4" in werte          # LCC Stahlbeton + EPS (Standardwerte) auf der Übersicht
    assert not app.error


@pytest.mark.parametrize("seite", SEITEN)
def test_alle_seiten_ohne_fehler(app, seite):
    app.switch_page(seite).run()
    assert not app.exception, app.exception


def test_app_energietraeger_und_rundung(app):
    app.sidebar.selectbox[0].select_index(1).run()
    app.sidebar.radio[0].set_value("kaufmaennisch").run()
    assert not app.exception


def test_app_ziel_u_nicht_erreichbar_bleibt_sichtbar(app):
    app.sidebar.number_input[0].set_value(0.6).run()
    assert not app.exception
    assert any("nicht erreichbar" in e.value for e in app.error)


def test_app_optimum(app):
    app.switch_page("seiten/optimum.py").run()
    assert not app.exception
    parameter = (ORIGINALDATEN / "parameter.csv").read_text(encoding="utf-8-sig")
    if "optimierung_toleranz" in parameter:
        assert any(m.label == "Optimum [cm]" for m in app.metric)
    else:
        assert any("fehlen" in w.value for w in app.warning)


def test_aufbauten_fehler_werden_gemeldet(app):
    app.switch_page("seiten/aufbauten.py").run()
    df = app.session_state["aufbauten"].copy()
    df.loc[0, "material"] = "gibtsnicht"
    app.session_state["aufbauten"] = df
    app.run()
    assert not app.exception
    assert any("gibtsnicht" in e.value for e in app.error)


def test_bericht_enthaelt_ergebnisse(app):
    from oberflaeche.bericht import erstelle_bericht
    k = app.session_state["_lce_kontext"]
    text = erstelle_bericht(k, "Testbericht")
    assert "<title>Testbericht</title>" in text
    for v in k.ergebnis.varianten["variante"]:
        assert v in text
    assert "772.4" in text                       # LCC Stahlbeton + EPS wie in der Übersicht
    assert text.count("vegaEmbed(") >= 4         # Diagramme eingebunden


def test_betrieb_schalter_gilt_seitenuebergreifend(app):
    app.switch_page("seiten/verlauf.py").run()
    app.toggle[0].set_value(False).run()
    app.switch_page("seiten/uebersicht.py").run()
    assert app.toggle[0].value is False


def test_modus_wanddicke_in_der_oberflaeche(app):
    app.session_state["e_modus"] = "wanddicke"
    app.run()
    assert not app.exception
    parameter = (ORIGINALDATEN / "parameter.csv").read_text(encoding="utf-8-sig")
    if "ziel_wanddicke_m" in parameter:
        assert any("gleiche Wanddicke" in w.value for w in app.warning)
    else:
        assert any("ziel_wanddicke_m" in w.value for w in app.sidebar.warning)
