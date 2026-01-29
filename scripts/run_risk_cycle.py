from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from desk_grade import api
from portfolio.exit_engine import ExitEngine
from portfolio.lifecycle_engine import LifecycleEngine
from portfolio.order_builder import OrderIntent, build_order_intent
from portfolio.risk_layer import ExposureSnapshot, RiskEngine


load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_risk_cycle")


PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
STRATEGY_ID = os.getenv("STRATEGY_ID", "baseline")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_open_trades() -> List[Dict]:
    """Obtiene operaciones en estado ENTERED o MANAGED."""
    return api.fetch_all(
        """
        SELECT *
        FROM public.trade_state
        WHERE state IN ('ENTERED', 'MANAGED')
        """
    )


def _fetch_latest_price(symbol: str) -> Optional[float]:
    row = api.fetch_one(
        """
        SELECT close
        FROM ohlcv
        WHERE symbol = %s
        ORDER BY ts DESC
        LIMIT 1
        """,
        (symbol,),
    )
    return float(row["close"]) if row else None


def _fetch_atr(symbol: str) -> Optional[float]:
    row = api.fetch_one(
        """
        SELECT atr
        FROM atr_cache
        WHERE symbol = %s
        ORDER BY ts DESC
        LIMIT 1
        """,
        (symbol,),
    )
    return float(row["atr"]) if row else None


def _compute_equity_and_pnl() -> Tuple[float, float, float]:
    """
    Calcula equity actual y PnL diario/semanal aproximados en modo PAPER.

    - equity: último balance disponible en cash_balances.
    - daily_pnl / weekly_pnl: aproximados mediante diferencias de balance.
    """
    latest_cash = api.fetch_one(
        """
        SELECT ts, balance
        FROM cash_balances
        ORDER BY ts DESC
        LIMIT 1
        """
    )
    if not latest_cash:
        return 0.0, 0.0, 0.0

    equity = float(latest_cash["balance"])
    latest_ts = latest_cash["ts"]

    # Daily PnL
    day_ago = latest_ts - timedelta(days=1)
    day_ref = api.fetch_one(
        """
        SELECT balance
        FROM cash_balances
        WHERE ts <= %s
        ORDER BY ts DESC
        LIMIT 1
        """,
        (day_ago,),
    )
    daily_pnl = equity - float(day_ref["balance"]) if day_ref else 0.0

    # Weekly PnL
    week_ago = latest_ts - timedelta(days=7)
    week_ref = api.fetch_one(
        """
        SELECT balance
        FROM cash_balances
        WHERE ts <= %s
        ORDER BY ts DESC
        LIMIT 1
        """,
        (week_ago,),
    )
    weekly_pnl = equity - float(week_ref["balance"]) if week_ref else 0.0

    return equity, daily_pnl, weekly_pnl


def _fetch_sector_exposure_pct() -> Dict[str, float]:
    """
    Agrega exposure_snapshots recientes por sector para aproximar exposición sectorial.
    """
    rows = api.fetch_all(
        """
        SELECT sector, SUM(net_exposure) AS net_exp
        FROM exposure_snapshots
        WHERE ts >= NOW() - INTERVAL '1 day'
        GROUP BY sector
        """
    )
    # Normalizamos por equity actual para obtener porcentaje aproximado
    equity, _, _ = _compute_equity_and_pnl()
    if equity <= 0:
        return {}

    result: Dict[str, float] = {}
    for r in rows:
        sector = r["sector"] or "UNKNOWN"
        pct = float(r["net_exp"] or 0.0) / equity
        result[sector] = pct
    return result


