"""
Script para poblar datos iniciales en la base de datos.

Útil para desarrollo y pruebas.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from desk_grade import api
from desk_grade.logging_config import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger("seed_data")


def seed_ohlcv(symbol: str, days: int = 30, timeframe: str = "1m") -> None:
    """
    Genera datos OHLCV sintéticos para un símbolo.

    Args:
        symbol: Símbolo del activo (ej: "EURUSD", "AAPL")
        days: Número de días de datos históricos a generar
        timeframe: Timeframe de las velas (por defecto "1m")
    """
    logger.info("Generando OHLCV para %s (%d días, %s)", symbol, days, timeframe)

    now = datetime.now(timezone.utc)
    start_ts = now - timedelta(days=days)

    # Precio base sintético
    base_price = 100.0 if "USD" not in symbol else 1.0

    current_ts = start_ts
    current_price = base_price
    count = 0

    while current_ts < now:
        # Movimiento aleatorio simple (random walk)
        import random

        change_pct = random.uniform(-0.001, 0.001)  # ±0.1% por minuto
        current_price *= 1 + change_pct

        high = current_price * 1.0005
        low = current_price * 0.9995
        open_price = current_price * 0.9998
        close_price = current_price

        api.execute(
            """
            INSERT INTO ohlcv (symbol, ts, open, high, low, close, volume, timeframe)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                symbol,
                current_ts,
                open_price,
                high,
                low,
                close_price,
                random.uniform(1000, 10000),
                timeframe,
            ),
        )

        current_ts += timedelta(minutes=1)
        count += 1

        if count % 1000 == 0:
            logger.debug("Insertadas %d velas hasta %s", count, current_ts)

    logger.info("OHLCV generado: %d velas para %s", count, symbol)


def seed_signals(symbol: str, side: str = "BUY", strength: float = 0.7) -> None:
    """
    Inserta una señal de trading en signals_live.

    Args:
        symbol: Símbolo del activo
        side: Dirección de la señal ("BUY" o "SELL")
        strength: Fuerza de la señal (0.0 a 1.0)
    """
    strategy_id = os.getenv("STRATEGY_ID", "baseline")

    api.execute(
        """
        INSERT INTO signals_live (symbol, ts, side, strength, strategy_id)
        VALUES (%s, NOW(), %s, %s, %s)
        """,
        (symbol, side, strength, strategy_id),
    )

    logger.info("Señal insertada: %s %s strength=%.2f", symbol, side, strength)


def seed_cash_balance(currency: str = "USD", balance: float = 10000.0) -> None:
    """
    Inserta o actualiza un balance de efectivo.

    Args:
        currency: Moneda (por defecto "USD")
        balance: Balance inicial
    """
    api.execute(
        """
        INSERT INTO cash_balances (currency, balance, available)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (currency, balance, balance),
    )

    logger.info("Balance inicial: %s %.2f", currency, balance)


def seed_atr_cache(symbol: str, atr: float = 0.5) -> None:
    """
    Inserta un valor de ATR en el cache.

    Args:
        symbol: Símbolo del activo
        atr: Valor de ATR
    """
    api.execute(
        """
        INSERT INTO atr_cache (symbol, timeframe, ts, atr)
        VALUES (%s, '1m', NOW(), %s)
        ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET atr = EXCLUDED.atr
        """,
        (symbol, atr),
    )

    logger.info("ATR cache actualizado: %s = %.4f", symbol, atr)


def main() -> None:
    """Función principal: pobla datos de ejemplo."""
    logger.info("=== SEED DATA START ===")

    # Símbolos de ejemplo
    symbols = ["EURUSD", "GBPUSD", "AAPL", "TSLA"]

    # 1. Balance inicial
    seed_cash_balance()

    # 2. OHLCV para cada símbolo
    for symbol in symbols:
        seed_ohlcv(symbol, days=7)  # 7 días de datos
        seed_atr_cache(symbol, atr=0.5)

    # 3. Señales de ejemplo
    seed_signals("EURUSD", side="BUY", strength=0.8)
    seed_signals("AAPL", side="BUY", strength=0.6)

    logger.info("=== SEED DATA END ===")


if __name__ == "__main__":
    main()
