"""Einlesen und Prüfen der CSV-Dateien aus daten/.

Es wird nichts berechnet. Fehlende oder ungültige Werte werden nie als 0
übernommen, sondern als Meldung mit Datei, Zeile und Spalte zurückgegeben
(Regel 5). Sobald ein Fehler vorliegt, gibt das Laden keine Daten zurück.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Dateiformat laut Projektvorgabe: Trennzeichen ";", Dezimalpunkt ".", UTF-8.
# "utf-8-sig" liest UTF-8 mit und ohne BOM (Excel speichert oft mit BOM).
TRENNZEICHEN = ";"
KODIERUNG = "utf-8-sig"

# Prüftoleranz für die Summe der Volumenanteile einer inhomogenen Schicht
# (Vorgabe aus Prompt P01, kein Fachwert).
TOLERANZ_ANTEILE = 0.001

# Trennzeichen innerhalb der Spalte "material" in aufbauten.csv,
# z. B. "kvh:0.12|glaswolle:0.88"
TRENNER_BESTANDTEILE = "|"
TRENNER_ANTEIL = ":"

# Textmerkmal für geschätzte Werte in der Spalte "status"
STATUS_GESCHAETZT = "geschätzt"


@dataclass(frozen=True)
class Dateischema:
    """Pflichtspalten einer Datei und welche davon Zahlen sein müssen."""

    pflicht: tuple[str, ...]
    zahlen: tuple[str, ...]


SCHEMA: dict[str, Dateischema] = {
    "materialien.csv": Dateischema(
        pflicht=(
            "id", "name", "rohdichte_kg_m3", "lambda_W_mK",
            "gwp_a1a3_kg", "gwp_c3_kg", "gwp_c4_kg", "gwp_d_kg",
            "penrt_a1a3_mj_kg", "penrt_c3_mj_kg", "penrt_c4_mj_kg", "penrt_d_mj_kg",
            "nutzungsdauer_a", "status",
        ),
        zahlen=(
            "rohdichte_kg_m3", "lambda_W_mK",
            "gwp_a1a3_kg", "gwp_c3_kg", "gwp_c4_kg", "gwp_d_kg",
            "penrt_a1a3_mj_kg", "penrt_c3_mj_kg", "penrt_c4_mj_kg", "penrt_d_mj_kg",
            "nutzungsdauer_a",
        ),
    ),
    "aufbauten.csv": Dateischema(
        pflicht=("variante", "position", "schicht", "material", "dicke_m", "anpassbar"),
        zahlen=("position", "dicke_m", "anpassbar"),
    ),
    "kosten.csv": Dateischema(
        pflicht=(
            "material_id", "kosten_fix_eur_m2", "kosten_je_cm_eur_m2",
            "abbruch_fix_eur_m2", "abbruch_je_cm_eur_m2", "status",
        ),
        zahlen=(
            "kosten_fix_eur_m2", "kosten_je_cm_eur_m2",
            "abbruch_fix_eur_m2", "abbruch_je_cm_eur_m2",
        ),
    ),
    "energietraeger.csv": Dateischema(
        pflicht=(
            "id", "name", "wirkungsgrad", "emissionsfaktor_kg_kwh",
            "primaerenergiefaktor_nren", "preis_eur_kwh", "strom",
        ),
        zahlen=(
            "wirkungsgrad", "emissionsfaktor_kg_kwh",
            "primaerenergiefaktor_nren", "preis_eur_kwh", "strom",
        ),
    ),
    "parameter.csv": Dateischema(pflicht=("schluessel", "wert"), zahlen=("wert",)),
    "strom_szenario.csv": Dateischema(
        pflicht=("jahr", "emissionsfaktor_kg_kwh"),
        zahlen=("jahr", "emissionsfaktor_kg_kwh"),
    ),
}

# Ganzzahlige Spalten (werden nach erfolgreicher Prüfung als int gespeichert)
GANZZAHLEN: dict[str, tuple[str, ...]] = {
    "aufbauten.csv": ("position", "anpassbar"),
    "strom_szenario.csv": ("jahr",),
}

# Spalten, deren Werte eindeutig sein müssen: Datei → (Schlüsselspalte, Gruppenspalte).
# Gruppenspalte None = eindeutig in der ganzen Datei, sonst nur innerhalb der Gruppe.
EINDEUTIG: dict[str, tuple[str, str | None]] = {
    "materialien.csv": ("id", None),
    "kosten.csv": ("material_id", None),
    "energietraeger.csv": ("id", None),
    "parameter.csv": ("schluessel", None),
    "strom_szenario.csv": ("jahr", None),
    "aufbauten.csv": ("position", "variante"),
}


@dataclass(frozen=True)
class Meldung:
    """Fehler oder Hinweis. zeile wie im Editor (Kopfzeile = 1), None = ganze Datei."""

    datei: str
    zeile: int | None
    spalte: str | None
    grund: str

    def __str__(self) -> str:
        teile = [self.datei]
        if self.zeile is not None:
            teile.append(f"Zeile {self.zeile}")
        if self.spalte is not None:
            teile.append(f"Spalte {self.spalte}")
        return ", ".join(teile) + f": {self.grund}"


@dataclass
class Ladeergebnis:
    """daten ist None, sobald mindestens ein Fehler vorliegt."""

    daten: dict[str, pd.DataFrame] | None
    fehler: list[Meldung] = field(default_factory=list)
    hinweise: list[Meldung] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fehler


def lies_zahl(text: str) -> float:
    """Liest eine Zahl mit Dezimalpunkt. Löst ValueError aus, wenn sie nicht lesbar ist.

    Abgelehnt werden u. a. Dezimalkomma, "nan", "inf" und Unterstriche.
    """
    t = text.strip()
    if t == "" or "_" in t:
        raise ValueError(text)
    wert = float(t)
    if not math.isfinite(wert):
        raise ValueError(text)
    return wert


def zerlege_material(text: str) -> list[tuple[str, float]]:
    """Zerlegt die Spalte "material" in (Material-ID, Volumenanteil).

    "eps" → [("eps", 1.0)]
    "kvh:0.12|glaswolle:0.88" → [("kvh", 0.12), ("glaswolle", 0.88)]
    Löst ValueError mit Begründung aus, wenn Format oder Anteilssumme ungültig sind.
    """
    t = text.strip()
    if TRENNER_BESTANDTEILE not in t and TRENNER_ANTEIL not in t:
        return [(t, 1.0)]

    bestandteile: list[tuple[str, float]] = []
    for teil in t.split(TRENNER_BESTANDTEILE):
        if teil.count(TRENNER_ANTEIL) != 1:
            raise ValueError(f"Bestandteil '{teil.strip()}' nicht im Format id:anteil")
        mat_id, anteil_text = (s.strip() for s in teil.split(TRENNER_ANTEIL))
        if mat_id == "":
            raise ValueError(f"Bestandteil '{teil.strip()}' ohne Material-ID")
        try:
            anteil = lies_zahl(anteil_text)
        except ValueError:
            raise ValueError(f"Anteil '{anteil_text}' bei '{mat_id}' ist keine lesbare Zahl") from None
        if anteil <= 0:
            raise ValueError(f"Anteil bei '{mat_id}' muss größer als 0 sein, ist {anteil_text}")
        bestandteile.append((mat_id, anteil))

    summe = sum(a for _, a in bestandteile)
    if abs(summe - 1.0) > TOLERANZ_ANTEILE:
        raise ValueError(
            f"Anteile der inhomogenen Schicht ergeben {summe:.4f} statt 1 "
            f"(Toleranz {TOLERANZ_ANTEILE})"
        )
    return bestandteile


def _lies_csv(pfad: Path) -> pd.DataFrame:
    """Liest eine CSV vollständig als Text. Leere Felder bleiben "" (nie 0 oder NaN)."""
    df = pd.read_csv(
        pfad,
        sep=TRENNZEICHEN,
        encoding=KODIERUNG,
        dtype=str,
        keep_default_na=False,
        skip_blank_lines=False,
    )
    df.columns = [str(s).strip() for s in df.columns]
    df = df.fillna("")
    # Leerzeilen entfernen, Index bleibt erhalten → Zeilennummer = Index + 2
    leer = df.apply(lambda z: all(str(w).strip() == "" for w in z), axis=1)
    return df[~leer]


def _editorzeile(index: int) -> int:
    """Zeilennummer wie im Editor: Kopfzeile = 1, erste Datenzeile = 2."""
    return int(index) + 2


def _pruefe_datei(datei: str, df: pd.DataFrame, schema: Dateischema) -> list[Meldung]:
    """Pflichtspalten, Pflichtwerte und Zahlen prüfen."""
    fehler: list[Meldung] = []
    vorhanden = [s for s in schema.pflicht if s in df.columns]
    for spalte in schema.pflicht:
        if spalte not in df.columns:
            fehler.append(Meldung(datei, 1, spalte, "Pflichtspalte fehlt"))

    for index, zeile in df.iterrows():
        nr = _editorzeile(index)
        for spalte in vorhanden:
            wert = str(zeile[spalte]).strip()
            if wert == "":
                fehler.append(Meldung(datei, nr, spalte, "Pflichtwert leer"))
            elif spalte in schema.zahlen:
                try:
                    lies_zahl(wert)
                except ValueError:
                    fehler.append(Meldung(datei, nr, spalte, f"Zahl nicht lesbar: '{wert}'"))
    return fehler


def _pruefe_eindeutig(datei: str, df: pd.DataFrame) -> list[Meldung]:
    """Doppelte Schlüssel melden (an der späteren Zeile, mit Verweis auf die frühere).

    Zahlenspalten werden als Zahl verglichen ("2026" = "2026.0"). Leere oder nicht
    lesbare Werte sind bereits gemeldet und werden hier übersprungen.
    """
    spalte, gruppe = EINDEUTIG[datei]
    if spalte not in df.columns or (gruppe is not None and gruppe not in df.columns):
        return []
    ist_zahl = spalte in SCHEMA[datei].zahlen
    fehler: list[Meldung] = []
    gesehen: dict[tuple, int] = {}
    for index, zeile in df.iterrows():
        text = str(zeile[spalte]).strip()
        if text == "":
            continue
        if ist_zahl:
            try:
                wert: object = lies_zahl(text)
            except ValueError:
                continue
        else:
            wert = text
        gruppenwert = str(zeile[gruppe]).strip() if gruppe is not None else None
        schluessel = (gruppenwert, wert)
        nr = _editorzeile(index)
        if schluessel in gesehen:
            bereich = f" in Variante '{gruppenwert}'" if gruppe is not None else ""
            fehler.append(Meldung(datei, nr, spalte,
                                  f"'{text}' doppelt{bereich} (Zeilen {gesehen[schluessel]} und {nr})"))
        else:
            gesehen[schluessel] = nr
    return fehler


def _pruefe_aufbauten(df: pd.DataFrame, material_ids: set[str] | None) -> list[Meldung]:
    """Fachliche Prüfungen für aufbauten.csv (anpassbar, dicke_m, material)."""
    datei = "aufbauten.csv"
    fehler: list[Meldung] = []
    for index, zeile in df.iterrows():
        nr = _editorzeile(index)

        if "anpassbar" in df.columns:
            try:
                anpassbar = lies_zahl(str(zeile["anpassbar"]))
                if anpassbar not in (0.0, 1.0):
                    fehler.append(Meldung(datei, nr, "anpassbar",
                                          f"muss 0 oder 1 sein, ist '{zeile['anpassbar']}'"))
            except ValueError:
                pass  # bereits als leer bzw. nicht lesbar gemeldet

        if "dicke_m" in df.columns:
            try:
                dicke = lies_zahl(str(zeile["dicke_m"]))
                if dicke <= 0:
                    fehler.append(Meldung(datei, nr, "dicke_m",
                                          f"muss größer als 0 sein, ist '{zeile['dicke_m']}'"))
            except ValueError:
                pass

        if "material" in df.columns and str(zeile["material"]).strip() != "":
            try:
                bestandteile = zerlege_material(str(zeile["material"]))
            except ValueError as e:
                fehler.append(Meldung(datei, nr, "material", str(e)))
                continue
            if material_ids is not None:
                for mat_id, _ in bestandteile:
                    if mat_id not in material_ids:
                        fehler.append(Meldung(datei, nr, "material",
                                              f"Material '{mat_id}' fehlt in materialien.csv"))
    return fehler


def _pruefe_kosten(df: pd.DataFrame, material_ids: set[str]) -> tuple[list[Meldung], list[Meldung]]:
    """Material aus kosten.csv muss in materialien.csv stehen (Fehler).
    Material ohne Kosteneintrag ergibt nur einen Hinweis."""
    datei = "kosten.csv"
    fehler: list[Meldung] = []
    hinweise: list[Meldung] = []
    if "material_id" not in df.columns:
        return fehler, hinweise
    kosten_ids: set[str] = set()
    for index, zeile in df.iterrows():
        mat_id = str(zeile["material_id"]).strip()
        if mat_id == "":
            continue
        kosten_ids.add(mat_id)
        if mat_id not in material_ids:
            fehler.append(Meldung(datei, _editorzeile(index), "material_id",
                                  f"Material '{mat_id}' fehlt in materialien.csv"))
    for mat_id in sorted(material_ids - kosten_ids):
        hinweise.append(Meldung(datei, None, "material_id",
                                f"Kosten unvollständig: kein Eintrag für Material '{mat_id}'"))
    return fehler, hinweise


def _in_zahlen_umwandeln(datei: str, df: pd.DataFrame) -> pd.DataFrame:
    """Nach erfolgreicher Prüfung: Zahlenspalten als float bzw. int speichern."""
    df = df.copy()
    for spalte in SCHEMA[datei].zahlen:
        df[spalte] = df[spalte].map(lies_zahl)
    for spalte in GANZZAHLEN.get(datei, ()):
        df[spalte] = df[spalte].astype(int)
    for spalte in df.columns:
        if df[spalte].dtype == object:
            df[spalte] = df[spalte].map(lambda w: str(w).strip())
    return df


def lade_daten(ordner: Path | str) -> Ladeergebnis:
    """Lädt und prüft alle CSV-Dateien aus `ordner`. Sammelt alle Fehler."""
    ordner = Path(ordner)
    roh: dict[str, pd.DataFrame] = {}
    fehler: list[Meldung] = []
    hinweise: list[Meldung] = []

    for datei, schema in SCHEMA.items():
        pfad = ordner / datei
        if not pfad.is_file():
            fehler.append(Meldung(datei, None, None, f"Datei fehlt ({pfad})"))
            continue
        try:
            df = _lies_csv(pfad)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
            fehler.append(Meldung(datei, None, None, f"Datei nicht lesbar: {e}"))
            continue
        fehler.extend(_pruefe_datei(datei, df, schema))
        fehler.extend(_pruefe_eindeutig(datei, df))
        roh[datei] = df

    # Querprüfungen gegen materialien.csv (nur wenn die ID-Spalte gelesen werden konnte)
    material_ids: set[str] | None = None
    mat = roh.get("materialien.csv")
    if mat is not None and "id" in mat.columns:
        material_ids = {str(i).strip() for i in mat["id"] if str(i).strip() != ""}

    if "aufbauten.csv" in roh:
        fehler.extend(_pruefe_aufbauten(roh["aufbauten.csv"], material_ids))
    if "kosten.csv" in roh and material_ids is not None:
        f, h = _pruefe_kosten(roh["kosten.csv"], material_ids)
        fehler.extend(f)
        hinweise.extend(h)

    if fehler:
        return Ladeergebnis(daten=None, fehler=fehler, hinweise=hinweise)

    daten = {datei: _in_zahlen_umwandeln(datei, df) for datei, df in roh.items()}
    # Schichten je Variante innen → außen (nach position), Reihenfolge der Varianten wie in der Datei
    auf = daten["aufbauten.csv"]
    reihenfolge = {v: i for i, v in enumerate(dict.fromkeys(auf["variante"]))}
    daten["aufbauten.csv"] = auf.sort_values(
        by=["variante", "position"], key=lambda s: s.map(reihenfolge) if s.name == "variante" else s,
        kind="stable",
    )
    return Ladeergebnis(daten=daten, fehler=[], hinweise=hinweise)


def zaehle_geschaetzt(daten: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Anzahl Einträge je Datei, deren Status "geschätzt" enthält
    (auch "teilweise geschätzt"; Groß-/Kleinschreibung egal)."""
    anzahl: dict[str, int] = {}
    for datei, df in daten.items():
        if "status" in df.columns:
            anzahl[datei] = int(
                df["status"].astype(str).str.lower().str.contains(STATUS_GESCHAETZT).sum()
            )
    return anzahl
