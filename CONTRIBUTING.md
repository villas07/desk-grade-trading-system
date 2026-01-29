# Guía de Contribución

## Estructura del Código

### Módulos principales

- **`desk_grade/`**: Core del sistema (DB, API, config, logging)
- **`portfolio/`**: Lógica de negocio (riesgo, lifecycle, exits, métricas)
- **`scripts/`**: Scripts ejecutables (risk cycle, scheduler, utilidades)
- **`tests/`**: Tests unitarios

## Convenciones

- **Python 3.11+**: Requerido
- **Type hints**: Usar type hints en todas las funciones públicas
- **Docstrings**: Documentar funciones y clases principales
- **Logging**: Usar el módulo `desk_grade.logging_config` para logging consistente

## Desarrollo

### Setup del entorno

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -e ".[dev]"  # Instalar dependencias de desarrollo
```

### Ejecutar tests

```bash
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/ --cov=desk_grade --cov=portfolio  # Con coverage
```

### Formateo de código

```bash
black .
ruff check --fix .
```

## Flujo de trabajo

1. Crear una rama para tu feature/fix
2. Hacer cambios y añadir tests si es necesario
3. Ejecutar tests y verificar que pasan
4. Formatear código con black/ruff
5. Crear pull request

## Testing

- Tests unitarios en `tests/`
- Cada módulo debe tener tests correspondientes
- Usar fixtures de pytest para datos de prueba
- Mockear acceso a base de datos cuando sea necesario

## Logging

Usar niveles apropiados:
- `DEBUG`: Información detallada para debugging
- `INFO`: Eventos normales del sistema
- `WARNING`: Situaciones que requieren atención pero no son errores
- `ERROR`: Errores que no detienen el sistema
- `CRITICAL`: Errores que detienen el sistema

## Base de datos

- Todas las queries deben usar `desk_grade.api` (execute, fetch_one, fetch_all)
- No hacer queries directas con psycopg
- Usar parámetros en queries (nunca string formatting directo)
- Las transacciones se manejan automáticamente con `db_session()`
