# database.py
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from config.settings import settings

load_dotenv()

# Configuración de la base de datos de autenticación
# Usar AUTH_DB_* para la base de datos de autenticación (líneas 17-21 del .env)
AUTH_DB_HOST = os.getenv("AUTH_DB_HOST", "localhost")
AUTH_DB_PORT = os.getenv("AUTH_DB_PORT", "5432")
AUTH_DB_NAME = os.getenv("AUTH_DB_NAME", "")
AUTH_DB_USER = os.getenv("AUTH_DB_USER", "")
AUTH_DB_PASSWORD = os.getenv("AUTH_DB_PASSWORD", "")

# Construir DATABASE_URL desde las variables AUTH_DB_*
if AUTH_DB_NAME and AUTH_DB_USER and AUTH_DB_PASSWORD:
    DATABASE_URL = f"postgresql+asyncpg://{AUTH_DB_USER}:{AUTH_DB_PASSWORD}@{AUTH_DB_HOST}:{AUTH_DB_PORT}/{AUTH_DB_NAME}"
elif os.getenv("DATABASE_URL"):
    # Fallback a DATABASE_URL si está definida
    DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
else:
    # Último fallback: usar settings (que usa DB_*)
    DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Motores asíncronos
engine = create_async_engine(DATABASE_URL, echo=False)  

# Fábricas de sesiones
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    """
    Proveedor de dependencia para obtener una sesión de base de datos.
    """
    async with SessionLocal() as session:
        yield session
