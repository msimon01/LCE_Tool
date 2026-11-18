"""Einzige Stelle für Einheitenumrechnungen (Regel 6).

Intern rechnet das Tool in SI-Einheiten (m, kg, W, K) bzw. in den Einheiten der
Datendateien (kWh, MJ, €). Umrechnungen stehen ausschließlich hier.
"""

# Definition der Einheit: 1 m = 100 cm
CM_JE_M = 100.0

# 1 = 100 % (Definition)
PROZENT_JE_ANTEIL = 100.0

# 1 kWh = 3,6 MJ (Definition)
MJ_JE_KWH = 3.6

# U [W/(m²K)] · Gt [kKh/a] = W·kKh/(m²K·a) = kWh/(m²a), also Faktor 1
KWH_JE_W_KKH = 1.0


def m_in_cm(wert_m: float) -> float:
    """Länge von m in cm: l_cm = l_m · 100."""
    return wert_m * CM_JE_M


def cm_in_m(wert_cm: float) -> float:
    """Länge von cm in m: l_m = l_cm / 100."""
    return wert_cm / CM_JE_M


def kwh_in_mj(wert_kwh: float) -> float:
    """Energie von kWh in MJ: E_MJ = E_kWh · 3,6."""
    return wert_kwh * MJ_JE_KWH


def waermeverlust_kwh_m2a(u_w_m2k: float, gt_kkh_a: float) -> float:
    """Transmissionswärmeverlust Q = U · Gt in kWh/(m²a) (Heizgradstundenverfahren)."""
    return u_w_m2k * gt_kkh_a * KWH_JE_W_KKH


def anteil_in_prozent(anteil: float) -> float:
    """Anteil in Prozent: p = a · 100."""
    return anteil * PROZENT_JE_ANTEIL


def prozent_in_anteil(prozent: float) -> float:
    """Prozent als Anteil: a = p / 100."""
    return prozent / PROZENT_JE_ANTEIL
