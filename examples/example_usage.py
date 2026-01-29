"""
Ejemplo de uso programático del sistema Desk-Grade.

Este script muestra cómo usar los módulos principales del sistema
desde código Python.
"""

from datetime import datetime, timezone

from desk_grade import api
from portfolio.exit_engine import ExitEngine
from portfolio.lifecycle_engine import LifecycleEngine
from portfolio.order_builder import build_order_intent
from portfolio.risk_layer import RiskEngine


def example_risk_engine() -> None:
    """Ejemplo de uso del motor de riesgo."""
    print("=== Ejemplo: Risk Engine ===")

    engine = RiskEngine()

    # Evaluar gates de riesgo
    result = engine.evaluate_gates(
        equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=-100.0,
        weekly_pnl=-200.0,
    )

    print(f"Modo de riesgo: {result.mode}")
    print(f"Razones: {result.reasons}")

    # Calcular tamaño de posición
    size = engine.compute_position_size(
        symbol="EURUSD",
        price=1.10,
        equity=10000.0,
        atr=0.005,
    )
    print(f"Tamaño de posición recomendado: {size}")


def example_lifecycle_engine() -> None:
    """Ejemplo de uso del motor de lifecycle."""
    print("\n=== Ejemplo: Lifecycle Engine ===")

    lifecycle = LifecycleEngine(cooldown_minutes=5)

    # Registrar una entrada
    lifecycle.register_entry(
        symbol="EURUSD",
        strategy_id="baseline",
        qty=1000.0,
        entry_price=1.10,
        stop_price=1.095,
        tp1_price=1.105,
        tp2_price=1.11,
    )

    print("Entrada registrada para EURUSD")

    # Verificar cooldown
    in_cooldown = lifecycle.is_in_cooldown("EURUSD", "baseline")
    print(f"En cooldown: {in_cooldown}")


def example_exit_engine() -> None:
    """Ejemplo de uso del motor de salidas."""
    print("\n=== Ejemplo: Exit Engine ===")

    exit_engine = ExitEngine()

    # Procesar salida para un trade
    exit_engine.process_trade_exit(
        symbol="EURUSD",
        strategy_id="baseline",
        current_price=1.105,
        atr=0.005,
    )

    print("Salida procesada para EURUSD")


def example_order_builder() -> None:
    """Ejemplo de construcción de órdenes."""
    print("\n=== Ejemplo: Order Builder ===")

    # Construir intención de orden
    intent = build_order_intent(
        symbol="EURUSD",
        target_qty=1000.0,
        current_qty=0.0,
        price=1.10,
        strategy_id="baseline",
        reason="NUEVA_ENTRADA",
    )

    if intent:
        print(f"Orden generada: {intent.side} {intent.qty} {intent.symbol} @ {intent.price}")
    else:
        print("No se requiere orden (target_qty == current_qty)")


def example_database_queries() -> None:
    """Ejemplo de consultas a la base de datos."""
    print("\n=== Ejemplo: Database Queries ===")

    # Obtener posiciones abiertas
    positions = api.fetch_all(
        """
        SELECT symbol, qty, avg_price, realized_pnl
        FROM positions
        WHERE qty != 0
        """
    )

    print(f"Posiciones abiertas: {len(positions)}")
    for pos in positions:
        print(f"  {pos['symbol']}: qty={pos['qty']} avg={pos['avg_price']}")

    # Obtener último estado de riesgo
    risk_state = api.fetch_one(
        """
        SELECT mode, reason, daily_pnl, weekly_pnl
        FROM risk_state
        ORDER BY ts DESC
        LIMIT 1
        """
    )

    if risk_state:
        print(f"\nEstado de riesgo:")
        print(f"  Modo: {risk_state['mode']}")
        print(f"  PnL diario: {risk_state['daily_pnl']}")
        print(f"  PnL semanal: {risk_state['weekly_pnl']}")


def main() -> None:
    """Función principal del ejemplo."""
    print("Ejemplos de uso del sistema Desk-Grade\n")
    print("=" * 50)

    try:
        example_risk_engine()
        example_lifecycle_engine()
        example_exit_engine()
        example_order_builder()
        example_database_queries()

        print("\n" + "=" * 50)
        print("Ejemplos completados exitosamente")
    except Exception as e:
        print(f"\nError ejecutando ejemplos: {e}")
        print("Asegúrate de que:")
        print("  1. La base de datos esté corriendo (docker compose up -d)")
        print("  2. Los datos estén poblados (python -m scripts.seed_data)")
        print("  3. El archivo .env esté configurado correctamente")


if __name__ == "__main__":
    main()
