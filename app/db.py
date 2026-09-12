from psycopg2 import pool as psycopg2_pool

from app.config import DATABASE_URL

# Abrir una conexión TCP nueva a Supabase por query toma ~1-2s (handshake +
# TLS a un pooler remoto). Con un pool, las conexiones se abren una vez al
# arrancar el proceso y se reutilizan — esto es lo que hace que /forecast
# responda en <3s en vez de >10s.
_pool = psycopg2_pool.SimpleConnectionPool(3, 10, DATABASE_URL)


def get_connection():
    return _pool.getconn()


def release_connection(conn):
    _pool.putconn(conn)
