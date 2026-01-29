# Guía de Dashboards - Qué Ver en Cada Panel

Esta guía explica qué información deberías ver en cada dashboard de Grafana y qué datos necesitas tener en la base de datos.

## 📊 Dashboard 1: Equity & PnL

### Panel: Equity Curve (Gráfico de línea)
**Qué muestra**: Evolución del balance de tu cuenta en el tiempo
**Datos necesarios**: Registros en la tabla `cash_balances`
**Qué verás**:
- Una línea que muestra cómo cambia tu balance (equity) a lo largo del tiempo
- Si ejecutaste `seed_data.py`, verás un punto inicial de $10,000
- Cada vez que se ejecuta el ciclo de riesgo y hay cambios en el balance, aparecerán nuevos puntos

**Si está vacío**: Ejecuta `python -m scripts.seed_data` para crear un balance inicial

### Panel: PnL Diario (Número grande)
**Qué muestra**: Ganancia o pérdida del día actual
**Datos necesarios**: Registro en `risk_state` con `daily_pnl`
**Qué verás**:
- Un número grande que puede ser:
  - Verde si es positivo (ganancia)
  - Rojo si es negativo (pérdida)
- Se actualiza cada vez que se ejecuta el ciclo de riesgo

**Si muestra 0 o está vacío**: Ejecuta `python -m scripts.run_risk_cycle` para generar datos de riesgo

### Panel: PnL Semanal (Número grande)
**Qué muestra**: Ganancia o pérdida de la última semana
**Datos necesarios**: Registro en `risk_state` con `weekly_pnl`
**Qué verás**: Similar al PnL diario pero para el período semanal

### Panel: Drawdown % (Gauge circular)
**Qué muestra**: Porcentaje de pérdida desde el pico máximo
**Datos necesarios**: Registro en `risk_state` con `dd_pct`
**Qué verás**:
- Un medidor circular que muestra:
  - Verde: 0-10% drawdown (normal)
  - Amarillo: 10-20% drawdown (atención)
  - Rojo: >20% drawdown (crítico)

### Panel: PnL Diario Histórico (Gráfico de barras)
**Qué muestra**: Histórico de PnL diario día por día
**Datos necesarios**: Múltiples registros en `risk_state`
**Qué verás**: Barras verdes (ganancias) o rojas (pérdidas) por día

---

## 🚨 Dashboard 2: Risk Monitoring

### Panel: Risk Mode (Estado)
**Qué muestra**: Modo de operación actual del sistema
**Datos necesarios**: Último registro en `risk_state`
**Qué verás**:
- **NORMAL** (verde): Sistema operando normalmente, se permiten nuevas entradas
- **DEGRADED** (amarillo): Solo reducción de riesgo, sin nuevas entradas agresivas
- **HALT** (rojo): Trading detenido, no se permite incrementar riesgo

**Cómo se genera**: Se calcula automáticamente en `run_risk_cycle.py` evaluando:
- Drawdown máximo
- Límites de pérdida diaria/semanal
- Flags de correlación y reconciliación
- Límites de exposición por sector

### Panel: Risk Events (Tabla)
**Qué muestra**: Eventos de riesgo de las últimas 24 horas
**Datos necesarios**: Registros en `risk_events`
**Qué verás**:
- Lista de eventos como:
  - `RISK_GATES_EVALUATED`
  - `MAX_DRAWDOWN_SUPERADO`
  - `DAILY_LOSS_LIMIT_SUPERADO`
- Con timestamp, severidad (INFO/WARN/ERROR) y descripción

**Si está vacío**: Ejecuta `python -m scripts.run_risk_cycle` para generar eventos

### Panel: Exposure por Símbolo (Gráfico de barras)
**Qué muestra**: Exposición neta por cada activo/símbolo
**Datos necesarios**: Registros en `exposure_snapshots`
**Qué verás**:
- Barras horizontales mostrando exposición positiva (long) o negativa (short)
- Cada barra representa un símbolo diferente (EURUSD, AAPL, etc.)

**Cómo se genera**: Se crea automáticamente cuando hay posiciones abiertas

### Panel: Risk State Timeline (Gráfico de línea)
**Qué muestra**: Evolución del estado de riesgo en el tiempo
**Datos necesarios**: Histórico en `risk_state`
**Qué verás**:
- Línea que muestra:
  - 0 = NORMAL (verde)
  - 1 = DEGRADED (amarillo)
  - 2 = HALT (rojo)
- Permite ver cuándo y por cuánto tiempo el sistema estuvo en cada modo

---

## 💼 Dashboard 3: Positions & Trades

### Panel: Posiciones Abiertas (Tabla)
**Qué muestra**: Todas las posiciones activas en tu cuenta
**Datos necesarios**: Registros en `positions` donde `qty != 0`
**Qué verás**:
- Columnas: símbolo, cantidad (qty), precio promedio (avg_price), PnL realizado, PnL no realizado
- Una fila por cada símbolo con posición abierta

**Si está vacío**: No hay posiciones abiertas. Ejecuta el ciclo de riesgo con señales activas para generar posiciones.

### Panel: Trades Abiertos (Tabla)
**Qué muestra**: Trades en estado ENTERED o MANAGED
**Datos necesarios**: Registros en `trade_state` con estado 'ENTERED' o 'MANAGED'
**Qué verás**:
- Símbolo, estrategia, estado, cantidad, precio de entrada
- Niveles: stop_price, tp1_price, tp2_price
- Útil para ver trades activos y sus niveles de salida

**Si está vacío**: No hay trades activos. El sistema necesita señales en `signals_live` para crear trades.

