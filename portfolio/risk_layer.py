from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv

from desk_grade.api import execute


load_dotenv()


@dataclass(frozen=True)
class RiskLimits:
    """Límites de riesgo estáticos cargados desde variables de entorno."""

    max_drawdown_pct: float
    daily_loss_limit_pct: float
    weekly_loss_limit_pct: float
    vol_target: Optional[float]
    sector_cap_pct: Optional[float]
    sizing_mode: str  # "FIXED_FRACTIONAL" o "ATR"
    fixed_fractional: float
    atr_multiplier: float

    @classmethod
    def from_env(cls) -> "RiskLimits":
        sizing_mode = os.getenv("RISK_POSITION_SIZING_MODE", "FIXED_FRACTIONAL").upper()
        return cls(
            max_drawdown_pct=float(os.getenv("RISK_MAX_DRAWDOWN_PCT", "0.2")),
            daily_loss_limit_pct=float(os.getenv("RISK_DAILY_LOSS_PCT", "0.05")),
            weekly_loss_limit_pct=float(os.getenv("RISK_WEEKLY_LOSS_PCT", "0.10")),
            vol_target=float(os.getenv("RISK_VOL_TARGET", "0.0")) or None,
            sector_cap_pct=float(os.getenv("RISK_SECTOR_CAP_PCT", "0.0")) or None,
            sizing_mode=sizing_mode,
            fixed_fractional=float(os.getenv("RISK_FIXED_FRACTIONAL", "0.01")),
            atr_multiplier=float(os.getenv("RISK_ATR_MULTIPLIER", "2.0")),
        )


@dataclass
class RiskGateResult:
    """Resultado de evaluación de gates de riesgo."""

    mode: str  # NORMAL / DEGRADED / HALT
    reasons: List[str]

    @property
    def allow_new_risk(self) -> bool:
        return self.mode == "NORMAL"

    @property
    def reduce_only(self) -> bool:
        return self.mode in {"DEGRADED", "HALT"}


@dataclass
class ExposureSnapshot:
    """Snapshot de exposición que se puede persistir en DB."""

    symbol: str
    sector: Optional[str]
    strategy_id: str
    gross_exposure: float
    net_exposure: float
    leverage: Optional[float]


