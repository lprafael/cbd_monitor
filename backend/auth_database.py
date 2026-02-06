# database.py
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from config.settings import settings

load_dotenv()

# Configuración de las bases de datos
# Usar la misma configuración que el resto del sistema CBD
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Si no hay DATABASE_URL, construir desde settings
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
