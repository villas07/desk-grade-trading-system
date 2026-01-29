"""
Provider para obtener datos OHLCV desde QuantConnect/Lean.

Soporta:
- QuantConnect API (cloud)
- Lean Data Library (local)
- Exportaciones CSV desde QC Cloud
"""

from __future__ import annotations
import os
import pandas as pd
from typing import Optional
import requests
from datetime import datetime, timezone
from .base import Provider


class QuantConnectProvider(Provider):
    """
    Provider para QuantConnect/Lean.
    
    Opciones de uso:
    1. API de QuantConnect Cloud (requiere QC_USER_ID y QC_API_KEY)
    2. Lean Data Library local (requiere ruta a datos)
    3. CSV exportado desde QC Cloud
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        data_path: Optional[str] = None,
    ):
        """
        Args:
            user_id: QuantConnect User ID (para API)
            api_key: QuantConnect API Key (para API)
            data_path: Ruta a carpeta de datos Lean (alternativa a API)
        """
        self.user_id = user_id or os.getenv("QC_USER_ID")
        self.api_key = api_key or os.getenv("QC_API_KEY")
        self.data_path = data_path or os.getenv("QC_DATA_PATH")
        
        if not self.user_id and not self.data_path:
            raise ValueError(
                "QuantConnectProvider requiere QC_USER_ID/QC_API_KEY (API) "
                "o QC_DATA_PATH (Lean local)"
            )

    def fetch_ohlcv(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        """
        Obtiene datos OHLCV desde QuantConnect.
        
        Nota: La API de QuantConnect tiene limitaciones. Para producción,
        considera exportar datos desde QC Cloud o usar Lean Data Library local.
        """
        if self.data_path:
            return self._fetch_from_lean(symbols, timeframe, start_ts, end_ts, asset)
        else:
            return self._fetch_from_api(symbols, timeframe, start_ts, end_ts, asset)

    def _fetch_from_lean(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        """
        Lee datos desde Lean Data Library local.
        
        Estructura esperada:
        {data_path}/{asset}/{symbol}/{timeframe}/YYYYMMDD.csv
        """
        import glob
        
        all_data = []
        
        for symbol in symbols:
            # Mapear asset a estructura de carpetas Lean
            asset_map = {
                "USA_STOCK": "equity/usa",
                "FOREX": "forex",
                "FUTURES": "future",
                "CRYPTO": "crypto",
            }
            lean_asset = asset_map.get(asset, asset.lower())
            
            # Construir patrón de búsqueda
            pattern = os.path.join(
                self.data_path,
                lean_asset,
                symbol.lower(),
                timeframe.lower(),
                "*.csv",
            )
            
            files = glob.glob(pattern)
            if not files:
                continue
            
            for file_path in sorted(files):
                try:
                    df_file = pd.read_csv(file_path)
                    # Lean usa formato: time,open,high,low,close,volume
                    if "time" in df_file.columns:
                        df_file["ts"] = pd.to_datetime(df_file["time"], utc=True)
                    elif "Time" in df_file.columns:
                        df_file["ts"] = pd.to_datetime(df_file["Time"], utc=True)
                    else:
                        continue
                    
                    df_file["symbol"] = symbol.upper()
                    all_data.append(df_file)
                except Exception as e:
                    print(f"Error leyendo {file_path}: {e}")
                    continue
        
        if not all_data:
            return pd.DataFrame(columns=["ts", "symbol", "open", "high", "low", "close", "volume"])
        
        df = pd.concat(all_data, ignore_index=True)
        
        # Filtrar por fechas
        if start_ts:
            df = df[df["ts"] >= pd.to_datetime(start_ts, utc=True)]
        if end_ts:
            df = df[df["ts"] <= pd.to_datetime(end_ts, utc=True)]
        
        # Normalizar columnas
        df = df[["ts", "symbol", "open", "high", "low", "close", "volume"]].copy()
        df = df.sort_values(["symbol", "ts"])
        return df

    def _fetch_from_api(
        self,
        symbols: list[str],
        timeframe: str,
        start_ts: Optional[str],
        end_ts: Optional[str],
        asset: str,
    ) -> pd.DataFrame:
        """
        Obtiene datos desde QuantConnect Cloud API.
        
        Nota: La API pública de QC es limitada. Para datos históricos completos,
        usa exportaciones CSV o Lean Data Library.
        """
        # QuantConnect API v2 endpoints
        base_url = "https://www.quantconnect.com/api/v2"
        
        all_data = []
        
        for symbol in symbols:
            # Mapear timeframe a resolución de QC
            resolution_map = {
                "1m": "Minute",
                "5m": "Minute",
                "15m": "Minute",
                "1h": "Hour",
                "1d": "Daily",
            }
            resolution = resolution_map.get(timeframe, "Daily")
            
            # Mapear asset a tipo de QC
            asset_type_map = {
                "USA_STOCK": "Equity",
                "FOREX": "Forex",
                "FUTURES": "Future",
                "CRYPTO": "Crypto",
            }
            qc_asset_type = asset_type_map.get(asset, "Equity")
            
            # Construir request
            # Nota: Esto es un ejemplo. La API real de QC puede requerir autenticación diferente
            # y endpoints específicos. Consulta la documentación oficial.
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "type": qc_asset_type,
            }
            
            if start_ts:
                params["start"] = start_ts
            if end_ts:
                params["end"] = end_ts
            
            try:
                # Ejemplo de llamada (ajustar según documentación real de QC API)
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                response = requests.get(
                    f"{base_url}/data/read",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Procesar respuesta según formato de QC API
                    # (ajustar según documentación real)
                    df_symbol = pd.DataFrame(data.get("bars", []))
                    if not df_symbol.empty:
                        df_symbol["symbol"] = symbol.upper()
                        all_data.append(df_symbol)
            except Exception as e:
                print(f"Error obteniendo datos de QC API para {symbol}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame(columns=["ts", "symbol", "open", "high", "low", "close", "volume"])
        
        df = pd.concat(all_data, ignore_index=True)
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df[["ts", "symbol", "open", "high", "low", "close", "volume"]].copy()
        df = df.sort_values(["symbol", "ts"])
        return df
