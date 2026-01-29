"""
Tests básicos para el módulo de métricas.
"""

import pytest

from portfolio import metrics


def test_r_multiple_long() -> None:
    """Test cálculo de R múltiple para posición LONG."""
    # Entry: 100, Stop: 95, Exit: 105
    # R = (105 - 100) / (100 - 95) = 5 / 5 = 1.0
    r = metrics.r_multiple("BUY", entry_price=100.0, stop_price=95.0, exit_price=105.0)
    assert r == pytest.approx(1.0)


def test_r_multiple_short() -> None:
    """Test cálculo de R múltiple para posición SHORT."""
    # Entry: 100, Stop: 105, Exit: 95
    # R = (100 - 95) / (105 - 100) = 5 / 5 = 1.0
    r = metrics.r_multiple("SELL", entry_price=100.0, stop_price=105.0, exit_price=95.0)
    assert r == pytest.approx(1.0)


def test_realized_pnl_long() -> None:
    """Test PnL realizado para posición LONG."""
    # Entry: 100, Exit: 105, Qty: 10
    # PnL = (105 - 100) * 10 = 50
    pnl = metrics.realized_pnl("BUY", entry_price=100.0, exit_price=105.0, qty=10.0)
    assert pnl == pytest.approx(50.0)


def test_realized_pnl_short() -> None:
    """Test PnL realizado para posición SHORT."""
    # Entry: 100, Exit: 95, Qty: 10
    # PnL = (100 - 95) * 10 = 50
    pnl = metrics.realized_pnl("SELL", entry_price=100.0, exit_price=95.0, qty=10.0)
    assert pnl == pytest.approx(50.0)


def test_mae_mfe_r() -> None:
    """Test cálculo de MAE y MFE en unidades R."""
    # Entry: 100, Stop: 95, Price path: [98, 102, 99, 103]
    # R = 5 (100 - 95)
    # Movimientos: -2, +2, -1, +3
    # En R: -0.4, +0.4, -0.2, +0.6
    # MAE = -0.4, MFE = +0.6
    mae, mfe = metrics.mae_mfe_r(
        side="BUY",
        entry_price=100.0,
        stop_price=95.0,
        price_path=[98.0, 102.0, 99.0, 103.0],
    )
    assert mae == pytest.approx(-0.4)
    assert mfe == pytest.approx(0.6)
