"""
Interfaz base para providers de datos OHLCV.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class Provider(ABC):
    """Provider interface. Returns normalized OHLCV bars for one or many symbols."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        """
        Retorna DataFrame con columnas: ts, symbol, open, high, low, close, volume.
        
        Args:
            symbols: Lista de símbolos a obtener
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            start_ts: Timestamp de inicio (ISO string o None)
            end_ts: Timestamp de fin (ISO string o None)
            asset: Clase de activo (USA_STOCK, FOREX, FUTURES, CRYPTO, etc.)
            
        Returns:
            DataFrame con columnas normalizadas: ts, symbol, open, high, low, close, volume
        """
        raise NotImplementedError
