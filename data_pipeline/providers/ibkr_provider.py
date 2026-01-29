"""
Provider para obtener datos OHLCV desde Interactive Brokers (IBKR).

Usa ib_insync para conectarse a TWS/IB Gateway.
"""

from __future__ import annotations
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta, timezone
from .base import Provider

try:
    from ib_insync import IB, Stock, Forex, Future, Crypto, util
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False


class IBKRProvider(Provider):
    """
    Provider para Interactive Brokers usando ib_insync.
    
    Requiere:
    - TWS o IB Gateway corriendo
    - ib_insync instalado: pip install ib_insync
    - Conexión configurada (host, port)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
    ):
        """
        Args:
            host: Host de TWS/IB Gateway (default: 127.0.0.1)
            port: Puerto (7497 para paper, 4001 para live)
            client_id: ID de cliente único
        """
        if not IB_AVAILABLE:
            raise ImportError(
                "ib_insync no está instalado. Instala con: pip install ib_insync"
            )
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self._connected = False

    def connect(self) -> None:
        """Conecta a TWS/IB Gateway."""
        if not self._connected:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self._connected = True

    def disconnect(self) -> None:
        """Desconecta de TWS/IB Gateway."""
        if self._connected:
            self.ib.disconnect()
            self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        """
        Obtiene datos OHLCV desde IBKR.
        
        Args:
            symbols: Lista de símbolos
            timeframe: 1m, 5m, 15m, 1h, 1d, etc.
            start_ts: Timestamp de inicio (ISO string)
            end_ts: Timestamp de fin (ISO string)
            asset: Clase de activo (USA_STOCK, FOREX, FUTURES, CRYPTO)
        """
        if not self._connected:
            self.connect()
        
        # Mapear timeframe a barSize de IBKR
        bar_size_map = {
            "1m": "1 min",
            "5m": "5 mins",
            "15m": "15 mins",
            "30m": "30 mins",
            "1h": "1 hour",
            "1d": "1 day",
        }
        bar_size = bar_size_map.get(timeframe, "1 day")
        
        # Mapear asset a tipo de contrato IBKR
        asset_type_map = {
            "USA_STOCK": Stock,
            "FOREX": Forex,
            "FUTURES": Future,
            "CRYPTO": Crypto,
        }
        contract_class = asset_type_map.get(asset, Stock)
        
        all_data = []
        
        for symbol in symbols:
            try:
                # Crear contrato IBKR
                if asset == "FOREX":
                    # FOREX: formato "EURUSD" -> "EUR", "USD"
                    if len(symbol) == 6:
                        base = symbol[:3]
                        quote = symbol[3:]
                        contract = Forex(base, quote)
                    else:
                        print(f"Símbolo FOREX inválido: {symbol}")
                        continue
                elif asset == "USA_STOCK":
                    contract = Stock(symbol, "SMART", "USD")
                elif asset == "FUTURES":
                    # Para futuros, el símbolo debe incluir mes/año
                    # Ejemplo: "ES", "NQ", etc. (requiere lógica adicional)
                    contract = Future(symbol, "CME")
                elif asset == "CRYPTO":
                    # IBKR crypto: formato "BTCUSD"
                    contract = Crypto(symbol, "PAXOS", "USD")
                else:
                    contract = Stock(symbol, "SMART", "USD")
                
                # Convertir timestamps
                if start_ts:
                    start_dt = pd.to_datetime(start_ts, utc=True).replace(tzinfo=None)
                else:
                    start_dt = datetime.now() - timedelta(days=30)
                
                if end_ts:
                    end_dt = pd.to_datetime(end_ts, utc=True).replace(tzinfo=None)
                else:
                    end_dt = datetime.now()
                
                # Solicitar datos históricos
                bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime=end_dt,
                    durationStr=f"{(end_dt - start_dt).days} D",
                    barSizeSetting=bar_size,
                    whatToShow="TRADES",
                    useRTH=True,
                )
                
                if bars:
                    # Convertir a DataFrame
                    df_symbol = util.df(bars)
                    df_symbol["symbol"] = symbol.upper()
                    df_symbol["ts"] = pd.to_datetime(df_symbol["date"], utc=True)
                    df_symbol = df_symbol.rename(columns={
                        "open": "open",
                        "high": "high",
                        "low": "low",
                        "close": "close",
                        "volume": "volume",
                    })
                    all_data.append(df_symbol[["ts", "symbol", "open", "high", "low", "close", "volume"]])
            except Exception as e:
                print(f"Error obteniendo datos de IBKR para {symbol}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame(columns=["ts", "symbol", "open", "high", "low", "close", "volume"])
        
        df = pd.concat(all_data, ignore_index=True)
        df = df.sort_values(["symbol", "ts"])
        return df
