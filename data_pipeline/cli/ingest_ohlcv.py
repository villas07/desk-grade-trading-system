"""
Script CLI para ingerir datos OHLCV desde diferentes providers.

Ejemplos de uso:
    # Desde CSV
    python -m data_pipeline.cli.ingest_ohlcv --provider csv --path data.csv --timeframe 1d --asset USA_STOCK

    # Desde QuantConnect (Lean local)
    python -m data_pipeline.cli.ingest_ohlcv --provider quantconnect --timeframe 1d --asset USA_STOCK --symbols AAPL,TSLA

    # Desde IBKR
    python -m data_pipeline.cli.ingest_ohlcv --provider ibkr --timeframe 1h --asset FOREX --symbols EURUSD,GBPUSD

    # Desde TradingView (CSV export)
    python -m data_pipeline.cli.ingest_ohlcv --provider tradingview --timeframe 1d --asset USA_STOCK --symbols AAPL
"""

from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from data_pipeline.providers import (
    CsvProvider,
    QuantConnectProvider,
    IBKRProvider,
    TradingViewProvider,
)
from desk_grade import api

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Ingiere datos OHLCV desde diferentes providers"
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=["csv", "quantconnect", "ibkr", "tradingview"],
        help="Provider de datos",
    )
    parser.add_argument(
        "--path",
        help="Ruta al archivo/carpeta (requerido para csv/tradingview)",
    )
    parser.add_argument(
        "--symbols",
        required=True,
        help="Símbolos separados por comas (ej: AAPL,TSLA,EURUSD)",
    )
    parser.add_argument(
        "--timeframe",
        required=True,
        help="Timeframe (1m, 5m, 15m, 1h, 1d)",
    )
    parser.add_argument(
        "--asset",
        required=True,
        help="Clase de activo (USA_STOCK, FOREX, FUTURES, CRYPTO)",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Nombre de la fuente (default: nombre del provider)",
    )
    parser.add_argument(
        "--start",
        help="Fecha de inicio (ISO format, ej: 2024-01-01)",
    )
    parser.add_argument(
        "--end",
        help="Fecha de fin (ISO format, ej: 2024-12-31)",
    )

    args = parser.parse_args()

    # Parsear símbolos
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    # Crear provider
    if args.provider == "csv":
        if not args.path:
            print("ERROR: --path es requerido para provider csv")
            sys.exit(1)
        provider = CsvProvider(args.path)
    elif args.provider == "quantconnect":
        provider = QuantConnectProvider()
    elif args.provider == "ibkr":
        provider = IBKRProvider(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),
            client_id=int(os.getenv("IBKR_CLIENT_ID", "1")),
        )
    elif args.provider == "tradingview":
        if not args.path:
            args.path = os.getenv("TRADINGVIEW_EXPORT_PATH")
        if not args.path:
            print("ERROR: --path o TRADINGVIEW_EXPORT_PATH es requerido")
            sys.exit(1)
        provider = TradingViewProvider(export_path=args.path)
    else:
        print(f"ERROR: Provider desconocido: {args.provider}")
        sys.exit(1)

    # Obtener datos
    print(f"[INGEST] Obteniendo datos desde {args.provider}...")
    print(f"  Símbolos: {', '.join(symbols)}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Asset: {args.asset}")

    try:
        # IBKR requiere contexto de conexión
        if args.provider == "ibkr":
            with provider:
                df = provider.fetch_ohlcv(
                    symbols=symbols,
                    timeframe=args.timeframe,
                    start_ts=args.start,
                    end_ts=args.end,
                    asset=args.asset,
                )
        else:
            df = provider.fetch_ohlcv(
                symbols=symbols,
                timeframe=args.timeframe,
                start_ts=args.start,
                end_ts=args.end,
                asset=args.asset,
            )

        if df.empty:
            print("[INGEST] No se obtuvieron datos")
            sys.exit(1)

        print(f"[INGEST] Obtenidos {len(df)} registros")

        # Insertar en base de datos
        source = args.source or args.provider
        print(f"[INGEST] Insertando en base de datos (source={source})...")

        count = 0
        for _, row in df.iterrows():
            api.execute(
                """
                INSERT INTO ohlcv (symbol, ts, open, high, low, close, volume, timeframe)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, ts, timeframe) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
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

        print(f"[INGEST] Completado: {count} registros insertados")
        print(f"[INGEST] Rango: {df['ts'].min()} a {df['ts'].max()}")

    except Exception as e:
        print(f"[INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
