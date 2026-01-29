## Desk-Grade Ready

Este repositorio contiene una versión funcional del **sistema Desk-Grade** orientado a:

- Trading en modo **paper**.
- Gestión de riesgo centralizada.
- Ciclos intradía orquestados vía scripts de Python.
- Sistema completo y listo para producción.

### Estructura principal

- `docker-compose.yml`: levanta **PostgreSQL + TimescaleDB** y **Grafana**.
- `infra/init.sql`: esquema completo de base de datos (ohlcv, positions, risk_state, trade_state, job_queue, etc.).
- `desk_grade/`:
  - `db.py`: conexión a PostgreSQL usando variables de entorno.
  - `api.py`: helpers de acceso (`execute`, `fetch_all`, `fetch_one`).
  - `config.py`: configuración centralizada.
  - `logging_config.py`: configuración de logging.
- `portfolio/`:
  - `risk_layer.py`: motores de riesgo y gates.
  - `lifecycle_engine.py`: gestión del ciclo de vida de trades.
  - `exit_engine.py`: motor de salidas (stops, TPs, trailing).
  - `metrics.py`: métricas básicas (R, MAE, MFE, PnL).
  - `advanced_metrics.py`: métricas avanzadas (Sharpe, drawdown, expectancy).
  - `order_builder.py`: construcción de intenciones de orden.
  - `exits.py`: lógica de niveles de salida.
- `scripts/`:
  - `run_risk_cycle.py`: ejecuta un ciclo completo de riesgo intradía.
  - `scheduler.py`: scheduler básico para ejecutar ciclos periódicamente.
  - `seed_data.py`: script para poblar datos de prueba.
  - `health_check.py`: verificación de salud del sistema.
  - `status.py`: muestra estado actual del sistema.
- `tests/`: tests unitarios básicos.
- `.env.example`: ejemplo de configuración.
- `requirements.txt`: dependencias de Python.
- `pyproject.toml`: configuración del proyecto Python.

### Requisitos previos

- Docker + Docker Compose.
- Python 3.11+.

### 1. Configurar entorno (.env)

En la raíz del repo (`desk-grade-ready`), crea un archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Revisa especialmente las variables de base de datos:

- `DB_HOST` (por defecto `localhost`)
- `DB_PORT` (por defecto `5432`)
- `DB_NAME` (por defecto `desk`)
- `DB_USER` (por defecto `desk`)
- `DB_PASSWORD` (por defecto `desk_pass`)

> Ahora `desk_grade/db.py` usa **exclusivamente** estas variables para construir el DSN.

### 2. Levantar la base de datos con Docker

Desde la carpeta `desk-grade-ready`:

```bash
docker compose up -d
```

Esto:

- Levanta `timescale/timescaledb:latest-pg14` con usuario `desk` / `desk_pass` y DB `desk`.
- Aplica automáticamente `infra/init.sql` en el arranque (todas las tablas y tipos).
- Levanta Grafana en `http://localhost:3000` (usuario/contraseña `admin`/`admin` por defecto).
- Configura automáticamente el datasource de PostgreSQL.
- Carga dashboards predefinidos para monitoreo del sistema.

Para ver logs:

```bash
docker compose logs -f db
```

### 3. Instalar dependencias de Python

Opcional pero recomendado: usar entorno virtual.

```bash
python -m venv .venv
.venv\Scripts\activate  # en Windows
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Inicializar la base de datos

Si es la primera vez o si las tablas no existen, ejecuta:

```bash
python -m scripts.init_db
```

Este script verifica si las tablas existen y ejecuta `infra/init.sql` si es necesario.

**Nota**: Si el contenedor de Docker se creó antes de montar `init.sql`, las tablas no se habrán creado automáticamente. En ese caso:
- Opción 1: Ejecuta `python -m scripts.init_db` (recomendado)
- Opción 2: Elimina el volumen y recrea: `docker compose down -v && docker compose up -d`

### 5. Ejecutar el ciclo de riesgo intradía (Risk Cycle)

Con la base de datos levantada y `.env` configurado:

```bash
python -m scripts.run_risk_cycle
```

Este script realiza:

1. **Exits**: procesa posibles salidas de trades abiertos según niveles/ATR.
2. **Journal**: actualiza `trade_journal` (R, MAE, MFE, pnl_r) y estados.
3. **Risk gates**: evalúa presupuestos de riesgo y actualiza `risk_state` / `risk_events`.
4. **Entries**: en modo PAPER, genera nuevas entradas a partir de `signals_live`.

Los logs se controlan con `LOG_LEVEL` en `.env`.

### 6. Poblar datos de prueba

Para que el ciclo haga algo útil, ejecuta el script de seeding:

```bash
python -m scripts.seed_data
```

Esto genera:
- Datos OHLCV sintéticos para varios símbolos (EURUSD, GBPUSD, AAPL, TSLA).
- Señales de ejemplo en `signals_live`.
- Balance inicial en `cash_balances`.
- Valores de ATR en `atr_cache`.

### 7. Scripts disponibles

#### Health Check
Verifica conectividad y estado del sistema:

```bash
python -m scripts.health_check
```

#### Status
Muestra estado actual (equity, posiciones, riesgo, trades abiertos):

```bash
python -m scripts.status
```

#### Scheduler
Ejecuta el ciclo de riesgo periódicamente (cada 5 minutos por defecto):

```bash
python -m scripts.scheduler
```

Puedes configurar el intervalo con `SCHEDULER_INTERVAL_MINUTES` en `.env`.

### 8. Ejecutar tests

```bash
pip install pytest
pytest tests/
```

### 9. Estructura de comandos (entry points)

Si instalas el paquete con `pip install -e .`, puedes usar:

```bash
desk-grade-risk-cycle    # Ejecuta un ciclo de riesgo
desk-grade-scheduler     # Inicia el scheduler
desk-grade-health        # Health check
desk-grade-status        # Estado del sistema
desk-grade-seed          # Poblar datos de prueba
```

### 10. Flujo completo de trabajo

1. **Inicio del sistema**:
   ```bash
   docker compose up -d
   python -m scripts.health_check
   python -m scripts.seed_data
   ```

2. **Ejecutar ciclo manualmente**:
   ```bash
   python -m scripts.run_risk_cycle
   ```

3. **Ver estado**:
   ```bash
   python -m scripts.status
   ```

4. **Ejecutar scheduler continuo**:
   ```bash
   python -m scripts.scheduler
   ```

### 11. Dashboards de Grafana

El sistema incluye dashboards preconfigurados en Grafana:

1. **Equity & PnL**: 
   - Equity curve en tiempo real
   - PnL diario y semanal
   - Drawdown gauge
   - Histórico de PnL

2. **Risk Monitoring**:
   - Estado de riesgo (NORMAL/DEGRADED/HALT)
   - Eventos de riesgo de las últimas 24h
   - Exposición por símbolo
   - Timeline de estados de riesgo

3. **Positions & Trades**:
   - Tabla de posiciones abiertas
   - Trades activos con niveles (stop, TP1, TP2)
   - PnL realizado vs no realizado
   - Eventos de trades

4. **Trade Metrics**:
   - Distribución de R-múltiples
   - Win rate y métricas promedio
   - MAE vs MFE
   - Trade journal completo

**Acceso**: `http://localhost:3000` (admin/admin)

