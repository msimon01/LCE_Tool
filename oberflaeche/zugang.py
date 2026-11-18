'''Zugangsschutz und geschützte Daten über Streamlit-Secrets (E08).

Secrets stehen lokal in .streamlit/secrets.toml (nicht auf GitHub, siehe .gitignore) und
online in den App-Einstellungen von Streamlit Community Cloud (Settings → Secrets):

    [zugang]
    passwort = "..."

    [daten]
    kosten_csv = """
    material_id;kosten_fix_eur_m2;...
    ...
    """

Ohne Eintrag gilt: kein Passwort (lokale Nutzung) und Kosten aus daten/kosten.csv.
Das Passwort schützt die Oberfläche, nicht den Code. Es ist ein gemeinsames Passwort
für eine Lehrveranstaltung, keine persönliche Anmeldung.
'''

from __future__ import annotations

import hmac

import streamlit as st

SCHLUESSEL_OK = "_zugang_ok"


def _secret(bereich: str, schluessel: str) -> str | None:
    """Wert aus st.secrets oder None, wenn es keine Secrets bzw. den Eintrag nicht gibt."""
    try:
        if bereich in st.secrets and schluessel in st.secrets[bereich]:
            wert = str(st.secrets[bereich][schluessel])
            return wert if wert.strip() else None
    except (FileNotFoundError, KeyError, AttributeError):
        pass
    return None


def passwort_aktiv() -> bool:
    return _secret("zugang", "passwort") is not None


def zugang_pruefen() -> bool:
    """True, wenn kein Passwort eingestellt ist oder es in dieser Sitzung richtig eingegeben wurde.
    Sonst wird die Passwortabfrage angezeigt und False zurückgegeben."""
    passwort = _secret("zugang", "passwort")
    if passwort is None or st.session_state.get(SCHLUESSEL_OK):
        return True

    def pruefen():
        eingabe = st.session_state.get("_zugang_eingabe", "")
        # Vergleich in konstanter Zeit, Eingabe danach nicht im Sitzungszustand behalten
        st.session_state[SCHLUESSEL_OK] = hmac.compare_digest(eingabe.encode(), passwort.encode())
        st.session_state["_zugang_falsch"] = not st.session_state[SCHLUESSEL_OK]
        st.session_state["_zugang_eingabe"] = ""

    links, mitte, rechts = st.columns([1, 2, 1])
    with mitte:
        st.markdown("# 🧱 LCE-Tool Außenwand")
        st.caption("Variantenvergleich im Modul Life-Cycle-Engineering, TH Köln. "
                   "Der Zugang ist auf die Lehrveranstaltung beschränkt.")
        st.text_input("Passwort", type="password", key="_zugang_eingabe", on_change=pruefen)
        st.button("Anmelden", on_click=pruefen, type="primary", width="stretch")
        if st.session_state.get("_zugang_falsch"):
            st.error("Passwort falsch.")
    return False


def abmelden_knopf() -> None:
    """Abmelden in der Seitenleiste, nur wenn ein Passwort aktiv ist."""
    if passwort_aktiv() and st.session_state.get(SCHLUESSEL_OK):
        if st.sidebar.button("Abmelden", icon=":material/logout:"):
            st.session_state[SCHLUESSEL_OK] = False
            st.rerun()


def kosten_aus_secret() -> str | None:
    """CSV-Text der Kosten aus dem Secret [daten] kosten_csv, sonst None."""
    return _secret("daten", "kosten_csv")
