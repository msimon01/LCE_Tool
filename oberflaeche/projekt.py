"""Projektdatei (.json): Einstellungen, Variantenauswahl, Gewichte, Suchbereich und Aufbauten.

Gespeichert wird in SI-Einheiten bzw. Anteilen wie im Rechenkern (Dicken der Aufbauten in cm
wie im Editor, Spalte dicke_cm). daten/ bleibt unverändert; die Projektdatei enthält nur
das, was in der Oberfläche geändert werden kann.
"""

from __future__ import annotations

import json
from dataclasses import MISSING, asdict, fields
from datetime import datetime

import pandas as pd

from lce.berechnung import Einstellungen

FORMAT = "LCE-Tool-Projekt"
VERSION = 1
EDITOR_SPALTEN = ["variante", "position", "schicht", "material", "dicke_cm", "anpassbar"]


class Projektfehler(ValueError):
    """Projektdatei nicht lesbar oder unvollständig."""


def projekt_json(einst: Einstellungen, auswahl: list[str], aufbauten: pd.DataFrame,
                 gewichte: dict[str, float] | None, suchbereich: dict[str, float] | None) -> str:
    daten = {
        "format": FORMAT, "version": VERSION,
        "gespeichert": datetime.now().isoformat(timespec="seconds"),
        "einstellungen": asdict(einst),
        "auswahl": list(auswahl),
        "gewichte": gewichte,
        "suchbereich": suchbereich,
        "aufbauten": json.loads(aufbauten[EDITOR_SPALTEN].to_json(orient="records")),
    }
    return json.dumps(daten, ensure_ascii=False, indent=2)


def projekt_lesen(text: str | bytes) -> dict:
    """Prüft und liest eine Projektdatei. Löst Projektfehler mit Begründung aus."""
    try:
        daten = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Projektfehler(f"keine gültige JSON-Datei ({e})") from None
    if not isinstance(daten, dict) or daten.get("format") != FORMAT:
        raise Projektfehler("keine Projektdatei des LCE-Tools")
    if daten.get("version") != VERSION:
        raise Projektfehler(f"Version {daten.get('version')} wird nicht unterstützt")
    alle = {f.name for f in fields(Einstellungen)}
    pflicht = {f.name for f in fields(Einstellungen) if f.default is MISSING}
    einst = daten.get("einstellungen") or {}
    fehlend = sorted(pflicht - set(einst))
    if fehlend:
        raise Projektfehler("in den Einstellungen fehlen " + ", ".join(fehlend))
    aufbauten = pd.DataFrame(daten.get("aufbauten") or [])
    fehlend = [s for s in EDITOR_SPALTEN if s not in aufbauten.columns]
    if aufbauten.empty or fehlend:
        raise Projektfehler("Aufbauten fehlen oder sind unvollständig")
    return {
        # Felder mit Standardwert (z. B. modus aus E06) dürfen in älteren Dateien fehlen
        "einstellungen": Einstellungen(**{k: einst[k] for k in alle if k in einst}),
        "auswahl": list(daten.get("auswahl") or []),
        "gewichte": daten.get("gewichte"),
        "suchbereich": daten.get("suchbereich"),
        "aufbauten": aufbauten[EDITOR_SPALTEN],
        "gespeichert": daten.get("gespeichert", ""),
    }