class RiskEngine:
    """
    Capa de riesgo determinista:
    - Gates de riesgo (DD, pérdidas diaria/semanal, reconciliación, correlación, sector caps)
    - Position sizing (fixed fractional / ATR-based)
    - Vol targeting
    - Construcción y persistencia de exposure_snapshots

    NO ejecuta órdenes ni habla con el broker.
    """

    def __init__(self, limits: Optional[RiskLimits] = None) -> None:
        self.limits = limits or RiskLimits.from_env()

    # -------------------------
    # GATES DE RIESGO
    # -------------------------
    def evaluate_gates(
        self,
        *,
        equity: float,
        peak_equity: float,
        daily_pnl: float,
        weekly_pnl: float,
        sector_exposure_pct: Optional[Dict[str, float]] = None,
        correlation_flag: bool = False,
        reconciliation_flag: bool = False,
    ) -> RiskGateResult:
        """
        Evalúa todos los gates de riesgo y devuelve el modo de operación:
        - NORMAL     : trading normal permitido
        - DEGRADED   : sólo reducción de riesgo, sin nuevas exposiciones agresivas
        - HALT       : no se permite incrementar riesgo

        Esta función es completamente determinista y side‑effect free.
        """
        reasons: List[str] = []
        mode: str = "NORMAL"

        # Max drawdown
        if peak_equity > 0:
            drawdown_pct = (peak_equity - equity) / peak_equity
            if drawdown_pct >= self.limits.max_drawdown_pct:
                mode = "HALT"
                reasons.append(
                    f"MAX_DRAWDOWN_SUPERADO dd={drawdown_pct:.4f} limite={self.limits.max_drawdown_pct:.4f}"
                )

        # Pérdida diaria
        daily_loss_limit_value = -self.limits.daily_loss_limit_pct * equity
        if daily_pnl <= daily_loss_limit_value:
            mode = "HALT"
            reasons.append(
                f"DAILY_LOSS_LIMIT_SUPERADO pnl={daily_pnl:.2f} limite={daily_loss_limit_value:.2f}"
            )

        # Pérdida semanal
        weekly_loss_limit_value = -self.limits.weekly_loss_limit_pct * equity
        if weekly_pnl <= weekly_loss_limit_value:
            mode = "HALT"
            reasons.append(
                f"WEEKLY_LOSS_LIMIT_SUPERADO pnl={weekly_pnl:.2f} limite={weekly_loss_limit_value:.2f}"
            )

        # Reconciliación → HALT
        if reconciliation_flag:
            mode = "HALT"
            reasons.append("RECONCILIATION_FLAG_ACTIVO")

        # Correlación → DEGRADED si aún no estamos en HALT
        if correlation_flag and mode != "HALT":
            mode = "DEGRADED"
            reasons.append("CORRELATION_FLAG_ACTIVO")

        # Sector caps → si hay sectores por encima del límite, modo DEGRADED
        if sector_exposure_pct and self.limits.sector_cap_pct:
            for sector, pct in sector_exposure_pct.items():
                if abs(pct) > self.limits.sector_cap_pct:
                    if mode != "HALT":
                        mode = "DEGRADED"
                    reasons.append(
                        f"SECTOR_CAP_SUPERADO sector={sector} exp_pct={pct:.4f} "
                        f"limite={self.limits.sector_cap_pct:.4f}"
                    )

        if not reasons:
            reasons.append("RISK_OK")

        return RiskGateResult(mode=mode, reasons=reasons)

    # -------------------------
    # POSITION SIZING
    # -------------------------
    def _position_size_fixed_fractional(self, *, price: float, equity: float) -> float:
        """
        Fixed fractional: arriesga un % fijo del equity por trade.
        size ≈ (equity * fixed_fractional) / price
        """
        if price <= 0 or equity <= 0:
            return 0.0
        risk_dollars = equity * self.limits.fixed_fractional
        size = risk_dollars / price
        return max(0.0, math.floor(size))

    def _position_size_atr_based(
        self, *, price: float, equity: float, atr: Optional[float]
    ) -> float:
        """
        ATR-based sizing: arriesga un % fijo del equity, dimensionando
        el stop como atr_multiplier * ATR.

        size ≈ (equity * fixed_fractional) / (ATR * atr_multiplier)
        """
        if price <= 0 or equity <= 0 or not atr or atr <= 0:
            return 0.0

        risk_dollars = equity * self.limits.fixed_fractional
        per_unit_risk = atr * self.limits.atr_multiplier
        if per_unit_risk <= 0:
            return 0.0

        size = risk_dollars / per_unit_risk
        return max(0.0, math.floor(size))

    def compute_position_size(
        self,
        *,
        symbol: str,
        price: float,
        equity: float,
        atr: Optional[float] = None,
    ) -> float:
        """
        Calcula el tamaño de posición recomendado para un símbolo dado
        según la configuración de sizing:

        - FIXED_FRACTIONAL: usa sólo equity y precio
        - ATR: usa equity y ATR; si ATR no está disponible, devuelve 0

        No aplica aún vol targeting; este se aplica después sobre el tamaño base.
        """
        sizing_mode = self.limits.sizing_mode.upper()
        if sizing_mode == "ATR":
            return self._position_size_atr_based(price=price, equity=equity, atr=atr)
        return self._position_size_fixed_fractional(price=price, equity=equity)

    # -------------------------
    # VOL TARGETING
    # -------------------------
    def apply_vol_targeting(
        self,
        *,
        base_size: float,
        asset_annual_vol: Optional[float],
    ) -> float:
        """
        Ajusta el tamaño de posición en función de la volatilidad anualizada
        del activo y la vol target del portafolio.

        size_vol = base_size * (vol_target / asset_annual_vol)

        Si no hay vol_target o no se conoce la vol del activo, devuelve base_size.
        """
        if base_size <= 0:
            return 0.0
        if not self.limits.vol_target or not asset_annual_vol or asset_annual_vol <= 0:
            return base_size

        scaled = base_size * (self.limits.vol_target / asset_annual_vol)
        return max(0.0, math.floor(scaled))

    # -------------------------
    # EXPOSURE SNAPSHOTS
    # -------------------------
    def build_exposure_snapshot(
        self,
        *,
        symbol: str,
        sector: Optional[str],
        strategy_id: str,
        qty: float,
        price: float,
        equity: Optional[float] = None,
    ) -> ExposureSnapshot:
        """
        Construye un snapshot de exposición a partir de cantidad y precio.
        No tiene efectos secundarios; sólo devuelve la estructura.
        """
        position_value = qty * price
        gross_exposure = abs(position_value)
        net_exposure = position_value
        leverage = None
        if equity and equity > 0:
            leverage = gross_exposure / equity

        return ExposureSnapshot(
            symbol=symbol,
            sector=sector,
            strategy_id=strategy_id,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            leverage=leverage,
        )

    def persist_exposure_snapshot(self, snapshot: ExposureSnapshot) -> None:
        """
        Persiste un snapshot de exposición en la tabla exposure_snapshots.

        Esta es la ÚNICA función de esta clase que tiene efectos en la base
        de datos, y no interactúa con órdenes ni fills.
        """
        leverage_value = snapshot.leverage if snapshot.leverage is not None else None
        execute(
            """
            INSERT INTO exposure_snapshots (symbol, sector, gross_exposure, net_exposure, leverage, strategy_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                snapshot.symbol,
                snapshot.sector,
                snapshot.gross_exposure,
                snapshot.net_exposure,
                leverage_value,
                snapshot.strategy_id,
            ),
        )
