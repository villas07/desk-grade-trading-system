"""
Script de ejemplo para ingerir datos desde QuantConnect/Lean.

Opciones:
1. Lean Data Library local (recomendado):
   - Configurar QC_DATA_PATH en .env apuntando a carpeta de datos Lean
   - Ejemplo: QC_DATA_PATH=C:/Lean/Data

2. QuantConnect Cloud API:
   - Configurar QC_USER_ID y QC_API_KEY en .env

Ejemplo de uso:
    python -m scripts.ingest_from_qc --symbols AAPL,TSLA --timeframe 1d --asset USA_STOCK
"""

from __future__ import annotations
import argparse
import sys
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data_pipeline.providers import QuantConnectProvider
from desk_grade import api

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Ingiere datos OHLCV desde QuantConnect/Lean")
    parser.add_argument(
        "--symbols",
        required=True,
        help="Símbolos separados por comas (ej: AAPL,TSLA,EURUSD)",
    )
    parser.add_argument(
        "--timeframe",
        default="1d",
        help="Timeframe (1m, 5m, 15m, 1h, 1d)",
    )
    parser.add_argument(
        "--asset",
        required=True,
        help="Clase de activo (USA_STOCK, FOREX, FUTURES, CRYPTO)",
    )
    parser.add_argument(
        "--start",
        help="Fecha de inicio (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        help="Fecha de fin (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    start_ts = args.start
    end_ts = args.end

    print(f"[QC] Obteniendo datos desde QuantConnect/Lean...")
    print(f"  Símbolos: {', '.join(symbols)}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Asset: {args.asset}")

    if os.getenv("QC_DATA_PATH"):
        print(f"  Usando Lean Data Library: {os.getenv('QC_DATA_PATH')}")
    elif os.getenv("QC_USER_ID"):
        print(f"  Usando QuantConnect Cloud API")
    else:
        print("ERROR: Configura QC_DATA_PATH o QC_USER_ID/QC_API_KEY en .env")
        sys.exit(1)

    try:
        provider = QuantConnectProvider()

        df = provider.fetch_ohlcv(
            symbols=symbols,
            timeframe=args.timeframe,
            start_ts=start_ts,
            end_ts=end_ts,
            asset=args.asset,
        )

        if df.empty:
            print("[QC] No se obtuvieron datos")
            sys.exit(1)

        print(f"[QC] Obtenidos {len(df)} registros")
        print(f"[QC] Insertando en base de datos...")

        count = 0
        for _, row in df.iterrows():
            api.execute(
                """
                INSERT INTO ohlcv (symbol, ts, open, high, low, close, volume, timeframe, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'quantconnect')
                ON CONFLICT (symbol, ts, timeframe) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
                """,
                (
                    row["symbol"],
                    row["ts"].to_pydatetime(),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                    args.timeframe,
                ),
            )
            count += 1
            if count % 1000 == 0:
                print(f"  Insertados {count}/{len(df)} registros...")

        print(f"[QC] Completado: {count} registros insertados")
        print(f"[QC] Rango: {df['ts'].min()} a {df['ts'].max()}")

    except Exception as e:
        print(f"[QC] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
