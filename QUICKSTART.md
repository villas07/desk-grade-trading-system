# Quick Start Guide

Guía rápida para poner en marcha el sistema Desk-Grade en 5 minutos.

## Paso 1: Verificar requisitos

```bash
python setup.py
```

Esto verifica Python, Docker, dependencias, etc.

## Paso 2: Configurar entorno

```bash
cp .env.example .env
```

Edita `.env` si necesitas cambiar credenciales de base de datos.

## Paso 3: Levantar infraestructura

```bash
docker compose up -d
```

Espera unos segundos a que PostgreSQL arranque completamente.

## Paso 4: Inicializar base de datos

```bash
python -m scripts.init_db
```

Esto crea todas las tablas necesarias si no existen.

## Paso 5: Instalar dependencias Python

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Paso 6: Verificar salud del sistema

```bash
python -m scripts.health_check
```

Deberías ver todos los checks en verde.

## Paso 7: Poblar datos de prueba

```bash
python -m scripts.seed_data
```

Esto genera datos OHLCV, señales y balances iniciales.

## Paso 8: Ejecutar un ciclo de riesgo

```bash
python -m scripts.run_risk_cycle
```

Deberías ver logs del ciclo ejecutándose.

## Paso 9: Ver estado del sistema

```bash
python -m scripts.status
```

Muestra equity, posiciones, riesgo, etc.

## Paso 10: Ejecutar scheduler continuo (opcional)

```bash
python -m scripts.scheduler
```

Ejecuta ciclos automáticamente cada 5 minutos (configurable en `.env`).

## Acceder a Grafana Dashboard

Una vez levantado Docker, accede a:
- **URL**: `http://localhost:3000`
- **Usuario**: `admin`
- **Contraseña**: `admin`
- **Idioma**: Español (configurado por defecto)

Los dashboards se cargan automáticamente y muestran:
- **Equity y PnL**: Curva de equity, PnL diario/semanal, drawdown
- **Monitoreo de Riesgo**: Modo de riesgo, eventos, exposición, timeline
- **Posiciones y Trades**: Posiciones abiertas, trades activos, PnL realizado/no realizado
- **Métricas de Trades**: Distribución de R, tasa de éxito, MAE/MFE, diario completo

## Comandos útiles

- **Ver logs de Docker**: `docker compose logs -f db`
- **Ver logs de Grafana**: `docker compose logs -f grafana`
- **Detener Docker**: `docker compose down`
- **Reiniciar Docker**: `docker compose restart`
- **Ver estado**: `python -m scripts.status`
- **Health check**: `python -m scripts.health_check`

## Troubleshooting

### Error de conexión a base de datos
- Verifica que Docker esté corriendo: `docker ps`
- Verifica que el contenedor esté activo: `docker compose ps`
- Revisa logs: `docker compose logs db`

### Error "tabla no existe" o "relation does not exist"
- Ejecuta: `python -m scripts.init_db` para crear las tablas
- Si persiste, resetea la base de datos: `python -m scripts.reset_db` (¡elimina todos los datos!)
- O recrea el contenedor: `docker compose down -v && docker compose up -d`

### Dependencias faltantes
- Ejecuta: `pip install -r requirements.txt`
- Si usas entorno virtual, asegúrate de activarlo

## Siguiente paso

Lee el `README.md` completo para más detalles sobre arquitectura, configuración avanzada y extensión del sistema.
