"""Einzige Stelle für Einheitenumrechnungen (Regel 6).

Intern rechnet das Tool in SI-Einheiten (m, kg, s, J, W, K). Umrechnungen in
Anzeigeeinheiten stehen ausschließlich hier.
"""

# Definition der Einheit: 1 m = 100 cm
CM_JE_M = 100.0


def m_in_cm(wert_m: float) -> float:
    """Länge von m in cm: l_cm = l_m · 100."""
    return wert_m * CM_JE_M
