"""
Provider para obtener datos OHLCV desde TradingView.

Opciones:
1. Pine Script export (recomendado): Exportar datos desde Pine Script a CSV
2. TradingView API (limitada): Usar API REST si está disponible
"""

from __future__ import annotations
import os
import pandas as pd
from typing import Optional
from .base import Provider


class TradingViewProvider(Provider):
    """
    Provider para TradingView.
    
    TradingView no tiene una API pública completa para datos históricos.
    Opciones:
    1. Exportar datos desde Pine Script a CSV (recomendado)
    2. Usar webhook/API privada si tienes acceso
    """

    def __init__(self, export_path: Optional[str] = None):
        """
        Args:
            export_path: Ruta a carpeta con CSVs exportados desde Pine Script
        """
        self.export_path = export_path or os.getenv("TRADINGVIEW_EXPORT_PATH")
        
        if not self.export_path:
            raise ValueError(
                "TradingViewProvider requiere TRADINGVIEW_EXPORT_PATH "
                "con CSVs exportados desde Pine Script"
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
        Lee datos desde CSVs exportados por Pine Script.
        
        Formato esperado del CSV:
        - Nombre: {symbol}_{timeframe}.csv
        - Columnas: time,open,high,low,close,volume
        """
        import glob
        
        all_data = []
        
        for symbol in symbols:
            # Buscar archivo CSV para este símbolo y timeframe
            pattern = os.path.join(
                self.export_path,
                f"{symbol}_{timeframe}.csv",
            )
            
            files = glob.glob(pattern)
            if not files:
                # Intentar sin timeframe
                pattern_alt = os.path.join(self.export_path, f"{symbol}*.csv")
                files = glob.glob(pattern_alt)
            
            for file_path in files:
                try:
                    df_file = pd.read_csv(file_path)
                    
                    # Normalizar nombres de columnas
                    col_map = {
                        "time": "ts",
                        "Time": "ts",
                        "TIME": "ts",
                        "timestamp": "ts",
                        "Timestamp": "ts",
                    }
                    df_file = df_file.rename(columns=col_map)
                    
                    if "ts" not in df_file.columns:
                        # Intentar primera columna como timestamp
                        df_file.columns.values[0] = "ts"
                    
                    df_file["ts"] = pd.to_datetime(df_file["ts"], utc=True)
                    df_file["symbol"] = symbol.upper()
                    
                    # Asegurar columnas OHLCV
                    required_cols = ["open", "high", "low", "close"]
                    for col in required_cols:
                        if col not in df_file.columns:
                            # Intentar mayúsculas
                            col_upper = col.upper()
                            if col_upper in df_file.columns:
                                df_file[col] = df_file[col_upper]
                            else:
                                raise ValueError(f"CSV falta columna: {col}")
                    
                    if "volume" not in df_file.columns:
                        df_file["volume"] = 0
                    
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

    @staticmethod
    def generate_pine_script_export_script(symbols: list[str], timeframe: str) -> str:
        """
        Genera un script Pine Script de ejemplo para exportar datos.
        
        Copia este script en TradingView y ejecútalo para exportar datos.
        """
        return f"""
//@version=5
// Script para exportar datos OHLCV desde TradingView
// Instrucciones:
// 1. Copia este script en Pine Editor
// 2. Ajusta los símbolos y timeframe
// 3. Ejecuta y exporta los datos manualmente o usa webhook

indicator("Desk-Grade Data Export", overlay=true)

// Configuración
symbols = array.from({", ".join([f'"{s}"' for s in symbols])})
timeframe_str = "{timeframe}"

// Para cada símbolo, obtener datos
if barstate.islast
    for i = 0 to array.size(symbols) - 1
        sym = array.get(symbols, i)
        // Obtener datos del timeframe especificado
        [o, h, l, c, v] = request.security(sym, timeframe_str, [open, high, low, close, volume])
        
        // Log para exportar (o usar webhook)
        // En producción, usarías webhook para enviar a tu API
        label.new(bar_index, high, text=sym + "\\n" + str.tostring(c))
"""