def _risk_gates_step(risk_engine: RiskEngine) -> str:
    """Evalúa gates de riesgo y persiste risk_state / risk_events."""
    equity, daily_pnl, weekly_pnl = _compute_equity_and_pnl()
    # Aproximaciones simples de flags
    correlation_flag = False
    reconciliation_flag = False

    sector_exposure_pct = _fetch_sector_exposure_pct()

    # Peak equity aproximado como máximo histórico en cash_balances
    peak_row = api.fetch_one(
        """
        SELECT MAX(balance) AS peak
        FROM cash_balances
        """
    )
    peak_equity = float(peak_row["peak"] or 0.0) if peak_row else equity

    result = risk_engine.evaluate_gates(
        equity=equity,
        peak_equity=peak_equity,
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
        sector_exposure_pct=sector_exposure_pct,
        correlation_flag=correlation_flag,
        reconciliation_flag=reconciliation_flag,
    )

    api.execute(
        """
        INSERT INTO risk_state (
            mode, reason, dd_pct, daily_pnl, weekly_pnl,
            correlation_flag, reconciliation_flag
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            result.mode,
            ";".join(result.reasons),
            (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0,
            daily_pnl,
            weekly_pnl,
            correlation_flag,
            reconciliation_flag,
        ),
    )

    api.execute(
        """
        INSERT INTO risk_events (event_type, severity, description)
        VALUES (%s, %s, %s)
        """,
        (
            "RISK_GATES_EVALUATED",
            "INFO" if result.mode == "NORMAL" else "WARN",
            f"mode={result.mode} reasons={','.join(result.reasons)}",
        ),
    )

    logger.info("Risk mode=%s reasons=%s", result.mode, result.reasons)
    return result.mode


def _fetch_latest_signals() -> List[Dict]:
    """
    Recupera señales vivas más recientes para cada símbolo.
    """
    rows = api.fetch_all(
        """
        SELECT s.*
        FROM signals_live s
        JOIN (
            SELECT symbol, MAX(ts) AS max_ts
            FROM signals_live
            GROUP BY symbol
        ) t
          ON s.symbol = t.symbol
         AND s.ts = t.max_ts
        """
    )
    return rows


def _fetch_current_position(symbol: str) -> float:
    row = api.fetch_one(
        """
        SELECT qty
        FROM positions
        WHERE symbol = %s
          AND strategy_id = %s
        """,
        (symbol, STRATEGY_ID),
    )
    return float(row["qty"]) if row else 0.0


def _persist_paper_fill(intent: OrderIntent) -> None:
    """
    En modo PAPER, consideramos que las órdenes se ejecutan instantáneamente
    al precio de mercado y actualizamos orders, fills y positions.
    """
    if not PAPER_TRADING:
        return

    # Insert order
    api.execute(
        """
        INSERT INTO orders (symbol, side, qty, price, order_type, status, strategy_id, paper_trade)
        VALUES (%s, %s, %s, %s, 'MARKET', 'FILLED', %s, TRUE)
        """,
        (
            intent.symbol,
            intent.side,
            intent.qty,
            intent.price,
            intent.strategy_id,
        ),
    )

    # Update or insert position
    current_row = api.fetch_one(
        """
        SELECT qty, avg_price, realized_pnl
        FROM positions
        WHERE symbol = %s
          AND strategy_id = %s
        """,
        (intent.symbol, intent.strategy_id),
    )

    qty_delta = intent.qty if intent.side == "BUY" else -intent.qty

    if not current_row:
        new_qty = qty_delta
        new_avg_price = intent.price
        realized_pnl = 0.0
        api.execute(
            """
            INSERT INTO positions (symbol, qty, avg_price, realized_pnl, strategy_id, last_updated)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (
                intent.symbol,
                new_qty,
                new_avg_price,
                realized_pnl,
                intent.strategy_id,
            ),
        )
    else:
        old_qty = float(current_row["qty"])
        old_avg = float(current_row["avg_price"])
        realized_pnl = float(current_row["realized_pnl"])

        new_qty = old_qty + qty_delta
        if (old_qty >= 0 and qty_delta >= 0) or (old_qty <= 0 and qty_delta <= 0):
            # Mismo signo: ajustamos precio medio
            total_notional = old_qty * old_avg + qty_delta * intent.price
            if new_qty != 0:
                new_avg_price = total_notional / new_qty
            else:
                new_avg_price = 0.0
        else:
            # Cierre parcial o total: calculamos PnL
            closing_qty = min(abs(old_qty), abs(qty_delta))
            if old_qty > 0:  # cerrando long
                pnl = (intent.price - old_avg) * closing_qty
            else:  # cerrando short
                pnl = (old_avg - intent.price) * closing_qty
            realized_pnl += pnl
            new_avg_price = old_avg if new_qty != 0 else 0.0

        api.execute(
            """
            UPDATE positions
            SET qty = %s,
                avg_price = %s,
                realized_pnl = %s,
                last_updated = NOW()
            WHERE symbol = %s
              AND strategy_id = %s
            """,
            (
                new_qty,
                new_avg_price,
                realized_pnl,
                intent.symbol,
                intent.strategy_id,
            ),
        )


