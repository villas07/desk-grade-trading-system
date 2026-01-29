# Grafana Dashboards - Desk-Grade

Este directorio contiene la configuración y dashboards de Grafana para el sistema Desk-Grade.

## Estructura

```
grafana/
├── provisioning/
│   ├── datasources/
│   │   └── postgres.yml          # Configuración del datasource PostgreSQL
│   └── dashboards/
│       └── default.yml            # Configuración de carga automática de dashboards
├── dashboards/
│   ├── equity_and_pnl.json       # Dashboard de equity y PnL
│   ├── risk_monitoring.json      # Dashboard de monitoreo de riesgo
│   ├── positions.json            # Dashboard de posiciones y trades
│   └── trade_metrics.json         # Dashboard de métricas de trades
└── README.md                      # Este archivo
```

## Configuración Automática

Cuando levantas Grafana con `docker compose up -d`, se configura automáticamente:

1. **Datasource PostgreSQL**: Se conecta a la base de datos `desk` en el contenedor `db`
2. **Dashboards**: Se cargan automáticamente desde `grafana/dashboards/`

## Dashboards Disponibles

### 1. Equity & PnL

Visualiza el rendimiento del sistema:
- **Equity Curve**: Evolución del balance en el tiempo
- **PnL Diario**: PnL del día actual
- **PnL Semanal**: PnL de la última semana
- **Drawdown %**: Porcentaje de drawdown actual
- **PnL Diario Histórico**: Histórico de PnL diario

### 2. Risk Monitoring

Monitoreo de riesgo en tiempo real:
- **Risk Mode**: Estado actual (NORMAL/DEGRADED/HALT)
- **Risk Events**: Eventos de riesgo de las últimas 24 horas
- **Exposure por Símbolo**: Exposición neta por activo
- **Risk State Timeline**: Evolución del estado de riesgo en el tiempo

### 3. Positions & Trades

Gestión de posiciones y trades:
- **Posiciones Abiertas**: Tabla con todas las posiciones activas
- **Trades Abiertos**: Trades en estado ENTERED o MANAGED con niveles
- **PnL Realizado vs No Realizado**: Comparación temporal
- **Trade Events**: Log de eventos de trades de las últimas 24h

### 4. Trade Metrics

Métricas de rendimiento de trades:
- **R-Multiple Distribution**: Histograma de R-múltiples
- **Win Rate**: Porcentaje de trades ganadores
- **Avg R-Multiple**: Promedio de R-múltiples
- **Total Trades**: Número total de trades cerrados
- **MAE vs MFE**: Comparación de Maximum Adverse/Favorable Excursion
- **Trade Journal**: Tabla completa con todos los trades cerrados

## Acceso

1. Levanta los servicios:
   ```bash
   docker compose up -d
   ```

2. Accede a Grafana:
   - URL: `http://localhost:3000`
   - Usuario: `admin`
   - Contraseña: `admin`

3. Los dashboards aparecen automáticamente en el menú lateral.

## Personalización

### Modificar Dashboards

Los dashboards están en formato JSON. Puedes:

1. Editar los archivos JSON directamente
2. O modificar desde la UI de Grafana (los cambios se guardan en la base de datos de Grafana)

### Añadir Nuevos Dashboards

1. Crea un nuevo archivo JSON en `grafana/dashboards/`
2. Reinicia Grafana: `docker compose restart grafana`
3. El nuevo dashboard aparecerá automáticamente

### Configurar Datasource Manualmente

Si necesitas configurar el datasource manualmente:

1. Ve a Configuration → Data Sources
2. Añade PostgreSQL con:
   - Host: `db:5432`
   - Database: `desk`
   - User: `desk`
   - Password: `desk_pass`
   - SSL Mode: `disable`

## Troubleshooting

### Dashboards no aparecen

- Verifica que los volúmenes estén montados correctamente en `docker-compose.yml`
- Revisa logs: `docker compose logs grafana`
- Verifica permisos de los archivos JSON

### Datasource no conecta

- Verifica que el contenedor `db` esté corriendo: `docker compose ps`
- Verifica credenciales en `grafana/provisioning/datasources/postgres.yml`
- Prueba la conexión desde la UI de Grafana

### Datos no aparecen

- Asegúrate de que haya datos en la base de datos (ejecuta `python -m scripts.seed_data`)
- Verifica que las queries SQL en los dashboards sean correctas
- Revisa que el formato de tiempo sea correcto (Grafana espera timestamps)

## Referencias

- [Documentación de Grafana](https://grafana.com/docs/grafana/latest/)
- [PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Dashboard JSON Model](https://grafana.com/docs/grafana/latest/dashboards/json-model/)
