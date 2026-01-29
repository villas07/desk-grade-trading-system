# Changelog

## [0.1.0] - 2026-01-28

### Añadido
- Sistema completo de gestión de riesgo de trading
- Módulo `desk_grade` con acceso a base de datos y API interna
- Módulo `portfolio` con motores de riesgo, lifecycle y exits
- Script `run_risk_cycle.py` para ejecutar ciclos intradía completos
- Script `scheduler.py` para ejecución periódica automática
- Script `seed_data.py` para poblar datos de prueba
- Script `health_check.py` para verificación del sistema
- Script `status.py` para mostrar estado actual
- Tests unitarios básicos para métricas y riesgo
- Configuración centralizada con variables de entorno
- Sistema de logging estructurado
- Docker Compose con PostgreSQL + TimescaleDB y Grafana
- Esquema completo de base de datos con todas las tablas necesarias
- Documentación completa en README.md
- pyproject.toml para gestión del proyecto
- .gitignore para Python/Docker

### Características principales
- Paper trading funcional
- Gates de riesgo (drawdown, pérdidas diaria/semanal, sector caps)
- Position sizing (fixed fractional y ATR-based)
- Vol targeting
- Lifecycle completo de trades (FLAT → ENTERED → MANAGED → EXITED)
- Motor de salidas con stops, TPs y trailing stops
- Trade journal con métricas R, MAE, MFE
- Cooldown tras salidas
- Exposure snapshots
- Risk state tracking
