"""
Provider para leer datos OHLCV desde archivos CSV.
"""

from __future__ import annotations
import pandas as pd
from typing import Optional
from .base import Provider


class CsvProvider(Provider):
    """
    Lee OHLCV desde un archivo CSV.

    Columnas esperadas:
    - ts (timestamp ISO)
    - symbol
    - open, high, low, close
    - volume (opcional)
    """

    def __init__(self, path: str):
        """
        Args:
            path: Ruta al archivo CSV
        """
        self.path = path

    def fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        if "ts" not in df.columns:
            raise ValueError("CSV debe incluir columna 'ts'")
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        if symbols:
            df = df[df["symbol"].isin(symbols)]
        if start_ts:
            df = df[df["ts"] >= pd.to_datetime(start_ts, utc=True)]
        if end_ts:
            df = df[df["ts"] <= pd.to_datetime(end_ts, utc=True)]
        for c in ["open", "high", "low", "close"]:
            if c not in df.columns:
                raise ValueError(f"CSV falta columna requerida: {c}")
        if "volume" not in df.columns:
            df["volume"] = 0
        # Normalizar orden y tipos
        df = df[["ts", "symbol", "open", "high", "low", "close", "volume"]].copy()
        return df
