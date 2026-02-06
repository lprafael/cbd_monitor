"""Conexión a la base de datos de autenticación (Postgres local, opción A)."""

import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings
from typing import Optional


class AuthDatabaseConnection:
    """Conexión a la BD de usuarios/login (postgres-auth en el servidor)."""

    def __init__(self):
        self.connection: Optional[psycopg2.extensions.connection] = None

    def connect(self):
        """Establecer conexión con la base de datos de autenticación."""
        try:
            self.connection = psycopg2.connect(
                host=settings.AUTH_DB_HOST,
                port=settings.AUTH_DB_PORT,
                database=settings.AUTH_DB_NAME,
                user=settings.AUTH_DB_USER,
                password=settings.AUTH_DB_PASSWORD,
            )
            return self.connection
        except Exception as e:
            print(f"Error al conectar a la BD de autenticación: {e}")
            raise

    def close(self):
        """Cerrar la conexión."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_cursor(self):
        """Obtener un cursor para ejecutar queries."""
        if not self.connection or self.connection.closed:
            self.connect()
        return self.connection.cursor(cursor_factory=RealDictCursor)


def get_auth_db_connection():
    """Dependency/helper para obtener una conexión a la BD de autenticación."""
    db = AuthDatabaseConnection()
    try:
        db.connect()
        yield db
    finally:
        db.close()
