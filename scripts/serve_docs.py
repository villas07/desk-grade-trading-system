"""Servidor sencillo de documentación para Desk-Grade.

Levanta un servidor HTTP estático que sirve los archivos de la repo
(README, GUIA_COMPLETA.md, QUICKSTART.md, etc.) para poder abrirlos
desde el navegador o enlazarlos desde Grafana.

Uso:

    python -m scripts.serve_docs

Luego abre en el navegador, por ejemplo:
- http://localhost:8001/GUIA_COMPLETA.md
- http://localhost:8001/README.md
- http://localhost:8001/QUICKSTART.md
"""

from __future__ import annotations

import http.server
import os
import socketserver
from pathlib import Path

PORT = int(os.getenv("DESKGRADE_DOCS_PORT", "8001"))

# Raíz del proyecto (carpeta "desk-grade-ready")
ROOT = Path(__file__).resolve().parents[1]


def run_server() -> None:
    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"Servidor de documentación Desk-Grade en http://localhost:{PORT}/")
        print("Ejemplos:")
        print("  - http://localhost:%d/GUIA_COMPLETA.md" % PORT)
        print("  - http://localhost:%d/README.md" % PORT)
        print("  - http://localhost:%d/QUICKSTART.md" % PORT)
        print("Pulsa Ctrl+C para detener el servidor.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    run_server()

