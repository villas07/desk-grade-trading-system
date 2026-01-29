# Módulo de Ingesta de Datos

Este módulo permite obtener datos OHLCV desde múltiples fuentes y almacenarlos en la base de datos.

## Fuentes Soportadas

### 1. QuantConnect/Lean
- **Lean Data Library local**: Lee datos desde carpeta local de Lean
- **QuantConnect Cloud API**: Obtiene datos desde QC Cloud (limitado)

**Configuración:**
```bash
# Opción 1: Lean Data Library (recomendado)
QC_DATA_PATH=C:/Lean/Data

# Opción 2: QuantConnect Cloud API
QC_USER_ID=tu_user_id
QC_API_KEY=tu_api_key
```

**Uso:**
```bash
python -m scripts.ingest_from_qc --symbols AAPL,TSLA --timeframe 1d --asset USA_STOCK
```

### 2. Interactive Brokers (IBKR)
- Requiere TWS o IB Gateway corriendo
- Usa `ib_insync` para conectarse

**Configuración:**
```bash
IBKR_HOST=127.0.0.1
IBKR_PORT=7497  # 7497 para paper, 4001 para live
IBKR_CLIENT_ID=1
```

**Uso:**
```bash
# Asegúrate de tener TWS/IB Gateway corriendo
python -m scripts.ingest_from_ibkr --symbols EURUSD,GBPUSD --timeframe 1h --days 30
```

### 3. TradingView
- Lee CSVs exportados desde Pine Script
- No hay API pública completa, requiere exportación manual

**Configuración:**
```bash
TRADINGVIEW_EXPORT_PATH=C:/TradingView/exports
```

**Uso:**
1. Exporta datos desde Pine Script en TradingView
2. Guarda CSVs en la carpeta configurada
3. Ejecuta:
```bash
python -m data_pipeline.cli.ingest_ohlcv --provider tradingview --symbols AAPL --timeframe 1d --asset USA_STOCK
```

### 4. CSV (Desarrollo/Testing)
- Para archivos CSV locales

**Uso:**
```bash
python -m data_pipeline.cli.ingest_ohlcv --provider csv --path data.csv --symbols AAPL,TSLA --timeframe 1d --asset USA_STOCK
```

## Instalación

```bash
pip install -r requirements.txt
```

Dependencias adicionales según provider:
- **IBKR**: `ib-insync` (ya incluido en requirements.txt)
- **QuantConnect API**: `requests` (ya incluido)

## Estructura de Datos

Todos los providers retornan un DataFrame normalizado con columnas:
- `ts`: Timestamp (UTC)
- `symbol`: Símbolo del activo
- `open`, `high`, `low`, `close`: Precios OHLC
- `volume`: Volumen

Los datos se almacenan en la tabla `ohlcv` con:
- Constraint único: `(symbol, ts, timeframe)` para evitar duplicados
- Campo `source`: Identifica la fuente de los datos

## Ejemplos Completos

### Ingesta desde IBKR (FOREX)
```bash
# 1. Inicia TWS o IB Gateway
# 2. Configura en .env:
#    IBKR_HOST=127.0.0.1
#    IBKR_PORT=7497
# 3. Ejecuta:
python -m scripts.ingest_from_ibkr --symbols EURUSD,GBPUSD,USDJPY --timeframe 1h --asset FOREX --days 90
```

### Ingesta desde QuantConnect (Stocks)
```bash
# 1. Configura en .env:
#    QC_DATA_PATH=C:/Lean/Data
# 2. Ejecuta:
python -m scripts.ingest_from_qc --symbols AAPL,TSLA,MSFT --timeframe 1d --asset USA_STOCK
```

### Ingesta desde TradingView
```bash
# 1. Exporta datos desde Pine Script en TradingView
# 2. Guarda CSVs en carpeta (ej: C:/TradingView/exports/AAPL_1d.csv)
# 3. Configura en .env:
#    TRADINGVIEW_EXPORT_PATH=C:/TradingView/exports
# 4. Ejecuta:
python -m data_pipeline.cli.ingest_ohlcv --provider tradingview --symbols AAPL --timeframe 1d --asset USA_STOCK
```

## Troubleshooting

### IBKR: "Connection refused"
- Verifica que TWS/IB Gateway esté corriendo
- Verifica host/port en `.env`
- En TWS: Configuración → API → Habilitar "Enable ActiveX and Socket Clients"

### QuantConnect: "No data found"
- Verifica que `QC_DATA_PATH` apunte a carpeta correcta
- Estructura esperada: `{QC_DATA_PATH}/{asset}/{symbol}/{timeframe}/YYYYMMDD.csv`
- Para API: Verifica `QC_USER_ID` y `QC_API_KEY`

### TradingView: "File not found"
- Verifica que los CSVs estén en `TRADINGVIEW_EXPORT_PATH`
- Formato esperado: `{symbol}_{timeframe}.csv`
- Columnas requeridas: `time`, `open`, `high`, `low`, `close`, `volume`

## Próximos Pasos

Después de ingerir datos, puedes:
1. Verificar datos: `python -m scripts.status`
2. Ejecutar ciclo de riesgo: `python -m scripts.run_risk_cycle`
3. Ver dashboards en Grafana: http://localhost:3000
