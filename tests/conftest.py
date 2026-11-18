"""Gemeinsame Hilfen für die Tests. Getestet wird immer mit einer temporären
Kopie von daten/, daten/ selbst wird nie verändert."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PROJEKTORDNER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJEKTORDNER))

ORIGINALDATEN = PROJEKTORDNER / "daten"
TRENNZEICHEN = ";"


@pytest.fixture
def datenkopie(tmp_path: Path) -> Path:
    """Kopie aller CSV-Dateien aus daten/ in einen temporären Ordner."""
    ziel = tmp_path / "daten"
    ziel.mkdir()
    for pfad in ORIGINALDATEN.glob("*.csv"):
        shutil.copy(pfad, ziel / pfad.name)
    return ziel


def _lies_zeilen(pfad: Path) -> list[str]:
    return pfad.read_text(encoding="utf-8-sig").splitlines()


def _schreib_zeilen(pfad: Path, zeilen: list[str]) -> None:
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def setze_wert(pfad: Path, editorzeile: int, spalte: str, wert: str) -> None:
    """Ersetzt einen Wert direkt im Text (Kopfzeile = 1), ohne pandas."""
    zeilen = _lies_zeilen(pfad)
    kopf = zeilen[0].split(TRENNZEICHEN)
    felder = zeilen[editorzeile - 1].split(TRENNZEICHEN)
    felder[kopf.index(spalte)] = wert
    zeilen[editorzeile - 1] = TRENNZEICHEN.join(felder)
    _schreib_zeilen(pfad, zeilen)


def entferne_spalte(pfad: Path, spalte: str) -> None:
    zeilen = _lies_zeilen(pfad)
    i = zeilen[0].split(TRENNZEICHEN).index(spalte)
    neu = []
    for z in zeilen:
        felder = z.split(TRENNZEICHEN)
        del felder[i]
        neu.append(TRENNZEICHEN.join(felder))
    _schreib_zeilen(pfad, neu)


def ersetze_text(pfad: Path, alt: str, neu: str) -> None:
    text = pfad.read_text(encoding="utf-8-sig")
    assert alt in text, f"'{alt}' nicht in {pfad.name} gefunden"
    pfad.write_text(text.replace(alt, neu, 1), encoding="utf-8")


# Feste Kopie der Daten für Rechentests (Entwicklungsplan Abschnitt 8): bleibt gültig,
# wenn daten/ später geändert wird. Sollwerte gelten für diesen Datenstand.
TESTDATEN = PROJEKTORDNER / "tests" / "testdaten"


@pytest.fixture(scope="session")
def testdaten():
    from lce.daten_laden import lade_daten
    erg = lade_daten(TESTDATEN)
    assert erg.ok, erg.fehler
    return erg.daten
