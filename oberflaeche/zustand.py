"""Gemeinsamer Zustand aller Seiten: Daten, bearbeitete Aufbauten, Einstellungen, Ergebnisse.

app.py baut den Kontext bei jedem Lauf neu auf und legt ihn in st.session_state ab;
die Seiten lesen ihn mit kontext(). daten/ wird nie verändert.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import streamlit as st

from lce.berechnung import Einstellungen, Ergebnis, berechne
from lce.bewertung import bewerte
from lce.daten_laden import Ladeergebnis, Meldung, lies_zahl, pruefe_rohdaten
from lce.einheiten import anteil_in_prozent, cm_in_m, m_in_cm
from lce.optimierung import (OPTIMIERUNG_PARAMETER, Optimierung, Suchbereich, optimiere,
                             pruefe_suchbereich)
from lce.sensitivitaet import Sensitivitaet, spannen_aus_daten, untersuche
from lce.waermeschutz import Berechnungsfehler
from oberflaeche.projekt import Projektfehler, projekt_lesen

PROJEKTORDNER = Path(__file__).resolve().parent.parent
DATENORDNER = PROJEKTORDNER / "daten"
ERGEBNISORDNER = PROJEKTORDNER / "ergebnisse"

EDITOR_SPALTEN = ["variante", "position", "schicht", "material", "dicke_cm", "anpassbar"]
SCHLUESSEL = "_lce_kontext"

# Zwischenspeicher für Rechnungen (E07): gleiche Eingaben (Daten, Einstellungen, Auswahl)
# führen nicht zu einer neuen Rechnung, auch nicht für andere Nutzer. st.cache_data gibt je
# Abruf eine Kopie zurück, Sitzungen können sich also nicht gegenseitig verändern.
# Begrenzt, damit der Arbeitsspeicher auf dem Server nicht vollläuft.
CACHE = dict(max_entries=64, ttl=2 * 3600, show_spinner=False)


@st.cache_data(**CACHE)
def _berechne(daten, einst, auswahl):
    return berechne(daten, einst, list(auswahl))


@st.cache_data(**CACHE)
def _optimiere(daten, einst, auswahl, such):
    return optimiere(daten, einst, list(auswahl), such)


@st.cache_data(**CACHE)
def _untersuche(daten, einst, auswahl):
    return untersuche(daten, einst, list(auswahl), spannen_aus_daten(daten))


@st.cache_data(**CACHE)
def _verlauf(daten, einst, auswahl, _ergebnis, ergebnis_schluessel):
    # _ergebnis wird nicht gehasht (führender Unterstrich); ergebnis_schluessel = (einst, auswahl)
    from lce.verlauf import verlauf
    return verlauf(daten, einst, list(auswahl), _ergebnis)


# --------------------------------------------------------------------------- Aufbauten-Editor

def aufbauten_fuer_editor(aufbauten: pd.DataFrame) -> pd.DataFrame:
    df = aufbauten[["variante", "position", "schicht", "material", "dicke_m", "anpassbar"]].copy()
    df["dicke_cm"] = df["dicke_m"].map(m_in_cm)            # Umrechnung über lce.einheiten
    df["anpassbar"] = df["anpassbar"] == 1
    return df[EDITOR_SPALTEN].reset_index(drop=True)


def editor_als_rohdaten(df: pd.DataFrame) -> pd.DataFrame:
    """Editor-Tabelle → Text-Tabelle im Format von aufbauten.csv (dicke in m)."""
    def leer(w) -> bool:
        return w is None or (isinstance(w, float) and w != w) or w == ""

    def dicke_m(w):
        if leer(w):
            return ""
        try:
            return repr(cm_in_m(lies_zahl(str(w))))
        except ValueError:
            return str(w)

    def text(w):
        if leer(w):
            return ""
        if isinstance(w, float) and w.is_integer():
            return str(int(w))
        return str(w)

    out = pd.DataFrame({
        "variante": df["variante"].map(text),
        "position": df["position"].map(text),
        "schicht": df["schicht"].map(text),
        "material": df["material"].map(text),
        "dicke_m": df["dicke_cm"].map(dicke_m),
        "anpassbar": df["anpassbar"].map(lambda w: "1" if not leer(w) and bool(w) else "0"),
    })
    # vollständig leere Zeilen (z. B. frisch hinzugefügt) ignorieren
    nur_leer = (out[["variante", "schicht", "material", "dicke_m"]] == "").all(axis=1)
    return out[~nur_leer].reset_index(drop=True)


def editor_initialisieren(aufbauten: pd.DataFrame) -> None:
    if "aufbauten" not in st.session_state:
        st.session_state.aufbauten = aufbauten_fuer_editor(aufbauten)
        st.session_state.editor_version = 0


def editor_zuruecksetzen(aufbauten: pd.DataFrame) -> None:
    st.session_state.aufbauten = aufbauten_fuer_editor(aufbauten)
    st.session_state.editor_version += 1


def editor_aenderungen_uebernehmen(schluessel: str) -> None:
    """Callback des data_editor: Änderungen sofort in st.session_state.aufbauten übernehmen,
    damit sie beim Seitenwechsel erhalten bleiben."""
    delta = st.session_state.get(schluessel, {})
    df = st.session_state.aufbauten.copy()
    for zeile, werte in delta.get("edited_rows", {}).items():
        for spalte, wert in werte.items():
            df.at[int(zeile), spalte] = wert
    if delta.get("added_rows"):
        df = pd.concat([df, pd.DataFrame(delta["added_rows"])], ignore_index=True)
    if delta.get("deleted_rows"):
        df = df.drop(index=delta["deleted_rows"])
    st.session_state.aufbauten = df.reset_index(drop=True)[EDITOR_SPALTEN]
    st.session_state.editor_version += 1


# --------------------------------------------------------------------------- Kontext

@dataclass
class Kontext:
    roh: dict[str, pd.DataFrame]
    basis: Ladeergebnis                       # Daten aus daten/ (geprüft)
    geprueft: Ladeergebnis                    # mit bearbeiteten Aufbauten
    einst: Einstellungen
    such: Suchbereich | None
    such_fehler: str | None
    auswahl: list[str]
    farben: dict[str, str]
    gewichte: dict[str, float] | None = None
    ergebnis: Ergebnis | None = None
    _optimierung: Optimierung | None = field(default=None, repr=False)
    _sensitivitaet: Sensitivitaet | None = field(default=None, repr=False)
    _verlauf: tuple | None = field(default=None, repr=False)
    sens_fehler: str | None = None

    @property
    def daten_basis(self) -> dict[str, pd.DataFrame]:
        return self.basis.daten

    @property
    def daten(self) -> dict[str, pd.DataFrame] | None:
        return self.geprueft.daten

    @property
    def alle_varianten(self) -> list[str]:
        if self.daten is None:
            return []
        return list(dict.fromkeys(self.daten["aufbauten.csv"]["variante"]))

    def bewertung(self) -> pd.DataFrame | None:
        """Gesamtbewertung der berechneten Varianten (None ohne Gewichte oder Ergebnis)."""
        if self.gewichte is None or self.ergebnis is None or self.ergebnis.varianten.empty:
            return None
        try:
            return bewerte(self.ergebnis.varianten, self.gewichte)
        except Berechnungsfehler:
            return None

    def sensitivitaet(self) -> Sensitivitaet | None:
        """Robustheit, erst bei Bedarf berechnet (einmal je Lauf)."""
        if self._sensitivitaet is None and self.daten is not None and self.sens_fehler is None:
            try:
                # Robustheit rechnet immer im Modus gleicher U-Wert (E06)
                self._sensitivitaet = _untersuche(self.daten, self.einst_u_wert, tuple(self.auswahl))
            except Berechnungsfehler as e:
                self.sens_fehler = str(e)
        return self._sensitivitaet

    def verlauf(self) -> tuple[pd.DataFrame, dict[str, str]]:
        """Kumulierter Verlauf je Variante (E04), einmal je Lauf berechnet."""
        if self._verlauf is None:
            if self.daten is None or self.ergebnis is None:
                self._verlauf = (pd.DataFrame(), {})
            else:
                self._verlauf = _verlauf(self.daten, self.einst, tuple(self.auswahl), self.ergebnis,
                                         (self.einst, tuple(self.auswahl)))
        return self._verlauf

    @property
    def einst_u_wert(self) -> Einstellungen:
        return self.einst.mit(modus="u_wert")

    def ergebnis_im_modus(self, modus: str) -> Ergebnis | None:
        """Ergebnis im angegebenen Modus (für den Vergleich der Rangfolgen, E06)."""
        if self.daten is None:
            return None
        if modus == self.einst.modus:
            return self.ergebnis
        if modus == "wanddicke" and self.einst.ziel_wanddicke_m is None:
            return None
        return _berechne(self.daten, self.einst.mit(modus=modus), tuple(self.auswahl))

    def modus_ampel_moeglich(self) -> bool:
        """Die Ampel (E05) beruht auf der Robustheitsprüfung, die im Modus gleicher U-Wert rechnet."""
        return getattr(self.einst, "modus", "u_wert") == "u_wert"

    def optimierung(self) -> Optimierung | None:
        """Wird erst berechnet, wenn eine Seite sie braucht (einmal je Lauf)."""
        if self._optimierung is None and self.daten is not None and self.such is not None:
            # Optimum rechnet immer im Modus gleicher U-Wert (E06)
            self._optimierung = _optimiere(self.daten, self.einst_u_wert, tuple(self.auswahl), self.such)
        return self._optimierung


def optimierungsparameter_fehlen(daten: dict[str, pd.DataFrame]) -> list[str]:
    vorhanden = set(daten["parameter.csv"]["schluessel"])
    return [s for s in OPTIMIERUNG_PARAMETER if s not in vorhanden]


def standardwert(schluessel: str, wert) -> None:
    """Startwert einer Eingabe setzen, solange sie noch keinen Wert hat."""
    if schluessel not in st.session_state:
        st.session_state[schluessel] = wert


def baue_kontext(roh, basis, einst, auswahl, such_werte, gewichte=None) -> Kontext:
    """Prüft die bearbeiteten Aufbauten und rechnet die gewählten Varianten."""
    roh_bearbeitet = dict(roh)
    roh_bearbeitet["aufbauten.csv"] = editor_als_rohdaten(st.session_state.aufbauten)
    geprueft = pruefe_rohdaten(roh_bearbeitet)

    such, such_fehler = None, None
    if such_werte is None:
        such_fehler = ("In daten/parameter.csv fehlen: "
                       + ", ".join(optimierungsparameter_fehlen(basis.daten)))
    else:
        try:
            such = pruefe_suchbereich(Suchbereich(*such_werte))
        except Berechnungsfehler as e:
            such_fehler = str(e)

    alle = list(dict.fromkeys(geprueft.daten["aufbauten.csv"]["variante"])) if geprueft.ok else []
    k = Kontext(roh=roh, basis=basis, geprueft=geprueft, einst=einst, such=such,
                such_fehler=such_fehler, auswahl=[v for v in auswahl if v in alle] or alle,
                farben={}, gewichte=gewichte)
    if geprueft.ok:
        from oberflaeche.stil import variantenfarben
        k.farben = variantenfarben(alle)
        k.ergebnis = _berechne(geprueft.daten, einst, tuple(k.auswahl))
    st.session_state[SCHLUESSEL] = k
    return k


def kontext() -> Kontext:
    return st.session_state[SCHLUESSEL]


# --------------------------------------------------------------------------- Meldungen

def meldungen_text(meldungen: list[Meldung], editor: bool = False) -> str:
    """Fehler mit Datei, Zeile und Spalte; im Editor als Tabellenzeile/-spalte."""
    zeilen = []
    for m in meldungen:
        if editor and m.datei == "aufbauten.csv":
            ort = []
            if m.zeile is not None:
                ort.append(f"Zeile {m.zeile - 1}")
            if m.spalte is not None:
                ort.append(f"Spalte {'dicke_cm' if m.spalte == 'dicke_m' else m.spalte}")
            zeilen.append(f"- Aufbauten-Tabelle, {', '.join(ort)}: {m.grund}")
        else:
            zeilen.append(f"- {m}")
    return "\n".join(zeilen)


def fehler_in_aufbauten_hinweis() -> bool:
    """Zeigt auf Ergebnisseiten einen kurzen Hinweis, wenn die Aufbauten Fehler enthalten."""
    k = kontext()
    if not k.geprueft.ok:
        st.error("Die Aufbauten enthalten Fehler, daher wird nichts berechnet. "
                 "Details auf der Seite **Aufbauten**.")
        return True
    return False


# --------------------------------------------------------------------------- Projektdatei

def projekt_uebernehmen() -> None:
    """Callback des Datei-Uploads: Projekt lesen und alle Eingaben setzen."""
    datei = st.session_state.get("projekt_datei")
    if datei is None:
        return
    try:
        p = projekt_lesen(datei.getvalue())
    except Projektfehler as e:
        st.session_state.projekt_meldung = ("error", f"Projekt nicht geladen: {e}")
        return
    e = p["einstellungen"]
    s = st.session_state
    s.e_ziel_u, s.e_zeitraum, s.e_startjahr = e.ziel_u_w_m2k, e.zeitraum_a, e.startjahr
    s.e_gt, s.e_zins = e.heizgradstunden_kkh, e.zins
    s.e_p_bau, s.e_p_energie, s.e_rundung = e.preissteigerung_bau, e.preissteigerung_energie, e.rundung
    vorhandene_traeger = set(kontext().daten_basis["energietraeger.csv"]["id"])
    hinweis = ""
    if e.energietraeger_id in vorhandene_traeger:
        s.e_traeger = e.energietraeger_id
    else:
        hinweis = f"; Energieträger '{e.energietraeger_id}' fehlt in daten/, Auswahl unverändert"
    s.e_modus = e.modus
    if e.ziel_wanddicke_m is not None:
        s.e_wanddicke = m_in_cm(e.ziel_wanddicke_m)
    if p["suchbereich"]:
        sb = p["suchbereich"]
        s.e_d_min, s.e_d_max = m_in_cm(sb["d_min_m"]), m_in_cm(sb["d_max_m"])
        s.e_schritt, s.e_tol = m_in_cm(sb["schritt_m"]), anteil_in_prozent(sb["toleranz"])
    if p["gewichte"]:
        for kr, w in p["gewichte"].items():
            s[f"e_w_{kr}"] = float(w)
    s.aufbauten = p["aufbauten"].reset_index(drop=True)
    s.editor_version += 1
    s.e_bekannt = list(dict.fromkeys(s.aufbauten["variante"].dropna()))
    s.e_auswahl = [v for v in p["auswahl"] if v in s.e_bekannt] or s.e_bekannt
    s.projekt_meldung = ("success", f"Projekt geladen (gespeichert {p['gespeichert']}){hinweis}")


def betrieb_schalter(ziel, schluessel: str) -> bool:
    """Schalter „Betrieb einbeziehen“, gemeinsam für alle Seiten (Zustand in mit_betrieb)."""
    standardwert("mit_betrieb", True)

    def merken():
        st.session_state.mit_betrieb = st.session_state[schluessel]

    return ziel.toggle("Betrieb einbeziehen", value=st.session_state.mit_betrieb, key=schluessel,
                       on_change=merken,
                       help="B6 bzw. Heizkosten sind bei gleichem U-Wert für alle Varianten gleich "
                            "und überdecken die Unterschiede der Konstruktion. Gilt für alle Seiten.")


def ordner_beschreibbar(ordner: Path) -> bool:
    """True, wenn in den Ordner (oder, falls er fehlt, in den übergeordneten) geschrieben
    werden darf. Schreibt selbst nichts."""
    import os
    ziel = ordner if ordner.exists() else ordner.parent
    return ziel.is_dir() and os.access(ziel, os.W_OK)
