"""
Script para resetear completamente la base de datos.

ADVERTENCIA: Esto elimina TODOS los datos.
"""

from __future__ import annotations

import logging

from desk_grade import api
from desk_grade.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("reset_db")


def drop_all_tables() -> None:
    """Elimina todas las tablas del esquema public."""
    logger.warning("=== RESETEO DE BASE DE DATOS ===")
    logger.warning("ADVERTENCIA: Esto eliminará TODOS los datos")

    # Obtener todas las tablas
    tables = api.fetch_all(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """
    )

    if not tables:
        logger.info("No hay tablas para eliminar")
        return

    logger.info("Eliminando %d tablas...", len(tables))

    # Eliminar tablas en orden inverso (por si hay dependencias)
    for table in reversed(tables):
        table_name = table["tablename"]
        try:
            api.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            logger.info("  ✓ Eliminada: %s", table_name)
        except Exception as exc:
            logger.warning("  ✗ Error eliminando %s: %s", table_name, exc)

    # Eliminar tipos enum si existen
    enums = api.fetch_all(
        """
        SELECT typname
        FROM pg_type
        WHERE typtype = 'e'
        AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        """
    )

    for enum in enums:
        enum_name = enum["typname"]
        try:
            api.execute(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE')
            logger.info("  ✓ Eliminado tipo: %s", enum_name)
        except Exception as exc:
            logger.warning("  ✗ Error eliminando tipo %s: %s", enum_name, exc)

    logger.info("Base de datos reseteada. Ejecuta init_db.py para recrear el esquema.")


def main() -> None:
    """Función principal."""
    import sys

    response = input("¿Estás seguro de que quieres eliminar TODOS los datos? (escribe 'SI' para confirmar): ")
    if response != "SI":
        logger.info("Operación cancelada")
        sys.exit(0)

    try:
        drop_all_tables()
        logger.info("=== RESETEO COMPLETADO ===")
    except Exception as exc:
        logger.error("Error reseteando base de datos: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
