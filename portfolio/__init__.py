"""
Portfolio Management Module

Módulos principales:
- risk_layer: gestión de riesgo y gates
- lifecycle_engine: ciclo de vida de trades
- exit_engine: motor de salidas
- metrics: métricas básicas (R, MAE, MFE)
- advanced_metrics: métricas avanzadas (Sharpe, drawdown, expectancy)
"""

from . import (
    advanced_metrics,
    exit_engine,
    exits,
    lifecycle_engine,
    metrics,
    order_builder,
    risk_layer,
)

__all__ = [
    "advanced_metrics",
    "exit_engine",
    "exits",
    "lifecycle_engine",
    "metrics",
    "order_builder",
    "risk_layer",
]
