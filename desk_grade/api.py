import psycopg
from psycopg.rows import dict_row
from .db import db_session

def execute(query, params=None):
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()

def fetch_all(query, params=None):
    with db_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()

def fetch_one(query, params=None):
    with db_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
