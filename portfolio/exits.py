from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExitLevels:
    """
    Niveles de salida asociados a una operación.

    Para posiciones LONG:
      - stop  < entry
      - tp1   > entry
      - tp2   > tp1
      - trailing_stop opcional, siempre por encima del stop.

    Para posiciones SHORT, los signos se invierten de forma simétrica.
    """

    stop: float
    tp1: float
    tp2: float
    trailing_stop: Optional[float] = None


@dataclass(frozen=True)
class ExitDecision:
    """
    Resultado de evaluar el precio actual frente a los niveles de salida.

    action:
      - "NONE"          : no hay salida
      - "STOP"          : salida completa por stop loss
      - "TP1_PARTIAL"   : toma de beneficios parcial (1R)
      - "TP2_FULL"      : salida completa por 2R
      - "TRAIL_STOP"    : salida por trailing stop
    """

    action: str
    reason: str


def compute_atr_levels(
    *,
    side: str,
    entry_price: float,
    atr: float,
    atr_multiple_stop: float,
) -> ExitLevels:
    """
    Calcula stop y niveles de take profit basados en ATR.

    R se define como la distancia entre entry_price y stop.
    TP1 = entry ± 1R
    TP2 = entry ± 2R
    """
    if atr <= 0 or atr_multiple_stop <= 0:
        raise ValueError("ATR y múltiplo de ATR deben ser positivos")

    side = side.upper()
    risk_per_unit = atr * atr_multiple_stop

    if side == "BUY":
        stop = entry_price - risk_per_unit
        tp1 = entry_price + risk_per_unit
        tp2 = entry_price + 2 * risk_per_unit
    elif side == "SELL":
        stop = entry_price + risk_per_unit
        tp1 = entry_price - risk_per_unit
        tp2 = entry_price - 2 * risk_per_unit
    else:
        raise ValueError(f"side inválido: {side}")

    return ExitLevels(stop=stop, tp1=tp1, tp2=tp2, trailing_stop=None)


def update_trailing_stop(
    *,
    side: str,
    entry_price: float,
    current_price: float,
    risk_per_unit: float,
    existing_trailing_stop: Optional[float],
) -> Optional[float]:
    """
    Actualiza un trailing stop basado en el precio.

    Regla simple:
      - LONG: trailing_stop = max(existing, current_price - 1R)
      - SHORT: trailing_stop = min(existing, current_price + 1R)
    """
    if risk_per_unit <= 0:
        return existing_trailing_stop

    side = side.upper()

    if side == "BUY":
        candidate = current_price - risk_per_unit
        if existing_trailing_stop is None:
            return candidate
        return max(existing_trailing_stop, candidate)

    if side == "SELL":
        candidate = current_price + risk_per_unit
        if existing_trailing_stop is None:
            return candidate
        return min(existing_trailing_stop, candidate)

    raise ValueError(f"side inválido: {side}")


def evaluate_exit_decision(
    *,
    side: str,
    levels: ExitLevels,
    current_price: float,
    tp1_already_taken: bool,
) -> ExitDecision:
    """
    Evalúa qué evento de salida se dispara con el precio actual.

    Precedencia:
      1) STOP
      2) TRAILING STOP
      3) TP2
      4) TP1
      5) NONE
    """
    side = side.upper()

    # STOP
    if side == "BUY":
        if current_price <= levels.stop:
            return ExitDecision(action="STOP", reason="HARD_STOP_ATR")
        if levels.trailing_stop is not None and current_price <= levels.trailing_stop:
            return ExitDecision(action="TRAIL_STOP", reason="TRAILING_STOP_LONG")
        if current_price >= levels.tp2:
            return ExitDecision(action="TP2_FULL", reason="TAKE_PROFIT_2R_LONG")
        if not tp1_already_taken and current_price >= levels.tp1:
            return ExitDecision(action="TP1_PARTIAL", reason="TAKE_PROFIT_1R_LONG")
    elif side == "SELL":
        if current_price >= levels.stop:
            return ExitDecision(action="STOP", reason="HARD_STOP_ATR")
        if levels.trailing_stop is not None and current_price >= levels.trailing_stop:
            return ExitDecision(action="TRAIL_STOP", reason="TRAILING_STOP_SHORT")
        if current_price <= levels.tp2:
            return ExitDecision(action="TP2_FULL", reason="TAKE_PROFIT_2R_SHORT")
        if not tp1_already_taken and current_price <= levels.tp1:
            return ExitDecision(action="TP1_PARTIAL", reason="TAKE_PROFIT_1R_SHORT")
    else:
        raise ValueError(f"side inválido: {side}")

    return ExitDecision(action="NONE", reason="NO_EXIT_TRIGGERED")
