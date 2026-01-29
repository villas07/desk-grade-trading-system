"""Configuración de logging centralizada."""

import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Configura el logging del sistema.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR). Si es None, se lee de LOG_LEVEL.
        format_string: Formato personalizado. Si es None, usa un formato por defecto.
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    if format_string is None:
        format_string = "%(asctime)s [%(levelname)8s] %(name)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=format_string,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
