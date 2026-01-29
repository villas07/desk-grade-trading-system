"""
Script para inicializar la base de datos manualmente.

Ejecuta el script init.sql si las tablas no existen.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from desk_grade import api
from desk_grade.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("init_db")


def check_table_exists(table_name: str) -> bool:
    """Verifica si una tabla existe."""
    try:
        result = api.fetch_one(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
            """,
            (table_name,),
        )
        return result and result["exists"]
    except Exception as exc:
        logger.error("Error verificando tabla %s: %s", table_name, exc)
        return False


def init_database() -> None:
    """Ejecuta el script init.sql si las tablas no existen."""
    logger.info("=== INICIALIZACIÓN DE BASE DE DATOS ===")

    # Verificar si las tablas principales existen
    key_tables = ["cash_balances", "trade_state", "ohlcv", "positions"]
    missing_tables = [t for t in key_tables if not check_table_exists(t)]

    if not missing_tables:
        logger.info("✓ Todas las tablas principales existen. Base de datos ya inicializada.")
        return

    logger.info("Faltan tablas: %s", missing_tables)
    logger.info("Ejecutando init.sql...")

    # Leer el archivo init.sql
    script_path = Path(__file__).parent.parent / "infra" / "init.sql"
    if not script_path.exists():
        logger.error("✗ No se encontró init.sql en %s", script_path)
        raise FileNotFoundError(f"init.sql no encontrado en {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Ejecutar el script completo usando psycopg directamente
    # Necesitamos usar una conexión directa para ejecutar múltiples statements
    from desk_grade.db import db_session

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Ejecutar el script completo
                cur.execute(sql_script)
                conn.commit()
                logger.info("✓ Script init.sql ejecutado correctamente")
    except Exception as exc:
        # Algunos errores son esperados (tablas que ya existen, etc.)
        error_str = str(exc).lower()
        if "already exists" in error_str or "duplicate" in error_str:
            logger.info("Algunos objetos ya existen (normal si se ejecuta múltiples veces)")
        else:
            logger.warning("Error ejecutando init.sql: %s", exc)
            # Intentar ejecutar statement por statement como fallback
            logger.info("Intentando ejecutar statement por statement...")
            _execute_statements_fallback(sql_script)

    # Verificar nuevamente
    still_missing = [t for t in key_tables if not check_table_exists(t)]
    if still_missing:
        logger.error("✗ Aún faltan tablas después de ejecutar init.sql: %s", still_missing)
        logger.error("Intenta ejecutar init.sql manualmente desde psql")
        raise RuntimeError(f"No se pudieron crear todas las tablas: {still_missing}")

    logger.info("✓ Base de datos inicializada correctamente")


def _execute_statements_fallback(sql_script: str) -> None:
    """Fallback: ejecuta statements uno por uno."""
    from desk_grade.db import db_session

    # Dividir en statements (simple, no perfecto pero funciona para la mayoría)
    statements = []
    current = ""
    for line in sql_script.split("\n"):
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        current += line + " "
        if line.endswith(";"):
            statements.append(current.strip())
            current = ""

    executed = 0
    with db_session() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                if not statement or len(statement) < 5:
                    continue
                try:
                    cur.execute(statement)
                    executed += 1
                except Exception as exc:
                    error_str = str(exc).lower()
                    if "already exists" in error_str or "duplicate" in error_str:
                        logger.debug("Ya existe: %s", statement[:50])
                    else:
                        logger.warning("Error en statement: %s", str(exc)[:100])
            conn.commit()
    logger.info("Ejecutados %d statements", executed)


def main() -> None:
    """Función principal."""
    try:
        init_database()
        logger.info("=== INICIALIZACIÓN COMPLETADA ===")
    except Exception as exc:
        logger.error("Error inicializando base de datos: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
