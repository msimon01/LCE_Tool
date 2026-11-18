"""Tests zu E07: Vorbereitung der Online-Bereitstellung."""

from __future__ import annotations

import ast
import re
import subprocess
import sys

import pytest

from conftest import PROJEKTORDNER

EIGENE_PAKETE = {"lce", "ausgabe", "oberflaeche", "seiten", "conftest", "main", "app"}
CODE_ORDNER = ["lce", "ausgabe", "oberflaeche", "seiten"]


def _importe() -> set[str]:
    """Oberste Paketnamen aller Importe im Programmcode (ohne Tests)."""
    dateien = [PROJEKTORDNER / "app.py", PROJEKTORDNER / "main.py"]
    for ordner in CODE_ORDNER:
        dateien += list((PROJEKTORDNER / ordner).rglob("*.py"))
    namen = set()
    for d in dateien:
        if "__pycache__" in d.parts or (d.parent.name == "ausgabe" and d.parent.parent.name == "lce"):
            continue
        for knoten in ast.walk(ast.parse(d.read_text(encoding="utf-8"))):
            if isinstance(knoten, ast.Import):
                namen |= {a.name.split(".")[0] for a in knoten.names}
            elif isinstance(knoten, ast.ImportFrom) and knoten.module and knoten.level == 0:
                namen.add(knoten.module.split(".")[0])
    return namen - EIGENE_PAKETE - set(sys.stdlib_module_names) - {"__future__"}


def _anforderungen() -> dict[str, str]:
    zeilen = (PROJEKTORDNER / "requirements.txt").read_text(encoding="utf-8").splitlines()
    paare = [re.match(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([0-9][^\s;#]*)", z) for z in zeilen]
    return {m.group(1).lower(): m.group(2) for m in paare if m}


def test_1_alle_importierten_pakete_mit_fester_version():
    fest = _anforderungen()
    fehlend = sorted(p for p in _importe() if p.lower() not in fest)
    assert not fehlend, f"in requirements.txt fehlen (mit ==): {fehlend}"
    assert "pytest" in fest


def test_1_nur_feste_versionen():
    for z in (PROJEKTORDNER / "requirements.txt").read_text(encoding="utf-8").splitlines():
        z = z.split("#")[0].strip()
        if z:
            assert "==" in z, f"Version nicht fest: {z}"


def test_2_main_aus_anderem_ordner(tmp_path):
    lauf = subprocess.run([sys.executable, str(PROJEKTORDNER / "main.py")], cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "keine Fehler" in lauf.stdout
    assert not any(tmp_path.iterdir())          # nichts im Startordner abgelegt


def test_3_ordner_beschreibbar(tmp_path):
    from oberflaeche.zustand import ordner_beschreibbar
    assert ordner_beschreibbar(tmp_path)
    assert ordner_beschreibbar(tmp_path / "neu")                  # fehlt, Elternordner beschreibbar
    assert not ordner_beschreibbar(tmp_path / "gibt" / "es" / "nicht")


def test_3_oberflaeche_schreibt_nichts(tmp_path):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    ergebnisse = PROJEKTORDNER / "ergebnisse"
    vorher = {p.name: p.stat().st_mtime for p in ergebnisse.glob("*.csv")} if ergebnisse.exists() else {}
    at = AppTest.from_file(str(PROJEKTORDNER / "app.py"), default_timeout=90).run()
    for seite in ["seiten/export.py", "seiten/optimum.py", "seiten/robustheit.py"]:
        at.switch_page(seite).run()
        assert not at.exception
    nachher = {p.name: p.stat().st_mtime for p in ergebnisse.glob("*.csv")} if ergebnisse.exists() else {}
    assert vorher == nachher                     # Seitenaufrufe legen keine Dateien an


def test_4_sitzungen_getrennt():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    a = AppTest.from_file(str(PROJEKTORDNER / "app.py"), default_timeout=90).run()
    b = AppTest.from_file(str(PROJEKTORDNER / "app.py"), default_timeout=90).run()
    df = a.session_state["aufbauten"].copy()
    df.loc[1, "dicke_cm"] = 30.0
    a.session_state["aufbauten"] = df
    a.sidebar.number_input[0].set_value(0.3).run()
    b.run()
    assert b.session_state["aufbauten"].loc[1, "dicke_cm"] == pytest.approx(20.0)
    assert b.sidebar.number_input[0].value == pytest.approx(0.2)
    assert "772.4" in [m.value for m in b.metric]
