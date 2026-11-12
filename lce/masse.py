"""Flächenbezogene Masse je Schicht und je Variante.

Formel (Definition der flächenbezogenen Masse):
    m = d · Anteil · ρ                  [kg/m²] = [m] · [-] · [kg/m³]
Homogene Schicht: Anteil = 1. Inhomogene Schicht: je Bestandteil eine Teilmasse,
Schichtmasse = Σ Teilmassen. Masse je Variante = Σ Schichtmassen.

Dicken unverändert aus aufbauten.csv, Rohdichten aus materialien.csv.
Alle Werte ungerundet; gerundet wird nur in der Ausgabe.
"""

from __future__ import annotations

import pandas as pd

from lce.daten_laden import zerlege_material

SCHLUESSEL_SCHICHT = ["variante", "position", "schicht"]


def masse_je_bestandteil(aufbauten: pd.DataFrame, materialien: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile je Schicht bzw. je Bestandteil einer inhomogenen Schicht.

    Spalten: variante, position, schicht, material, anteil, dicke_m,
    rohdichte_kg_m3, masse_kg_m2 sowie material_angabe (Originaltext der Schicht).
    Erwartet geprüfte Daten aus lade_daten().
    """
    rohdichte = materialien.set_index("id")["rohdichte_kg_m3"]
    zeilen = []
    for _, s in aufbauten.iterrows():
        for mat_id, anteil in zerlege_material(s["material"]):
            rho = float(rohdichte[mat_id])
            zeilen.append({
                "variante": s["variante"],
                "position": s["position"],
                "schicht": s["schicht"],
                "material": mat_id,
                "anteil": anteil,
                "dicke_m": float(s["dicke_m"]),
                "rohdichte_kg_m3": rho,
                # m = d · Anteil · ρ
                "masse_kg_m2": float(s["dicke_m"]) * anteil * rho,
                "material_angabe": s["material"],
            })
    return pd.DataFrame(zeilen)


def masse_je_schicht(bestandteile: pd.DataFrame) -> pd.DataFrame:
    """Schichtmasse = Σ Teilmassen der Bestandteile (Reihenfolge bleibt erhalten)."""
    return (
        bestandteile
        .groupby(SCHLUESSEL_SCHICHT, sort=False, as_index=False)
        .agg(material=("material_angabe", "first"),
             dicke_m=("dicke_m", "first"),
             masse_kg_m2=("masse_kg_m2", "sum"))
    )


def masse_je_variante(bestandteile: pd.DataFrame) -> pd.Series:
    """Masse je Variante = Σ aller Schichten [kg/m²]."""
    return bestandteile.groupby("variante", sort=False)["masse_kg_m2"].sum()
