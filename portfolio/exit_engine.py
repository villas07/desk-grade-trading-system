from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from desk_grade.api import execute, fetch_one

from . import exits


@dataclass
class TradeContext:
    symbol: str
    strategy_id: str
    side: str  # "BUY" / "SELL"
    qty: float
    entry_price: float
    entry_ts: datetime
    stop_price: float
    tp1_price: float
    tp2_price: float
    trailing_stop: Optional[float]
    state: str  # FLAT / ENTERED / MANAGED / EXITED


class ExitEngine:
    """
    Motor de salidas:
      - Evalúa niveles de stop / TP / trailing
      - Actualiza trade_state
      - Registra trade_events

    NO ejecuta órdenes ni toca posiciones/cash directamente; sólo
    marca el estado de la operación en la base de datos.
    """

    def __init__(self) -> None:
        ...

    # -------------------------
    # Helpers de acceso a DB
    # -------------------------
    def _load_trade_state(self, symbol: str, strategy_id: str) -> Optional[TradeContext]:
        row = fetch_one(
            """
            SELECT symbol, strategy_id, state, entry_ts, entry_price, qty,
                   stop_price, tp1_price, tp2_price, trailing_price
            FROM public.trade_state
            WHERE symbol = %s
              AND strategy_id = %s
            """,
            (symbol, strategy_id),
        )
        if not row:
            return None

        qty = float(row["qty"] or 0.0)
        if qty == 0.0:
            return None

        side = "BUY" if qty > 0 else "SELL"

        return TradeContext(
            symbol=row["symbol"],
            strategy_id=row["strategy_id"],
            side=side,
            qty=qty,
            entry_price=float(row["entry_price"]),
            entry_ts=row["entry_ts"],
            stop_price=float(row["stop_price"]),
            tp1_price=float(row["tp1_price"]),
            tp2_price=float(row["tp2_price"]),
            trailing_stop=row["trailing_price"],
            state=row["state"],
        )

    def _persist_trade_state(
        self,
        ctx: TradeContext,
        *,
        new_state: str,
        new_qty: float,
        new_stop: Optional[float],
        new_tp1: Optional[float],
        new_tp2: Optional[float],
        new_trailing: Optional[float],
    ) -> None:
        execute(
            """
            UPDATE trade_state
            SET state = %s,
                qty = %s,
                stop_price = %s,
                tp1_price = %s,
                tp2_price = %s,
                trailing_price = %s,
                last_updated = NOW()
            WHERE symbol = %s
              AND strategy_id = %s
            """,
            (
                new_state,
                new_qty,
                new_stop,
                new_tp1,
                new_tp2,
                new_trailing,
                ctx.symbol,
                ctx.strategy_id,
            ),
        )

    def _log_event(self, ctx: TradeContext, event_type: str, description: str) -> None:
        execute(
            """
            INSERT INTO trade_events (symbol, strategy_id, event_type, description)
            VALUES (%s, %s, %s, %s)
            """,
            (ctx.symbol, ctx.strategy_id, event_type, description),
        )

    # -------------------------
    # API pública
    # -------------------------
    def process_trade_exit(
        self,
        *,
        symbol: str,
        strategy_id: str,
        current_price: float,
        atr: Optional[float] = None,
        atr_multiple_stop: float = 2.0,
    ) -> None:
        """
        Procesa lógica de salidas para una operación concreta.

        - Carga trade_state para (symbol, strategy_id)
        - Recalcula niveles si falta stop (por ejemplo, tras nueva entrada)
        - Evalúa si se dispara STOP / TP1 / TP2 / TRAIL
        - Actualiza trade_state y trade_events

        No modifica directamente posiciones ni journal; eso se maneja
        en la capa de lifecycle.
        """
        ctx = self._load_trade_state(symbol, strategy_id)
        if not ctx:
            return

        # Sólo gestionamos posiciones activas
        if ctx.state not in {"ENTERED", "MANAGED"}:
            return

        # Si todavía no hay stop definido y tenemos ATR, lo calculamos.
        stop_price = ctx.stop_price
        tp1_price = ctx.tp1_price
        tp2_price = ctx.tp2_price
        trailing_price = ctx.trailing_stop

        if stop_price is None or tp1_price is None or tp2_price is None:
            if atr is None:
                # Sin niveles no podemos gestionar exits.
                return
            levels = exits.compute_atr_levels(
                side=ctx.side,
                entry_price=ctx.entry_price,
                atr=atr,
                atr_multiple_stop=atr_multiple_stop,
            )
            stop_price = levels.stop
            tp1_price = levels.tp1
            tp2_price = levels.tp2

        # Determinar si TP1 ya fue tomado: lo veremos por el estado MANAGED
        tp1_already_taken = ctx.state == "MANAGED"

        # Calcular distancia de riesgo (1R) para trailing
        risk_per_unit = abs(ctx.entry_price - stop_price)
        trailing_price = exits.update_trailing_stop(
            side=ctx.side,
            entry_price=ctx.entry_price,
            current_price=current_price,
            risk_per_unit=risk_per_unit,
            existing_trailing_stop=trailing_price,
        )

        levels = exits.ExitLevels(
            stop=stop_price,
            tp1=tp1_price,
            tp2=tp2_price,
            trailing_stop=trailing_price,
        )

        decision = exits.evaluate_exit_decision(
            side=ctx.side,
            levels=levels,
            current_price=current_price,
            tp1_already_taken=tp1_already_taken,
        )

        now_state = ctx.state
        new_qty = ctx.qty

        if decision.action == "NONE":
            # Sólo actualizamos trailing y niveles.
            self._persist_trade_state(
                ctx,
                new_state=now_state,
                new_qty=new_qty,
                new_stop=levels.stop,
                new_tp1=levels.tp1,
                new_tp2=levels.tp2,
                new_trailing=levels.trailing_stop,
            )
            return

        # Acción STOP o TP2 o TRAIL → salida completa
        if decision.action in {"STOP", "TP2_FULL", "TRAIL_STOP"}:
            self._persist_trade_state(
                ctx,
                new_state="EXITED",
                new_qty=0.0,
                new_stop=None,
                new_tp1=None,
                new_tp2=None,
                new_trailing=None,
            )
            self._log_event(
                ctx,
                event_type=decision.action,
                description=f"{decision.reason} price={current_price:.6f}",
            )
            return

        # TP1 parcial → reducimos a la mitad y marcamos estado MANAGED
        if decision.action == "TP1_PARTIAL":
            new_qty = ctx.qty / 2.0
            self._persist_trade_state(
                ctx,
                new_state="MANAGED",
                new_qty=new_qty,
                new_stop=levels.stop,
                new_tp1=levels.tp1,
                new_tp2=levels.tp2,
                new_trailing=levels.trailing_stop,
            )
            self._log_event(
                ctx,
                event_type=decision.action,
                description=f"{decision.reason} price={current_price:.6f}",
            )
            return
