from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Tuple

from desk_grade.api import execute, fetch_all, fetch_one

from . import metrics


@dataclass
class TradeLifecycleInfo:
    symbol: str
    strategy_id: str
    state: str
    entry_ts: datetime
    entry_price: float
    stop_price: float
    qty: float


class LifecycleEngine:
    """
    Gestiona el ciclo de vida de las operaciones:
      - Estados FLAT → ENTERED → MANAGED → EXITED
      - position_lifecycle
      - cooldown tras salida
      - trade_journal (R, pnl_r, MAE, MFE)
    """

    def __init__(self, cooldown_minutes: int = 5, ohlcv_timeframe: str = "1m") -> None:
        self.cooldown_minutes = cooldown_minutes
        self.ohlcv_timeframe = ohlcv_timeframe

    # -------------------------
    # Helpers DB
    # -------------------------
    def _load_trade(self, symbol: str, strategy_id: str) -> Optional[TradeLifecycleInfo]:
        row = fetch_one(
            """
            SELECT symbol, strategy_id, state, entry_ts, entry_price, stop_price, qty
            FROM public.trade_state
            WHERE symbol = %s
              AND strategy_id = %s
            """,
            (symbol, strategy_id),
        )
        if not row or row["entry_ts"] is None or row["stop_price"] is None:
            return None

        return TradeLifecycleInfo(
            symbol=row["symbol"],
            strategy_id=row["strategy_id"],
            state=row["state"],
            entry_ts=row["entry_ts"],
            entry_price=float(row["entry_price"]),
            stop_price=float(row["stop_price"]),
            qty=float(row["qty"] or 0.0),
        )

    def _insert_lifecycle_event(
        self,
        symbol: str,
        strategy_id: str,
        lifecycle_state: str,
        meta: Optional[dict] = None,
    ) -> None:
        execute(
            """
            INSERT INTO position_lifecycle (symbol, strategy_id, lifecycle_state, meta)
            VALUES (%s, %s, %s, %s)
            """,
            (symbol, strategy_id, lifecycle_state, meta or {}),
        )

    def _fetch_ohlcv_prices(
        self,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> List[float]:
        rows = fetch_all(
            """
            SELECT close
            FROM ohlcv
            WHERE symbol = %s
              AND timeframe = %s
              AND ts >= %s
              AND ts <= %s
            ORDER BY ts ASC
            """,
            (symbol, self.ohlcv_timeframe, start_ts, end_ts),
        )
        return [float(r["close"]) for r in rows]

    # -------------------------
    # API pública
    # -------------------------
    def register_entry(
        self,
        *,
        symbol: str,
        strategy_id: str,
        qty: float,
        entry_price: float,
        stop_price: float,
        tp1_price: float,
        tp2_price: float,
    ) -> None:
        """
        Marca una nueva entrada en trade_state y position_lifecycle.
        """
        side_state = "ENTERED"
        execute(
            """
            INSERT INTO trade_state (
                symbol, strategy_id, state, entry_ts, entry_price,
                qty, stop_price, tp1_price, tp2_price, trailing_price, last_updated
            )
            VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s, NULL, NOW())
            ON CONFLICT (symbol, strategy_id) DO UPDATE
            SET state = EXCLUDED.state,
                entry_ts = EXCLUDED.entry_ts,
                entry_price = EXCLUDED.entry_price,
                qty = EXCLUDED.qty,
                stop_price = EXCLUDED.stop_price,
                tp1_price = EXCLUDED.tp1_price,
                tp2_price = EXCLUDED.tp2_price,
                trailing_price = EXCLUDED.trailing_price,
                last_updated = EXCLUDED.last_updated
            """,
            (
                symbol,
                strategy_id,
                side_state,
                entry_price,
                qty,
                stop_price,
                tp1_price,
                tp2_price,
            ),
        )
        self._insert_lifecycle_event(
            symbol=symbol,
            strategy_id=strategy_id,
            lifecycle_state="ENTERED",
        )

    def mark_managed(self, symbol: str, strategy_id: str) -> None:
        """
        Marca una operación como MANAGED manualmente (por ejemplo, tras TP1).
        """
        execute(
            """
            UPDATE trade_state
            SET state = 'MANAGED',
                last_updated = NOW()
            WHERE symbol = %s
              AND strategy_id = %s
            """,
            (symbol, strategy_id),
        )
        self._insert_lifecycle_event(
            symbol=symbol,
            strategy_id=strategy_id,
            lifecycle_state="MANAGED",
        )

    def apply_cooldown(self, symbol: str, strategy_id: str, exit_ts: datetime) -> None:
        """
        Registra un evento EXITED y almacena en meta el cooldown_until.
        """
        cooldown_until = exit_ts + timedelta(minutes=self.cooldown_minutes)
        self._insert_lifecycle_event(
            symbol=symbol,
            strategy_id=strategy_id,
            lifecycle_state="EXITED",
            meta={"cooldown_until": cooldown_until.isoformat()},
        )

    def is_in_cooldown(self, symbol: str, strategy_id: str, now: Optional[datetime] = None) -> bool:
        """
        Devuelve True si existe un evento EXITED reciente cuyo cooldown_until
        aún no ha expirado.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        row = fetch_one(
            """
            SELECT meta
            FROM position_lifecycle
            WHERE symbol = %s
              AND strategy_id = %s
              AND lifecycle_state = 'EXITED'
            ORDER BY ts DESC
            LIMIT 1
            """,
            (symbol, strategy_id),
        )
        if not row or not row["meta"]:
            return False

        meta = row["meta"]
        cooldown_str = meta.get("cooldown_until")
        if not cooldown_str:
            return False

        try:
            cooldown_until = datetime.fromisoformat(cooldown_str)
        except Exception:
            return False

        return now < cooldown_until

    def _compute_trade_journal_metrics(
        self,
        *,
        side: str,
        entry_price: float,
        stop_price: float,
        exit_price: float,
        qty: float,
        price_path: Iterable[float],
    ) -> Tuple[float, float, float, float]:
        """
        Calcula R, pnl_r, MAE y MFE para una operación concreta.
        """
        r = metrics.r_multiple(side, entry_price, stop_price, exit_price)
        pnl_r = metrics.realized_pnl(side, entry_price, exit_price, qty)
        mae_r, mfe_r = metrics.mae_mfe_r(side, entry_price, stop_price, price_path)
        return r, pnl_r, mae_r, mfe_r

    def process_exited_trades(self) -> None:
        """
        Recorre todas las operaciones con estado EXITED y genera entradas
        en trade_journal (si aún no existen) y eventos de lifecycle/cooldown.
        """
        exited_trades = fetch_all(
            """
            SELECT symbol, strategy_id, entry_ts, entry_price, stop_price, qty, last_updated
            FROM public.trade_state
            WHERE state = 'EXITED'
              AND qty = 0
            """,
        )

        for row in exited_trades:
            symbol = row["symbol"]
            strategy_id = row["strategy_id"]
            entry_ts = row["entry_ts"]
            exit_ts = row["last_updated"]
            entry_price = float(row["entry_price"])
            stop_price = float(row["stop_price"])
            qty = float(row["qty"] or 0.0)

            # Verificamos si ya existe un journal equivalente
            existing = fetch_one(
                """
                SELECT 1
                FROM trade_journal
                WHERE symbol = %s
                  AND strategy_id = %s
                  AND entry_ts = %s
                  AND exit_ts = %s
                """,
                (symbol, strategy_id, entry_ts, exit_ts),
            )
            if existing:
                continue

            # Obtenemos precios OHLCV para MAE/MFE
            price_path = self._fetch_ohlcv_prices(
                symbol=symbol,
                start_ts=entry_ts,
                end_ts=exit_ts,
            )
            # En caso extremo de no tener datos, usamos sólo entry/exit
            if not price_path:
                price_path = [entry_price, entry_price]

            side = "BUY" if qty >= 0 else "SELL"
            # Si qty es 0 (porque ya se cerró), asumimos el lado según stop/entry
            if qty == 0 and stop_price is not None:
                side = "BUY" if entry_price >= stop_price else "SELL"

            exit_price = price_path[-1]
            r, pnl_r, mae_r, mfe_r = self._compute_trade_journal_metrics(
                side=side,
                entry_price=entry_price,
                stop_price=stop_price,
                exit_price=exit_price,
                qty=abs(qty) if qty != 0 else 1.0,
                price_path=price_path,
            )

            execute(
                """
                INSERT INTO trade_journal (
                    symbol, strategy_id, entry_ts, exit_ts,
                    entry_price, exit_price, qty, r, pnl_r, mae, mfe
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    symbol,
                    strategy_id,
                    entry_ts,
                    exit_ts,
                    entry_price,
                    exit_price,
                    abs(qty),
                    r,
                    pnl_r,
                    mae_r,
                    mfe_r,
                ),
            )

            # Registra lifecycle EXITED + cooldown
            self.apply_cooldown(symbol=symbol, strategy_id=strategy_id, exit_ts=exit_ts)

            # Dejamos la operación en estado FLAT para futuras entradas
            execute(
                """
                UPDATE trade_state
                SET state = 'FLAT',
                    entry_ts = NULL,
                    entry_price = NULL,
                    stop_price = NULL,
                    tp1_price = NULL,
                    tp2_price = NULL,
                    trailing_price = NULL,
                    last_updated = NOW()
                WHERE symbol = %s
                  AND strategy_id = %s
                """,
                (symbol, strategy_id),
            )
