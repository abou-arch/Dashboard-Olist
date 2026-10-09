"""Mise en forme des nombres à la française (virgule décimale, espace des milliers)."""

NBSP = " "


def number(value: float, decimals: int = 0, signed: bool = False) -> str:
    """``signed=True`` affiche un « + » devant les valeurs positives (pour les écarts)."""
    sign = "+" if signed and round(value, decimals) > 0 else ""
    text = f"{value:,.{decimals}f}"
    return sign + text.replace(",", NBSP).replace(".", ",")


def compact(value: float) -> str:
    """1 284 -> « 1 284 », 25 400 -> « 25,4 k », 15 688 396 -> « 15,7 M »."""
    for threshold, suffix in ((1e9, "Md"), (1e6, "M"), (1e4, "k")):
        if abs(value) >= threshold:
            divisor = 1e3 if suffix == "k" else threshold
            return f"{number(value / divisor, 1)}{NBSP}{suffix}"
    return number(value)


def currency(value: float, decimals: int = 0) -> str:
    return f"R${NBSP}{number(value, decimals)}"


def compact_currency(value: float) -> str:
    return f"R${NBSP}{compact(value)}"


def percent(ratio: float, decimals: int = 1, signed: bool = False) -> str:
    return f"{number(ratio * 100, decimals, signed)}{NBSP}%"
