from __future__ import annotations

from math import sqrt
from typing import Iterable


def expectancy(r_values: Iterable[float]) -> float:
    """
    Expectativa de la estrategia medida en R.

    E[R] = media simple de los R-múltiplos.
    """
    rs = list(r_values)
    if not rs:
        return 0.0
    return sum(rs) / len(rs)


def sharpe_ratio(
    returns: Iterable[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio anualizado a partir de una serie de rendimientos periódicos.
    """
    rets = list(returns)
    if len(rets) < 2:
        return 0.0

    avg = sum(rets) / len(rets)
    var = sum((r - avg) ** 2 for r in rets) / (len(rets) - 1)
    std = sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0

    excess = avg - risk_free_rate / periods_per_year
    return (excess / std) * sqrt(periods_per_year)


def max_drawdown(equity_curve: Iterable[float]) -> float:
    """
    Calcula el máximo drawdown porcentual dado un equity curve.
    """
    values = list(equity_curve)
    if not values:
        return 0.0

    peak = values[0]
    max_dd = 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
    return max_dd
