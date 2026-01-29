"""
Script de ejemplo para ingerir datos desde IBKR.

Requisitos:
1. TWS o IB Gateway corriendo
2. Configurar en .env:
   - IBKR_HOST=127.0.0.1
   - IBKR_PORT=7497 (paper) o 4001 (live)
   - IBKR_CLIENT_ID=1

Ejemplo de uso:
    python -m scripts.ingest_from_ibkr --symbols EURUSD,GBPUSD --timeframe 1h --days 30
"""

from __future__ import annotations
import argparse
import sys
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data_pipeline.providers import IBKRProvider
from desk_grade import api

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Ingiere datos OHLCV desde IBKR")
    parser.add_argument(
        "--symbols",
        required=True,
        help="Símbolos separados por comas (ej: EURUSD,GBPUSD,AAPL)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        help="Timeframe (1m, 5m, 15m, 1h, 1d)",
    )
    parser.add_argument(
        "--asset",
        default="FOREX",
        help="Clase de activo (USA_STOCK, FOREX, FUTURES, CRYPTO)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Días de datos históricos a obtener",
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(days=args.days)

    print(f"[IBKR] Conectando a IBKR...")
    print(f"  Host: {os.getenv('IBKR_HOST', '127.0.0.1')}")
    print(f"  Port: {os.getenv('IBKR_PORT', '7497')}")
    print(f"  Símbolos: {', '.join(symbols)}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Período: {start_ts.date()} a {end_ts.date()}")

    try:
        provider = IBKRProvider(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),
            client_id=int(os.getenv("IBKR_CLIENT_ID", "1")),
        )

        with provider:
            df = provider.fetch_ohlcv(
                symbols=symbols,
                timeframe=args.timeframe,
                start_ts=start_ts.isoformat(),
                end_ts=end_ts.isoformat(),
                asset=args.asset,
            )

        if df.empty:
            print("[IBKR] No se obtuvieron datos")
            sys.exit(1)

        print(f"[IBKR] Obtenidos {len(df)} registros")
        print(f"[IBKR] Insertando en base de datos...")

        count = 0
        for _, row in df.iterrows():
            api.execute(
                """
                INSERT INTO ohlcv (symbol, ts, open, high, low, close, volume, timeframe, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ibkr')
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
            if count % 100 == 0:
                print(f"  Insertados {count}/{len(df)} registros...")

        print(f"[IBKR] Completado: {count} registros insertados")
        print(f"[IBKR] Rango: {df['ts'].min()} a {df['ts'].max()}")

    except Exception as e:
        print(f"[IBKR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
