# Guía Completa - Sistema Desk-Grade

Esta guía te explica paso a paso cómo usar el sistema completo y qué puedes hacer con él.

## 📋 Tabla de Contenidos

1. [Configuración Inicial](#configuración-inicial)
2. [Uso de Grafana](#uso-de-grafana)
3. [Scripts Disponibles](#scripts-disponibles)
4. [Flujos de Trabajo](#flujos-de-trabajo)
5. [Qué Puedes Hacer con el Sistema](#qué-puedes-hacer)

---

## 🚀 Configuración Inicial

### Paso 1: Verificar Requisitos

```powershell
python setup.py
```

Esto verifica:
- ✅ Python 3.11+
- ✅ Docker instalado
- ✅ Docker Compose instalado
- ✅ Archivo .env existe
- ✅ Dependencias instaladas

### Paso 2: Configurar Variables de Entorno

```powershell
# Copia el archivo de ejemplo
cp .env.example .env

# Edita .env con tus credenciales si es necesario
# Por defecto usa:
# - DB_HOST=localhost
# - DB_PORT=5432
# - DB_NAME=desk
# - DB_USER=desk
# - DB_PASSWORD=desk_pass
```

### Paso 3: Levantar Infraestructura

```powershell
# Levanta PostgreSQL + TimescaleDB y Grafana
docker compose up -d

# Verifica que estén corriendo
docker compose ps

# Ver logs si hay problemas
docker compose logs -f db
docker compose logs -f grafana
```

### Paso 4: Inicializar Base de Datos

```powershell
# Crea todas las tablas necesarias
python -m scripts.init_db

# Verifica que todo esté bien
python -m scripts.health_check
```

### Paso 5: Instalar Dependencias Python

```powershell
# Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 6: Poblar Datos Iniciales

```powershell
# Genera datos de prueba (OHLCV, señales, balances)
python -m scripts.seed_data
```

---

## 📊 Uso de Grafana

### Paso 1: Acceder a Grafana

1. Abre tu navegador y ve a: `http://localhost:3000`
2. Usuario: `admin`
3. Contraseña: `admin`

### Paso 2: Cambiar Idioma a Español (Opcional)

1. Haz clic en el icono de usuario (arriba a la derecha)
2. Selecciona **"Preferences"** o **"Preferencias"**
3. En **"Language"** o **"Idioma"**, selecciona **"Español"**
4. Haz clic en **"Save"** o **"Guardar"**

### Paso 3: Verificar Datasource

1. Ve a **Configuration** → **Data Sources** (o **Configuración** → **Fuentes de datos**)
2. Deberías ver **"PostgreSQL Desk-Grade"** configurado
3. Haz clic en él y luego **"Save & Test"** para verificar conexión
4. Deberías ver un mensaje verde: **"Data source is working"**

### Paso 4: Explorar Dashboards

Los dashboards se cargan automáticamente. En el menú lateral:

1. **Dashboards** → **Browse** (o **Explorar**)
2. Verás 4 dashboards:
   - **Equity y PnL**: Evolución del balance y ganancias/pérdidas
   - **Monitoreo de Riesgo**: Estado de riesgo, eventos, exposición
   - **Posiciones y Trades**: Posiciones abiertas, trades activos
   - **Métricas de Trades**: Estadísticas de rendimiento

### Paso 5: Usar los Dashboards

**Para ver datos en tiempo real:**

1. Ejecuta el ciclo de riesgo desde PowerShell:
   ```powershell
   python -m scripts.run_risk_cycle
   ```

2. Los dashboards se actualizan automáticamente cada 10-30 segundos

3. Puedes hacer clic en el icono de refresh (↻) para actualizar manualmente

**Personalizar dashboards:**

- Haz clic en el icono de engranaje (⚙️) en cualquier dashboard
- Selecciona **"Edit"** o **"Editar"**
- Puedes modificar paneles, añadir nuevos, cambiar queries SQL
- Guarda los cambios con **"Save"**

---

## 🛠️ Scripts Disponibles

### Scripts Principales

#### 1. `init_db.py` - Inicializar Base de Datos
```powershell
python -m scripts.init_db
```
**Qué hace**: Crea todas las tablas si no existen
**Cuándo usar**: Primera vez o si faltan tablas

#### 2. `seed_data.py` - Poblar Datos de Prueba
```powershell
python -m scripts.seed_data
```
**Qué hace**: Genera datos sintéticos (OHLCV, señales, balances)
**Cuándo usar**: Para tener datos de prueba y ver los dashboards funcionando

#### 3. `run_risk_cycle.py` - Ejecutar Ciclo de Riesgo
```powershell
python -m scripts.run_risk_cycle
```
**Qué hace**: 
- Procesa salidas de trades abiertos
- Actualiza trade journal (R, MAE, MFE)
- Evalúa gates de riesgo
- Genera nuevas entradas (en modo PAPER)
**Cuándo usar**: Regularmente (cada 5-15 minutos) para mantener el sistema actualizado

#### 4. `scheduler.py` - Scheduler Automático
```powershell
python -m scripts.scheduler
```
**Qué hace**: Ejecuta `run_risk_cycle` automáticamente cada N minutos
**Cuándo usar**: Para automatizar completamente el sistema
**Configuración**: Variable `SCHEDULER_INTERVAL_MINUTES` en `.env` (default: 5 minutos)

#### 5. `health_check.py` - Verificar Salud del Sistema
```powershell
python -m scripts.health_check
```
**Qué hace**: Verifica conectividad con BD y existencia de tablas
**Cuándo usar**: Cuando algo no funciona o para diagnóstico

#### 6. `status.py` - Ver Estado Actual
```powershell
python -m scripts.status
```
**Qué hace**: Muestra equity, riesgo, posiciones y trades abiertos en consola
**Cuándo usar**: Para ver un resumen rápido sin abrir Grafana

#### 7. `reset_db.py` - Resetear Base de Datos
```powershell
python -m scripts.reset_db
```
**⚠️ ADVERTENCIA**: Elimina TODOS los datos
**Cuándo usar**: Solo si quieres empezar desde cero

#### 8. `restart_grafana.py` - Reiniciar Grafana
```powershell
python -m scripts.restart_grafana
```
**Qué hace**: Reinicia el contenedor de Grafana
**Cuándo usar**: Después de cambiar configuración o si Grafana no responde

---

## 🔄 Flujos de Trabajo

### Flujo 1: Setup Inicial Completo

```powershell
# 1. Verificar entorno
python setup.py

# 2. Configurar .env
cp .env.example .env

# 3. Levantar Docker
docker compose up -d

# 4. Inicializar BD
python -m scripts.init_db

# 5. Verificar salud
python -m scripts.health_check

# 6. Instalar dependencias
pip install -r requirements.txt

# 7. Poblar datos
python -m scripts.seed_data

# 8. Ejecutar primer ciclo
python -m scripts.run_risk_cycle

# 9. Ver estado
python -m scripts.status

# 10. Abrir Grafana
# http://localhost:3000 (admin/admin)
```

### Flujo 2: Operación Diaria Normal

```powershell
# 1. Verificar que Docker esté corriendo
docker compose ps

# 2. Ver estado actual
python -m scripts.status

# 3. Ejecutar ciclo de riesgo manualmente
python -m scripts.run_risk_cycle

# 4. Revisar dashboards en Grafana
# http://localhost:3000
```

### Flujo 3: Operación Automatizada

```powershell
# 1. Iniciar scheduler (ejecuta ciclos automáticamente)
python -m scripts.scheduler

# Esto ejecutará run_risk_cycle cada 5 minutos (configurable)
# Deja corriendo en una terminal

# 2. Monitorear en Grafana
# Los dashboards se actualizan automáticamente
```

### Flujo 4: Desarrollo/Testing

```powershell
# 1. Resetear datos si es necesario
python -m scripts.reset_db  # ⚠️ Elimina todo
python -m scripts.init_db

# 2. Poblar datos de prueba
python -m scripts.seed_data

# 3. Ejecutar ciclo múltiples veces para generar datos
python -m scripts.run_risk_cycle
python -m scripts.run_risk_cycle
python -m scripts.run_risk_cycle

# 4. Ver resultados en Grafana y consola
python -m scripts.status
```

---

## 🎯 Qué Puedes Hacer con el Sistema

### 1. **Paper Trading Completo**

El sistema está diseñado para trading en modo papel (simulación):

- ✅ Ejecuta trades automáticamente basados en señales
- ✅ Gestiona riesgo en tiempo real
- ✅ Calcula PnL realizado y no realizado
- ✅ Registra todos los trades en journal
- ✅ No requiere conexión a broker real

**Cómo funciona:**
- Las señales en `signals_live` generan trades automáticamente
- Los trades se ejecutan instantáneamente al precio de mercado
- Las posiciones se actualizan automáticamente
- El sistema respeta los gates de riesgo

### 2. **Gestión de Riesgo Profesional**

El sistema implementa múltiples capas de gestión de riesgo:

**Gates de Riesgo:**
- Drawdown máximo (configurable en `.env`)
- Límite de pérdida diaria
- Límite de pérdida semanal
- Límites de exposición por sector
- Flags de correlación y reconciliación

**Position Sizing:**
- Fixed fractional (arriesga % fijo del equity)
- ATR-based (dimensiona según volatilidad)
- Vol targeting (ajusta según volatilidad objetivo)

**Estados de Riesgo:**
- **NORMAL**: Trading normal permitido
- **DEGRADED**: Solo reducción de riesgo
- **HALT**: Trading detenido

### 3. **Monitoreo en Tiempo Real con Grafana**

**Dashboards disponibles:**

1. **Equity y PnL**
   - Curva de equity en tiempo real
   - PnL diario y semanal
   - Drawdown porcentual
   - Histórico de PnL

2. **Monitoreo de Riesgo**
   - Estado actual (NORMAL/DEGRADADO/DETENIDO)
   - Eventos de riesgo de las últimas 24h
   - Exposición por símbolo
   - Timeline de estados de riesgo

3. **Posiciones y Trades**
   - Tabla de posiciones abiertas
   - Trades activos con niveles (stop, TP1, TP2)
   - PnL realizado vs no realizado
   - Log de eventos de trades

4. **Métricas de Trades**
   - Distribución de R-múltiples
   - Tasa de éxito (win rate)
   - R-múltiple promedio
   - MAE vs MFE
   - Diario completo de trades

### 4. **Análisis de Rendimiento**

El sistema calcula automáticamente:

- **R-Múltiples**: Mide ganancias/pérdidas en unidades de riesgo
- **MAE (Maximum Adverse Excursion)**: Peor movimiento en contra
- **MFE (Maximum Favourable Excursion)**: Mejor movimiento a favor
- **PnL Realizado**: Ganancias/pérdidas de trades cerrados
- **PnL No Realizado**: Ganancias/pérdidas de posiciones abiertas
- **Win Rate**: Porcentaje de trades ganadores
- **Expectancy**: R promedio esperado

### 5. **Lifecycle Completo de Trades**

El sistema gestiona el ciclo completo:

- **FLAT** → Sin posición
- **ENTERED** → Entrada ejecutada
- **MANAGED** → Toma parcial de beneficios (TP1)
- **EXITED** → Salida completa

**Características:**
- Stops automáticos basados en ATR
- Take profits en 1R y 2R
- Trailing stops
- Cooldown después de salidas

### 6. **Integración con Datos Externos**

Puedes integrar el sistema con:

- **APIs de datos de mercado**: Para poblar `ohlcv` automáticamente
- **Sistemas de señales**: Para insertar en `signals_live`
- **Brokers reales**: Modificando el código de ejecución (actualmente solo PAPER)
- **Colibrí**: Como scheduler externo (reemplazando `scheduler.py`)

### 7. **Backtesting y Análisis Histórico**

Con datos históricos en `ohlcv` puedes:

- Analizar rendimiento pasado
- Ver distribuciones de R-múltiples
- Evaluar estrategias
- Optimizar parámetros de riesgo

### 8. **Extensión y Personalización**

El código está estructurado para ser fácilmente extensible:

- **Añadir nuevos tipos de señales**: Modifica `signals_live` y lógica de entrada
- **Nuevos tipos de salida**: Extiende `exits.py` y `exit_engine.py`
- **Métricas personalizadas**: Añade funciones en `metrics.py` o `advanced_metrics.py`
- **Nuevos dashboards**: Crea JSON en `grafana/dashboards/`
- **Integraciones**: Conecta con APIs externas en `scripts/`

---

## 📚 Estructura del Repositorio

```
desk-grade-ready/
├── desk_grade/          # Core del sistema (DB, API, config)
├── portfolio/           # Lógica de negocio (riesgo, lifecycle, exits)
├── scripts/             # Scripts ejecutables
├── tests/               # Tests unitarios
├── grafana/             # Configuración y dashboards de Grafana
├── infra/               # Esquema de base de datos
├── examples/            # Ejemplos de uso programático
├── docker-compose.yml   # Infraestructura Docker
├── requirements.txt     # Dependencias Python
└── README.md           # Documentación principal
```

---

## 🔍 Troubleshooting Común

### Grafana no muestra datos

1. Verifica que haya datos: `python -m scripts.status`
2. Ejecuta ciclo de riesgo: `python -m scripts.run_risk_cycle`
3. Verifica datasource en Grafana: Configuration → Data Sources
4. Revisa logs: `docker compose logs grafana`

### Error "tabla no existe"

```powershell
python -m scripts.init_db
```

### Docker no inicia

```powershell
# Ver logs
docker compose logs

# Reiniciar todo
docker compose down
docker compose up -d
```

### Scripts no encuentran módulos

```powershell
# Asegúrate de estar en el directorio correcto
cd "C:\DESK-GRADE SYSTEM (Cursor)\desk-grade-ready"

# Verifica que las dependencias estén instaladas
pip install -r requirements.txt
```

---

## 🎓 Próximos Pasos

1. **Explorar los dashboards** en Grafana
2. **Ejecutar múltiples ciclos** para generar datos históricos
3. **Personalizar parámetros de riesgo** en `.env`
4. **Crear tus propias señales** insertando en `signals_live`
5. **Extender el sistema** según tus necesidades

---

## 📖 Documentación Adicional

- `README.md` - Documentación principal
- `QUICKSTART.md` - Guía rápida de inicio
- `DASHBOARD_GUIDE.md` - Guía detallada de dashboards
- `CONTRIBUTING.md` - Guía para contribuir
- `grafana/README.md` - Documentación de Grafana

---

¡El sistema está listo para usar! 🚀
