"""
Script de setup rápido para verificar el entorno y configurar el sistema.

Ejecuta verificaciones básicas y guía al usuario en el setup inicial.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_python_version() -> bool:
    """Verifica que la versión de Python sea 3.11+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python 3.11+ requerido. Versión actual: {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_docker() -> bool:
    """Verifica que Docker esté disponible."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ Docker: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker no encontrado. Instala Docker Desktop.")
        return False


def check_docker_compose() -> bool:
    """Verifica que Docker Compose esté disponible."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ Docker Compose: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose no encontrado.")
        return False


def check_env_file() -> bool:
    """Verifica que exista .env o .env.example."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")

    if env_path.exists():
        print("✓ Archivo .env encontrado")
        return True

    if env_example_path.exists():
        print("⚠ Archivo .env no encontrado, pero .env.example existe")
        print("  Ejecuta: cp .env.example .env")
        return False

    print("❌ No se encontró .env ni .env.example")
    return False


def check_requirements() -> bool:
    """Verifica que requirements.txt exista."""
    if Path("requirements.txt").exists():
        print("✓ requirements.txt encontrado")
        return True
    print("❌ requirements.txt no encontrado")
    return False


def check_dependencies() -> bool:
    """Verifica que las dependencias principales estén instaladas."""
    try:
        import psycopg
        import dotenv
        print("✓ Dependencias principales instaladas")
        return True
    except ImportError as e:
        print(f"⚠ Dependencias no instaladas: {e}")
        print("  Ejecuta: pip install -r requirements.txt")
        return False


def main() -> None:
    """Función principal del setup."""
    print("=== DESK-GRADE SETUP CHECK ===\n")

    checks = [
        ("Python version", check_python_version),
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        (".env file", check_env_file),
        ("requirements.txt", check_requirements),
        ("Dependencies", check_dependencies),
    ]

    results = []
    for name, check_func in checks:
        print(f"Verificando {name}...", end=" ")
        result = check_func()
        results.append((name, result))
        print()

    print("\n=== RESUMEN ===")
    all_ok = all(result for _, result in results)
    for name, result in results:
        status = "✓" if result else "❌"
        print(f"{status} {name}")

    if all_ok:
        print("\n✅ Sistema listo para usar!")
        print("\nPróximos pasos:")
        print("  1. docker compose up -d")
        print("  2. python -m scripts.health_check")
        print("  3. python -m scripts.seed_data")
        print("  4. python -m scripts.run_risk_cycle")
    else:
        print("\n⚠️  Algunas verificaciones fallaron. Revisa los mensajes arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
