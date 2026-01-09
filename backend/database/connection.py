"""Módulo para manejar la conexión a la base de datos PostgreSQL."""

import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings
from typing import Optional

class DatabaseConnection:
    """Clase para manejar las conexiones a PostgreSQL."""
    
    def __init__(self):
        """Inicializar la clase de conexión."""
        self.connection: Optional[psycopg2.extensions.connection] = None
    
    def connect(self):
        """Establecer conexión con la base de datos."""
        try:
            self.connection = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD
            )
            return self.connection
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            raise
    
    def close(self):
        """Cerrar la conexión a la base de datos."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get_cursor(self):
        """Obtener un cursor para ejecutar queries."""
        if not self.connection or self.connection.closed:
            self.connect()
        return self.connection.cursor(cursor_factory=RealDictCursor)

def get_db_connection():
    """Función helper para obtener una conexión a la base de datos."""
    db = DatabaseConnection()
    try:
        db.connect()
        yield db
    finally:
        db.close()
