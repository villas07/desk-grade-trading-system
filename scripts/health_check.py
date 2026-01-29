"""
Script de health check del sistema.

Verifica conectividad con la base de datos y estado de componentes clave.
"""

from __future__ import annotations

import logging
import sys

from desk_grade import api
from desk_grade.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("health_check")


def check_database() -> bool:
    """Verifica conectividad con la base de datos."""
    try:
        result = api.fetch_one("SELECT 1 AS test")
        if result and result["test"] == 1:
            logger.info("✓ Base de datos: OK")
            return True
        logger.error("✗ Base de datos: respuesta inesperada")
        return False
    except Exception as exc:
        logger.error("✗ Base de datos: ERROR - %s", exc)
        return False


def check_tables() -> bool:
    """Verifica que las tablas principales existan."""
    required_tables = [
        "trade_state",
        "trade_events",
        "trade_journal",
        "positions",
        "risk_state",
        "ohlcv",
        "signals_live",
    ]

    all_ok = True
    for table in required_tables:
        try:
            result = api.fetch_one(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
                """,
                (table,),
            )
            if result and result["exists"]:
                logger.info("  ✓ Tabla '%s': OK", table)
            else:
                logger.error("  ✗ Tabla '%s': NO EXISTE", table)
                all_ok = False
        except Exception as exc:
            logger.error("  ✗ Tabla '%s': ERROR - %s", table, exc)
            all_ok = False

    return all_ok


def check_data() -> bool:
    """Verifica que haya datos mínimos en el sistema."""
    checks = []

    # Cash balance
    try:
        cash = api.fetch_one("SELECT COUNT(*) AS cnt FROM cash_balances")
        if cash and cash["cnt"] > 0:
            logger.info("  ✓ Cash balances: %d registros", cash["cnt"])
            checks.append(True)
        else:
            logger.warning("  ⚠ Cash balances: vacío (se necesita balance inicial)")
            checks.append(False)
    except Exception as exc:
        logger.error("  ✗ Cash balances: ERROR - %s", exc)
        checks.append(False)

    # OHLCV data
    try:
        ohlcv = api.fetch_one("SELECT COUNT(*) AS cnt FROM ohlcv")
        if ohlcv and ohlcv["cnt"] > 0:
            logger.info("  ✓ OHLCV: %d registros", ohlcv["cnt"])
            checks.append(True)
        else:
            logger.warning("  ⚠ OHLCV: vacío (se necesitan datos de mercado)")
            checks.append(False)
    except Exception as exc:
        logger.error("  ✗ OHLCV: ERROR - %s", exc)
        checks.append(False)

    return all(checks)


def main() -> None:
    """Función principal del health check."""
    logger.info("=== HEALTH CHECK ===")

    db_ok = check_database()
    if not db_ok:
        logger.error("Health check FALLIDO: no hay conexión a la base de datos")
        sys.exit(1)

    tables_ok = check_tables()
    if not tables_ok:
        logger.error("Health check FALLIDO: faltan tablas requeridas")
        sys.exit(1)

    data_ok = check_data()
    if not data_ok:
        logger.warning("Health check PARCIAL: faltan datos (ejecuta seed_data.py)")

    logger.info("=== HEALTH CHECK COMPLETADO ===")
    sys.exit(0 if (db_ok and tables_ok) else 1)


if __name__ == "__main__":
    main()