**Nota**: Grafana está configurado en español por defecto. Después de levantar los contenedores, puede que necesites:
1. Reiniciar Grafana: `docker compose restart grafana` o `python -m scripts.restart_grafana`
2. Cambiar manualmente el idioma: Ve a tu perfil (icono de usuario arriba a la derecha) → Preferences → Language → Selecciona "Español"
3. Los dashboards que creamos ya están traducidos al español

**Importante**: Algunos elementos de la interfaz de Grafana pueden seguir en inglés si la versión no tiene traducción completa. Los dashboards personalizados sí están en español.

Los dashboards se cargan automáticamente al iniciar Grafana.

### 12. Troubleshooting

#### Error: "relation does not exist" o tablas faltantes

Si ves errores como `relation "cash_balances" does not exist`:

1. **Ejecuta el script de inicialización**:
   ```bash
   python -m scripts.init_db
   ```

2. **Si eso no funciona, resetea la base de datos**:
   ```bash
   python -m scripts.reset_db  # ADVERTENCIA: elimina todos los datos
   python -m scripts.init_db
   ```

3. **O recrea el contenedor desde cero**:
   ```bash
   docker compose down -v  # Elimina volúmenes
   docker compose up -d     # Recrea todo
   python -m scripts.init_db
   ```

#### Error de conexión a base de datos

- Verifica que Docker esté corriendo: `docker ps`
- Verifica que el contenedor esté activo: `docker compose ps`
- Revisa logs: `docker compose logs db`
- Verifica credenciales en `.env`

### 13. Ingesta de Datos Reales

El sistema ahora soporta múltiples fuentes de datos reales:

#### Fuentes Disponibles

1. **QuantConnect/Lean** (recomendado para datos históricos)
   ```bash
   # Configurar en .env:
   QC_DATA_PATH=C:/Lean/Data  # o QC_USER_ID + QC_API_KEY
   
   # Ingerir datos:
   python -m scripts.ingest_from_qc --symbols AAPL,TSLA --timeframe 1d --asset USA_STOCK
   ```

2. **Interactive Brokers (IBKR)**
   ```bash
   # Requiere TWS/IB Gateway corriendo
   # Configurar en .env:
   IBKR_HOST=127.0.0.1
   IBKR_PORT=7497  # paper: 7497, live: 4001
   
   # Ingerir datos:
   python -m scripts.ingest_from_ibkr --symbols EURUSD,GBPUSD --timeframe 1h --days 30
   ```

3. **TradingView** (CSV export)
   ```bash
   # Exportar datos desde Pine Script, luego:
   python -m data_pipeline.cli.ingest_ohlcv --provider tradingview --symbols AAPL --timeframe 1d --asset USA_STOCK
   ```

4. **CSV** (desarrollo/testing)
   ```bash
   python -m data_pipeline.cli.ingest_ohlcv --provider csv --path data.csv --symbols AAPL --timeframe 1d --asset USA_STOCK
   ```

Ver `data_pipeline/README.md` para documentación completa.

### 14. Próximos pasos / Extensión

- **Integración con Colibrí**: El scheduler básico puede ser reemplazado por Colibrí como scheduler externo.
- **Backtesting**: Añadir capacidades de backtesting sobre datos históricos (ya tienes datos reales disponibles).
- **Broker integration**: Conectar con brokers reales para trading en vivo (actualmente solo paper trading).

### 11. Documentación adicional

- Ver `C:\Users\PcVIP\Downloads\desk-grade-documentation\` para documentación detallada.
- Ver `C:\Users\PcVIP\Downloads\desk-grade-missing-docs\` para requisitos funcionales y casos de uso.

