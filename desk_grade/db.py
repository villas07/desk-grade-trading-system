import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv


load_dotenv()


def _build_dsn() -> str:
    """
    Construye el DSN de PostgreSQL a partir de variables de entorno.

    Variables soportadas (ver .env.example):
    - DB_HOST
    - DB_PORT
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    """
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "desk")
    user = os.getenv("DB_USER", "desk")
    password = os.getenv("DB_PASSWORD", "desk_pass")
    return f"dbname={name} user={user} password={password} host={host} port={port}"


@contextmanager
def db_session():
    """
    Proporciona una conexión a la base de datos usando psycopg.

    La conexión se crea para cada sesión y se cierra al salir del contexto.
    """
    dsn = _build_dsn()
    conn = psycopg.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()