### Panel: PnL Realizado vs No Realizado (Gráfico de líneas)
**Qué muestra**: Comparación entre ganancias/pérdidas realizadas y no realizadas
**Datos necesarios**: Histórico en `positions`
**Qué verás**:
- Dos líneas:
  - Realized PnL: ganancias/pérdidas de trades cerrados
  - Unrealized PnL: ganancias/pérdidas de posiciones abiertas (fluctúa con el precio)

### Panel: Trade Events (Log)
**Qué muestra**: Log de eventos de trades de las últimas 24 horas
**Datos necesarios**: Registros en `trade_events`
**Qué verás**:
- Eventos como:
  - `ENTERED`: Nueva entrada
  - `STOP`: Salida por stop loss
  - `TP1_PARTIAL`: Toma parcial de beneficios
  - `TP2_FULL`: Salida completa por TP2
  - `TRAIL_STOP`: Salida por trailing stop

---

## 📈 Dashboard 4: Trade Metrics

### Panel: R-Multiple Distribution (Histograma)
**Qué muestra**: Distribución de los R-múltiples de trades cerrados
**Datos necesarios**: Registros en `trade_journal` con campo `r`
**Qué verás**:
- Histograma mostrando cuántos trades tuvieron cada valor de R
- Ejemplo: muchos trades con R=1.0 significa que muchos trades ganaron exactamente 1R
- Útil para evaluar la distribución de resultados

**Si está vacío**: No hay trades cerrados aún. Necesitas ejecutar el ciclo de riesgo y que algunos trades se cierren.

### Panel: Win Rate (Porcentaje)
**Qué muestra**: Porcentaje de trades ganadores
**Datos necesarios**: Trades en `trade_journal` donde `r > 0`
**Qué verás**:
- Un porcentaje:
  - Verde si >50% (bueno)
  - Amarillo si 40-50% (aceptable)
  - Rojo si <40% (necesita mejora)

### Panel: Avg R-Multiple (Promedio)
**Qué muestra**: Promedio de R-múltiples de todos los trades
**Datos necesarios**: Promedio de `r` en `trade_journal`
**Qué verás**:
- Un número que indica el R promedio
- >1.0 es bueno (ganas más de 1R por trade en promedio)
- <1.0 significa que las pérdidas son mayores que las ganancias promedio

### Panel: Total Trades (Contador)
**Qué muestra**: Número total de trades cerrados en los últimos 30 días
**Datos necesarios**: Conteo en `trade_journal`

### Panel: MAE vs MFE (Gráfico de líneas)
**Qué muestra**: Maximum Adverse Excursion vs Maximum Favourable Excursion
**Datos necesarios**: Campos `mae` y `mfe` en `trade_journal`
**Qué verás**:
- Dos líneas comparando:
  - MAE: Cuánto se movió el precio en contra antes de cerrar
  - MFE: Cuánto se movió el precio a favor antes de cerrar
- Útil para evaluar timing de entradas y salidas

### Panel: Trade Journal (Tabla completa)
**Qué muestra**: Todos los trades cerrados con sus métricas
**Datos necesarios**: Registros completos en `trade_journal`
**Qué verás**:
- Tabla con: símbolo, fechas de entrada/salida, precios, cantidad, R, pnl_r, MAE, MFE
- Útil para análisis detallado trade por trade

---

## 🔄 Flujo de Datos

Para que los dashboards muestren información completa, necesitas:

1. **Datos iniciales**:
   ```bash
   python -m scripts.seed_data
   ```
   Esto crea: cash_balances, ohlcv, signals_live, atr_cache

2. **Ejecutar ciclo de riesgo**:
   ```bash
   python -m scripts.run_risk_cycle
   ```
   Esto genera:
   - risk_state (con PnL diario/semanal, modo de riesgo)
   - risk_events
   - trade_state (trades abiertos)
   - positions (si hay entradas)
   - trade_journal (si hay trades cerrados)

3. **Ejecutar múltiples veces**:
   - Cada ejecución del ciclo actualiza los datos
   - Los dashboards se actualizan automáticamente cada 10-30 segundos

## 🎯 Qué Esperar al Inicio

**Inmediatamente después de `seed_data`**:
- ✅ Equity Curve: 1 punto en $10,000
- ✅ Cash balances visibles
- ❌ PnL: 0 (no hay trades aún)
- ❌ Risk state: vacío (necesita ciclo de riesgo)

**Después de ejecutar `run_risk_cycle` una vez**:
- ✅ Risk state creado (modo NORMAL, PnL = 0)
- ✅ Risk events visibles
- ✅ Si hay señales: trades abiertos y posiciones
- ❌ Trade journal: vacío (no hay trades cerrados aún)

**Después de múltiples ciclos con trades cerrados**:
- ✅ Trade journal con métricas
- ✅ Win rate, R promedio, distribución de R
- ✅ MAE/MFE visibles
- ✅ Histórico completo de equity y PnL

## 🐛 Troubleshooting

**Dashboard vacío o sin datos**:
1. Verifica que Grafana esté conectado a la base de datos (Configuration → Data Sources)
2. Ejecuta `python -m scripts.health_check` para verificar tablas
3. Ejecuta `python -m scripts.seed_data` para crear datos iniciales
4. Ejecuta `python -m scripts.run_risk_cycle` para generar datos de riesgo

**Errores en queries SQL**:
- Verifica que las tablas existan: `python -m scripts.init_db`
- Revisa logs de Grafana: `docker compose logs grafana`

**Datos no se actualizan**:
- Los dashboards se refrescan automáticamente cada 10-30s según configuración
- Verifica que el ciclo de riesgo se esté ejecutando periódicamente
- Usa el botón de refresh manual en Grafana
