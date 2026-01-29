"""
Tests básicos para el módulo de riesgo.
"""

import pytest

from portfolio.risk_layer import RiskEngine, RiskLimits


def test_risk_gates_normal() -> None:
    """Test gates de riesgo en modo NORMAL."""
    limits = RiskLimits(
        max_drawdown_pct=0.2,
        daily_loss_limit_pct=0.05,
        weekly_loss_limit_pct=0.1,
        vol_target=None,
        sector_cap_pct=None,
        sizing_mode="FIXED_FRACTIONAL",
        fixed_fractional=0.01,
        atr_multiplier=2.0,
    )

    engine = RiskEngine(limits=limits)

    result = engine.evaluate_gates(
        equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
    )

    assert result.mode == "NORMAL"
    assert "RISK_OK" in result.reasons


def test_risk_gates_halt_drawdown() -> None:
    """Test gates de riesgo que activan HALT por drawdown."""
    limits = RiskLimits(
        max_drawdown_pct=0.2,
        daily_loss_limit_pct=0.05,
        weekly_loss_limit_pct=0.1,
        vol_target=None,
        sector_cap_pct=None,
        sizing_mode="FIXED_FRACTIONAL",
        fixed_fractional=0.01,
        atr_multiplier=2.0,
    )

    engine = RiskEngine(limits=limits)

    # Drawdown del 25% (> 20%)
    result = engine.evaluate_gates(
        equity=7500.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
    )

    assert result.mode == "HALT"
    assert any("MAX_DRAWDOWN" in r for r in result.reasons)


def test_position_sizing_fixed_fractional() -> None:
    """Test position sizing con fixed fractional."""
    limits = RiskLimits(
        max_drawdown_pct=0.2,
        daily_loss_limit_pct=0.05,
        weekly_loss_limit_pct=0.1,
        vol_target=None,
        sector_cap_pct=None,
        sizing_mode="FIXED_FRACTIONAL",
        fixed_fractional=0.01,  # 1% del equity
        atr_multiplier=2.0,
    )

    engine = RiskEngine(limits=limits)

    # Equity: 10000, Price: 100, Fixed fractional: 1%
    # Risk dollars: 10000 * 0.01 = 100
    # Size: 100 / 100 = 1 unidad
    size = engine.compute_position_size(symbol="TEST", price=100.0, equity=10000.0)
    assert size == pytest.approx(1.0)


def test_position_sizing_atr() -> None:
    """Test position sizing con ATR."""
    limits = RiskLimits(
        max_drawdown_pct=0.2,
        daily_loss_limit_pct=0.05,
        weekly_loss_limit_pct=0.1,
        vol_target=None,
        sector_cap_pct=None,
        sizing_mode="ATR",
        fixed_fractional=0.01,
        atr_multiplier=2.0,
    )

    engine = RiskEngine(limits=limits)

    # Equity: 10000, Price: 100, ATR: 2, Multiplier: 2
    # Risk per unit: 2 * 2 = 4
    # Risk dollars: 10000 * 0.01 = 100
    # Size: 100 / 4 = 25 unidades
    size = engine.compute_position_size(symbol="TEST", price=100.0, equity=10000.0, atr=2.0)
    assert size == pytest.approx(25.0)
