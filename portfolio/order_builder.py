from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderIntent:
    """
    Representa una intención de orden generada por la lógica de portfolio
    sin ejecutar nada contra broker ni contra la base de datos.
    """

    symbol: str
    side: str  # "BUY" o "SELL"
    qty: float
    price: float
    strategy_id: str
    reason: str


def build_order_intent(
    *,
    symbol: str,
    target_qty: float,
    current_qty: float,
    price: float,
    strategy_id: str,
    reason: str,
) -> Optional[OrderIntent]:
    """
    Construye una intención de orden para llevar la posición desde
    current_qty hasta target_qty.

    - Si target_qty == current_qty → no se genera orden.
    - Si target_qty > current_qty → BUY por (target_qty - current_qty).
    - Si target_qty < current_qty → SELL por (current_qty - target_qty).

    No tiene efectos secundarios: simplemente devuelve una OrderIntent
    o None si no es necesario cambiar la posición.
    """
    delta = target_qty - current_qty
    if abs(delta) <= 0:
        return None

    side = "BUY" if delta > 0 else "SELL"
    qty = abs(delta)

    return OrderIntent(
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        strategy_id=strategy_id,
        reason=reason,
    )
