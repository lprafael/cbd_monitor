#!/usr/bin/env python3
"""
Script de prueba para verificar que la conexión a la base de datos de autenticación
usa las variables AUTH_DB_* y el schema 'sistema'
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from auth_models import Usuario
from auth_database import DATABASE_URL, get_session

load_dotenv()

async def test_connection():
    """Prueba la conexión y verifica que use el schema correcto"""
    
    print("=" * 60)
    print("PRUEBA DE CONEXIÓN A BASE DE DATOS DE AUTENTICACIÓN")
    print("=" * 60)
    
    # Mostrar configuración
    print("\n[1] Configuración de conexión:")
    print(f"   DATABASE_URL: {DATABASE_URL[:50]}...")  # Mostrar solo los primeros caracteres por seguridad
    print(f"   AUTH_DB_HOST: {os.getenv('AUTH_DB_HOST')}")
    print(f"   AUTH_DB_PORT: {os.getenv('AUTH_DB_PORT')}")
    print(f"   AUTH_DB_NAME: {os.getenv('AUTH_DB_NAME')}")
    print(f"   AUTH_DB_USER: {os.getenv('AUTH_DB_USER')}")
    
    # Crear engine y sesión
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Verificar schema actual
            print("\n[2] Verificando schema actual:")
            result = await session.execute(text("SELECT current_schema()"))
            current_schema = result.scalar()
            print(f"   Schema actual: {current_schema}")
            
            # Verificar que existe el schema 'sistema'
            print("\n[3] Verificando existencia del schema 'sistema':")
            result = await session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'sistema'")
            )
            schema_exists = result.scalar()
            if schema_exists:
                print("   [OK] El schema 'sistema' existe")
            else:
                print("   [ERROR] El schema 'sistema' NO existe")
                return
            
            # Verificar que existe la tabla sistema.usuarios
            print("\n[4] Verificando tabla sistema.usuarios:")
            result = await session.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'sistema' AND table_name = 'usuarios'
                """)
            )
            table_exists = result.scalar()
            if table_exists:
                print("   [OK] La tabla sistema.usuarios existe")
            else:
                print("   [ERROR] La tabla sistema.usuarios NO existe")
                return
            
            # Probar consulta usando el modelo (debe usar schema automáticamente)
            print("\n[5] Probando consulta con modelo Usuario:")
            result = await session.execute(
                select(Usuario).where(Usuario.username == 'admin')
            )
            user = result.scalar_one_or_none()
            if user:
                print(f"   [OK] Usuario encontrado: {user.username}")
                print(f"   [OK] Email: {user.email}")
                print(f"   [OK] Rol: {user.rol}")
                print(f"   [OK] Activo: {user.activo}")
            else:
                print("   [ADVERTENCIA] No se encontró el usuario 'admin'")
            
            # Verificar la consulta SQL generada (usando echo=True temporalmente)
            print("\n[6] Verificando que las consultas usen el schema 'sistema':")
            engine_echo = create_async_engine(DATABASE_URL, echo=True)
            async_session_echo = sessionmaker(engine_echo, class_=AsyncSession, expire_on_commit=False)
            
            async with async_session_echo() as session_echo:
                print("   Ejecutando: select(Usuario).where(Usuario.username == 'admin')")
                result = await session_echo.execute(
                    select(Usuario).where(Usuario.username == 'admin')
                )
                user = result.scalar_one_or_none()
                if user:
                    print(f"   [OK] Consulta exitosa - Usuario: {user.username}")
            
            await engine_echo.dispose()
            
    except Exception as e:
        print(f"\n[ERROR] Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()
    
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_connection())
