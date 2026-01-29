"""Configuración centralizada del sistema."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_config() -> dict:
    """Devuelve configuración cacheada desde variables de entorno."""
    return {
        "db": {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "desk"),
            "user": os.getenv("DB_USER", "desk"),
            "password": os.getenv("DB_PASSWORD", "desk_pass"),
        },
        "risk": {
            "max_drawdown_pct": float(os.getenv("RISK_MAX_DRAWDOWN_PCT", "0.2")),
            "daily_loss_limit_pct": float(os.getenv("RISK_DAILY_LOSS_PCT", "0.05")),
            "weekly_loss_limit_pct": float(os.getenv("RISK_WEEKLY_LOSS_PCT", "0.10")),
            "vol_target": float(os.getenv("RISK_VOL_TARGET", "0.0")) or None,
            "sector_cap_pct": float(os.getenv("RISK_SECTOR_CAP_PCT", "0.0")) or None,
            "position_sizing_mode": os.getenv("RISK_POSITION_SIZING_MODE", "FIXED_FRACTIONAL").upper(),
            "fixed_fractional": float(os.getenv("RISK_FIXED_FRACTIONAL", "0.01")),
            "atr_multiplier": float(os.getenv("RISK_ATR_MULTIPLIER", "2.0")),
        },
        "trading": {
            "paper_trading": os.getenv("PAPER_TRADING", "true").lower() == "true",
            "strategy_id": os.getenv("STRATEGY_ID", "baseline"),
        },
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO").upper(),
        },
    }
