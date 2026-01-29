"""
Seed de demo para `trade_journal` y métricas de trades.

Este script inserta algunas operaciones simuladas en la tabla `trade_journal`
para que el dashboard de **Métricas de Trades** (R-múltiples, win rate, MAE/MFE)
muestre datos inmediatamente.

Uso:

    python -m scripts.seed_trade_metrics_demo

Solo debes ejecutarlo en entornos de desarrollo / demo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from desk_grade import api


def seed_demo_trades() -> None:
    now = datetime.now(timezone.utc)

    demo_rows = [
        # symbol, strategy_id, entry_ts, exit_ts, entry_price, exit_price, qty, r, pnl_r, mae, mfe
        ("AAPL", "baseline", now - timedelta(days=5), now - timedelta(days=4, hours=20), 180.0, 186.0, 10.0, 1.2, 600.0, -0.5, 2.0),
        ("AAPL", "baseline", now - timedelta(days=4), now - timedelta(days=3, hours=18), 185.0, 181.0, 8.0, -0.8, -320.0, -1.2, 0.6),
        ("TSLA", "baseline", now - timedelta(days=3), now - timedelta(days=2, hours=22), 240.0, 252.0, 5.0, 1.5, 600.0, -0.4, 2.3),
        ("EURUSD", "baseline", now - timedelta(days=2), now - timedelta(days=1, hours=21), 1.0800, 1.0760, 10000.0, -0.5, -400.0, -0.8, 0.7),
        ("GBPUSD", "baseline", now - timedelta(days=1), now - timedelta(hours=10), 1.2600, 1.2720, 8000.0, 1.1, 880.0, -0.3, 1.9),
    ]

    for row in demo_rows:
        symbol, strategy_id, entry_ts, exit_ts, entry_price, exit_price, qty, r, pnl_r, mae, mfe = row
        api.execute(
            """
            INSERT INTO trade_journal (
                symbol, strategy_id, entry_ts, exit_ts,
                entry_price, exit_price, qty, r, pnl_r, mae, mfe
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                symbol,
                strategy_id,
                entry_ts,
                exit_ts,
                entry_price,
                exit_price,
                qty,
                r,
                pnl_r,
                mae,
                mfe,
            ),
        )


def main() -> None:
    seed_demo_trades()
    print("Trades de demo insertados en trade_journal.")


if __name__ == "__main__":
    main()