def _entries_step(risk_engine: RiskEngine) -> None:
    """
    Genera entradas en modo PAPER, respetando gates de riesgo
    y cooldown de lifecycle.
    """
    lifecycle = LifecycleEngine()

    risk_mode_row = api.fetch_one(
        """
        SELECT mode
        FROM risk_state
        ORDER BY ts DESC
        LIMIT 1
        """
    )
    risk_mode = risk_mode_row["mode"] if risk_mode_row else "NORMAL"

    if risk_mode != "NORMAL":
        logger.info("Risk mode %s: sólo reducción, sin nuevas entradas", risk_mode)
        return

    equity, _, _ = _compute_equity_and_pnl()
    if equity <= 0:
        logger.warning("Equity no disponible, se omiten nuevas entradas")
        return

    signals = _fetch_latest_signals()

    for sig in signals:
        symbol = sig["symbol"]
        side = sig["side"].upper()

        if lifecycle.is_in_cooldown(symbol, STRATEGY_ID):
            logger.info("Symbol %s en cooldown, se salta entrada", symbol)
            continue

        price = _fetch_latest_price(symbol)
        if price is None or price <= 0:
            continue

        atr = _fetch_atr(symbol)
        base_size = risk_engine.compute_position_size(
            symbol=symbol,
            price=price,
            equity=equity,
            atr=atr,
        )
        # Para simplicidad, ignoramos vol específica del activo (no tenemos aquí)
        final_size = risk_engine.apply_vol_targeting(
            base_size=base_size,
            asset_annual_vol=None,
        )
        if final_size <= 0:
            continue

        target_qty = final_size if side == "BUY" else -final_size
        current_qty = _fetch_current_position(symbol)

        intent = build_order_intent(
            symbol=symbol,
            target_qty=target_qty,
            current_qty=current_qty,
            price=price,
            strategy_id=STRATEGY_ID,
            reason="RISK_CYCLE_ENTRY",
        )
        if not intent:
            continue

        logger.info(
            "Nueva entrada %s %s qty=%.4f price=%.4f",
            intent.side,
            intent.symbol,
            intent.qty,
            intent.price,
        )

        _persist_paper_fill(intent)

        # Registrar entrada en trade_state/lifecycle
        atr_for_levels = atr or (price * 0.01)
        from portfolio.exits import compute_atr_levels

        levels = compute_atr_levels(
            side=intent.side,
            entry_price=price,
            atr=atr_for_levels,
            atr_multiple_stop=2.0,
        )
        lifecycle.register_entry(
            symbol=intent.symbol,
            strategy_id=intent.strategy_id,
            qty=target_qty,
            entry_price=price,
            stop_price=levels.stop,
            tp1_price=levels.tp1,
            tp2_price=levels.tp2,
        )


def run_cycle() -> None:
    """
    Ejecuta un ciclo completo intradía en modo PAPER con el siguiente orden:
      1) Exits
      2) Journal
      3) Risk
      4) Entries
      5) Persistencia (implícita vía DB)
    """
    logger.info("=== RISK CYCLE START ===")

    risk_engine = RiskEngine()
    exit_engine = ExitEngine()
    lifecycle = LifecycleEngine()

    # 1) Exits
    open_trades = _fetch_open_trades()
    for t in open_trades:
        symbol = t["symbol"]
        strategy_id = t["strategy_id"]
        price = _fetch_latest_price(symbol)
        if price is None:
            continue
        atr = _fetch_atr(symbol)
        exit_engine.process_trade_exit(
            symbol=symbol,
            strategy_id=strategy_id,
            current_price=price,
            atr=atr,
        )

    # 2) Journal (MAE/MFE, R, pnl_r y lifecycle EXITED + cooldown)
    lifecycle.process_exited_trades()

    # 3) Risk gates y risk_state / risk_events
    _risk_gates_step(risk_engine)

    # 4) Entries (BUY/SELL) en modo PAPER
    _entries_step(risk_engine)

    # 5) Persistencia: todas las operaciones se realizan contra DB en cada paso
    logger.info("=== RISK CYCLE END ===")


if __name__ == "__main__":
    run_cycle()
