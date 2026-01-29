"""
Scheduler básico para ejecutar ciclos de riesgo periódicamente.

Este scheduler es simple y está diseñado para ser reemplazado por Colibrí
en producción. Ejecuta el ciclo de riesgo cada N minutos.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from desk_grade.logging_config import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger("scheduler")


def run_risk_cycle() -> None:
    """Importa y ejecuta el ciclo de riesgo."""
    from scripts.run_risk_cycle import run_cycle

    run_cycle()


def scheduler_loop(interval_minutes: int = 5) -> None:
    """
    Ejecuta el ciclo de riesgo cada N minutos de forma continua.

    Args:
        interval_minutes: Intervalo en minutos entre ejecuciones
    """
    interval_seconds = interval_minutes * 60
    logger.info(
        "Scheduler iniciado: ejecutando ciclo de riesgo cada %d minutos",
        interval_minutes,
    )

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            logger.info("=== CICLO #%d INICIADO ===", cycle_count)

            try:
                run_risk_cycle()
                logger.info("=== CICLO #%d COMPLETADO ===", cycle_count)
            except Exception as exc:
                logger.error("Error en ciclo #%d: %s", cycle_count, exc, exc_info=True)

            # Esperar hasta el siguiente ciclo
            logger.info("Esperando %d segundos hasta el siguiente ciclo...", interval_seconds)
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        logger.info("Scheduler detenido por el usuario")
    except Exception as exc:
        logger.error("Error fatal en scheduler: %s", exc, exc_info=True)
        raise


def main() -> None:
    """Función principal del scheduler."""
    interval = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "5"))
    scheduler_loop(interval_minutes=interval)


if __name__ == "__main__":
    main()
