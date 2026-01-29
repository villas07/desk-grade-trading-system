from __future__ import annotations

from typing import Iterable, Tuple


def _risk_per_unit(side: str, entry_price: float, stop_price: float) -> float:
    side = side.upper()
    if side == "BUY":
        return max(0.0, entry_price - stop_price)
    if side == "SELL":
        return max(0.0, stop_price - entry_price)
    raise ValueError(f"side inválido: {side}")


def realized_pnl(
    side: str,
    entry_price: float,
    exit_price: float,
    qty: float,
) -> float:
    """
    PnL realizado en moneda de la cuenta.
    """
    side = side.upper()
    if side == "BUY":
        return (exit_price - entry_price) * qty
    if side == "SELL":
        return (entry_price - exit_price) * qty
    raise ValueError(f"side inválido: {side}")


def r_multiple(
    side: str,
    entry_price: float,
    stop_price: float,
    exit_price: float,
) -> float:
    """
    Devuelve el múltiplo de riesgo R para una operación.

    R = (pnl por unidad) / (riesgo por unidad)
    """
    rpu = _risk_per_unit(side, entry_price, stop_price)
    if rpu <= 0:
        return 0.0

    side = side.upper()
    if side == "BUY":
        pnl_per_unit = exit_price - entry_price
    else:
        pnl_per_unit = entry_price - exit_price

    return pnl_per_unit / rpu


def mae_mfe_r(
    side: str,
    entry_price: float,
    stop_price: float,
    price_path: Iterable[float],
) -> Tuple[float, float]:
    """
    Calcula MAE (Maximum Adverse Excursion) y MFE (Maximum Favourable Excursion)
    en unidades de R a partir de una serie de precios (por ejemplo cierres 1m).
    """
    rpu = _risk_per_unit(side, entry_price, stop_price)
    if rpu <= 0:
        return 0.0, 0.0

    side = side.upper()
    mae_r = 0.0
    mfe_r = 0.0

    for px in price_path:
        if side == "BUY":
            pnl_per_unit = px - entry_price
        else:
            pnl_per_unit = entry_price - px
        r_move = pnl_per_unit / rpu
        mae_r = min(mae_r, r_move)
        mfe_r = max(mfe_r, r_move)

    return mae_r, mfe_r
