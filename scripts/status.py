"""
Script para mostrar el estado actual del sistema.

Muestra posiciones abiertas, estado de riesgo, equity, etc.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from desk_grade import api
from desk_grade.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("status")


def show_risk_state() -> None:
    """Muestra el estado actual de riesgo."""
    row = api.fetch_one(
        """
        SELECT mode, reason, dd_pct, daily_pnl, weekly_pnl, ts
        FROM risk_state
        ORDER BY ts DESC
        LIMIT 1
        """
    )

    if not row:
        logger.info("Estado de riesgo: NO DISPONIBLE")
        return

    logger.info("=== ESTADO DE RIESGO ===")
    logger.info("Modo: %s", row["mode"])
    logger.info("Razón: %s", row["reason"] or "N/A")
    logger.info("Drawdown: %.2f%%", (row["dd_pct"] or 0.0) * 100)
    logger.info("PnL Diario: %.2f", row["daily_pnl"] or 0.0)
    logger.info("PnL Semanal: %.2f", row["weekly_pnl"] or 0.0)
    logger.info("Última actualización: %s", row["ts"])


def show_positions() -> None:
    """Muestra posiciones abiertas."""
    rows = api.fetch_all(
        """
        SELECT symbol, qty, avg_price, realized_pnl, unrealized_pnl, last_updated
        FROM positions
        WHERE qty != 0
        ORDER BY symbol
        """
    )

    if not rows:
        logger.info("=== POSICIONES ===")
        logger.info("No hay posiciones abiertas")
        return

    logger.info("=== POSICIONES ABIERTAS ===")
    for row in rows:
        logger.info(
            "%s: qty=%.4f avg=%.4f realized=%.2f unrealized=%.2f",
            row["symbol"],
            row["qty"],
            row["avg_price"],
            row["realized_pnl"] or 0.0,
            row["unrealized_pnl"] or 0.0,
        )


def show_equity() -> None:
    """Muestra equity y balances."""
    row = api.fetch_one(
        """
        SELECT currency, balance, available, ts
        FROM cash_balances
        ORDER BY ts DESC
        LIMIT 1
        """
    )

    if not row:
        logger.info("Equity: NO DISPONIBLE")
        return

    logger.info("=== EQUITY ===")
    logger.info("Moneda: %s", row["currency"])
    logger.info("Balance: %.2f", row["balance"])
    logger.info("Disponible: %.2f", row["available"])
    logger.info("Última actualización: %s", row["ts"])


def show_open_trades() -> None:
    """Muestra trades abiertos."""
    rows = api.fetch_all(
        """
        SELECT symbol, strategy_id, state, qty, entry_price, stop_price, tp1_price, tp2_price
        FROM trade_state
        WHERE state IN ('ENTERED', 'MANAGED')
        ORDER BY symbol
        """
    )

    if not rows:
        logger.info("=== TRADES ABIERTOS ===")
        logger.info("No hay trades abiertos")
        return

    logger.info("=== TRADES ABIERTOS ===")
    for row in rows:
        logger.info(
            "%s (%s): estado=%s qty=%.4f entry=%.4f stop=%.4f tp1=%.4f tp2=%.4f",
            row["symbol"],
            row["strategy_id"],
            row["state"],
            row["qty"] or 0.0,
            row["entry_price"] or 0.0,
            row["stop_price"] or 0.0,
            row["tp1_price"] or 0.0,
            row["tp2_price"] or 0.0,
        )


def main() -> None:
    """Función principal."""
    logger.info("=== ESTADO DEL SISTEMA ===")
    logger.info("Timestamp: %s", datetime.now(timezone.utc))

    show_equity()
    show_risk_state()
    show_positions()
    show_open_trades()

    logger.info("=== FIN DEL REPORTE ===")


if __name__ == "__main__":
    main()
