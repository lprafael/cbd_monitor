"""Configuración de la aplicación usando variables de entorno."""

import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Settings:
    """Clase para manejar todas las configuraciones de la aplicación."""
    
    # Configuración de Base de Datos (datos CBD, reportes, etc.)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Base de datos de autenticación (Postgres local, opción A)
    AUTH_DB_HOST: str = os.getenv("AUTH_DB_HOST", "localhost")
    AUTH_DB_PORT: str = os.getenv("AUTH_DB_PORT", "5433")
    AUTH_DB_NAME: str = os.getenv("AUTH_DB_NAME", "cbd_auth")
    AUTH_DB_USER: str = os.getenv("AUTH_DB_USER", "")
    AUTH_DB_PASSWORD: str = os.getenv("AUTH_DB_PASSWORD", "")
    
    # Configuración del servidor
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Cadena de conexión para PostgreSQL
    @property
    def database_url(self) -> str:
        """Construir la URL de conexión a PostgreSQL (datos CBD)."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def auth_database_url(self) -> str:
        """URL de conexión a la BD de autenticación (usuarios/login)."""
        return f"postgresql://{self.AUTH_DB_USER}:{self.AUTH_DB_PASSWORD}@{self.AUTH_DB_HOST}:{self.AUTH_DB_PORT}/{self.AUTH_DB_NAME}"

settings = Settings()
