"""
Script para reiniciar Grafana y aplicar cambios de configuración.
"""

import subprocess
import sys


def restart_grafana() -> None:
    """Reinicia el contenedor de Grafana."""
    print("Reiniciando Grafana...")
    try:
        result = subprocess.run(
            ["docker", "compose", "restart", "grafana"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Grafana reiniciado correctamente")
        print("\nEspera unos segundos y luego accede a:")
        print("  http://localhost:3000")
        print("\nUsuario: admin")
        print("Contraseña: admin")
        print("\nNota: La interfaz puede tardar unos segundos en cambiar a español.")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error reiniciando Grafana: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("✗ Docker Compose no encontrado. Asegúrate de tener Docker instalado.")
        sys.exit(1)


if __name__ == "__main__":
    restart_grafana()
