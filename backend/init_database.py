#!/usr/bin/env python3
# Para ejecutar este script: python init_database.py
"""
Script para inicializar la base de datos con todas las tablas y datos por defecto
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from auth_models import Base, Usuario, Rol, Permiso, ParametroSistema, ConfiguracionEmail
from auth_security import get_password_hash
from datetime import datetime, timedelta
from config.settings import settings

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de la base de datos - Usar AUTH_DB_* para la base de datos de autenticación
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

async def init_database():
    """Inicializa la base de datos con todas las tablas y datos por defecto"""
    
    # Crear engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # Crear schema y todas las tablas
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sistema"))
        await conn.run_sync(Base.metadata.create_all)
    
    # Crear sesión
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Verificar si ya existen datos (usando el modelo que ya tiene el schema)
            result = await session.execute(select(Usuario).where(Usuario.id == 1))
            existing_admin = result.scalar_one_or_none()
            if existing_admin:
                print("La base de datos ya está inicializada.")
                print(f"Usuario administrador existente: {existing_admin.username}")
                return
            
            print("Inicializando base de datos...")
            
            # ===== CREAR PERMISOS POR DEFECTO =====
            print("Creando permisos...")
            
            # Verificar permisos existentes
            result_permisos = await session.execute(select(Permiso))
            permisos_existentes = {p.nombre for p in result_permisos.scalars().all()}
            
            permisos = [
                # Permisos para Usuarios
                Permiso(nombre="usuarios_read", descripcion="Leer usuarios", modulo="usuarios", accion="read"),
                Permiso(nombre="usuarios_write", descripcion="Crear/editar usuarios", modulo="usuarios", accion="write"),
                Permiso(nombre="usuarios_delete", descripcion="Eliminar usuarios", modulo="usuarios", accion="delete"),
                Permiso(nombre="usuarios_manage", descripcion="Gestionar usuarios", modulo="usuarios", accion="manage"),
                
                # Permisos para Roles
                Permiso(nombre="roles_read", descripcion="Leer roles", modulo="roles", accion="read"),
                Permiso(nombre="roles_write", descripcion="Crear/editar roles", modulo="roles", accion="write"),
                Permiso(nombre="roles_delete", descripcion="Eliminar roles", modulo="roles", accion="delete"),
                Permiso(nombre="roles_manage", descripcion="Gestionar roles", modulo="roles", accion="manage"),
                
                # Permisos para Auditoría
                Permiso(nombre="auditoria_read", descripcion="Ver logs de auditoría", modulo="auditoria", accion="read"),
                Permiso(nombre="auditoria_export", descripcion="Exportar logs de auditoría", modulo="auditoria", accion="export"),
                
                # Permisos para Sistema
                Permiso(nombre="sistema_config", descripcion="Configurar sistema", modulo="sistema", accion="config"),
                Permiso(nombre="sistema_backup", descripcion="Gestionar backups", modulo="sistema", accion="backup"),
                Permiso(nombre="sistema_reportes", descripcion="Generar reportes", modulo="sistema", accion="reportes"),
            ]
            
            # Solo agregar permisos que no existen
            permisos_a_crear = [p for p in permisos if p.nombre not in permisos_existentes]
            if permisos_a_crear:
                for permiso in permisos_a_crear:
                    session.add(permiso)
                await session.commit()
                print(f"  [OK] Creados {len(permisos_a_crear)} permisos nuevos")
            else:
                print("  [OK] Todos los permisos ya existen")
            
            # Obtener los permisos creados
            permisos_creados = await session.execute(
                text("SELECT id, nombre FROM sistema.permisos")
            )
            permisos_dict = {nombre: id_ for id_, nombre in permisos_creados.all()}
            
            # ===== CREAR ROLES POR DEFECTO =====
            print("Creando roles...")
            
            # Verificar roles existentes
            result_roles = await session.execute(select(Rol))
            roles_existentes = {r.nombre: r for r in result_roles.scalars().all()}
            
            # Rol Admin - Todos los permisos
            if "admin" not in roles_existentes:
                rol_admin = Rol(
                    nombre="admin",
                    descripcion="Administrador del sistema con acceso completo"
                )
                session.add(rol_admin)
                await session.commit()
                print("  [OK] Rol 'admin' creado")
            else:
                rol_admin = roles_existentes["admin"]
                print("  [OK] Rol 'admin' ya existe")
            
            # Asignar todos los permisos al admin
            for permiso_id in permisos_dict.values():
                await session.execute(
                    text("INSERT INTO sistema.rol_permiso (rol_id, permiso_id) VALUES (:rol_id, :permiso_id)"),
                    {"rol_id": rol_admin.id, "permiso_id": permiso_id}
                )
            
            # Rol Manager - Permisos de gestión
            if "manager" not in roles_existentes:
                rol_manager = Rol(
                    nombre="manager",
                    descripcion="Gerente con permisos de gestión y lectura"
                )
                session.add(rol_manager)
                await session.commit()
                print("  [OK] Rol 'manager' creado")
            else:
                rol_manager = roles_existentes["manager"]
                print("  [OK] Rol 'manager' ya existe")
            
            # Permisos para manager
            permisos_manager = [
                "usuarios_read", "auditoria_read", "sistema_backup"
            ]
            
            for permiso_nombre in permisos_manager:
                if permiso_nombre in permisos_dict:
                    await session.execute(
                        text("INSERT INTO sistema.rol_permiso (rol_id, permiso_id) VALUES (:rol_id, :permiso_id)"),
                        {"rol_id": rol_manager.id, "permiso_id": permisos_dict[permiso_nombre]}
                    )
            
            # Rol User - Permisos básicos
            if "user" not in roles_existentes:
                rol_user = Rol(
                    nombre="user",
                    descripcion="Usuario con permisos básicos de lectura y escritura"
                )
                session.add(rol_user)
                await session.commit()
                print("  [OK] Rol 'user' creado")
            else:
                rol_user = roles_existentes.get("user")
                print("  [OK] Rol 'user' ya existe")
            
            # Permisos para user (actualmente sin permisos específicos en base limpia)
            permisos_user = [
            ]
            
            for permiso_nombre in permisos_user:
                if permiso_nombre in permisos_dict:
                    await session.execute(
                        text("INSERT INTO sistema.rol_permiso (rol_id, permiso_id) VALUES (:rol_id, :permiso_id)"),
                        {"rol_id": rol_user.id, "permiso_id": permisos_dict[permiso_nombre]}
                    )
            
            # Rol Viewer - Solo lectura
            if "viewer" not in roles_existentes:
                rol_viewer = Rol(
                    nombre="viewer",
                    descripcion="Visualizador con permisos de solo lectura"
                )
                session.add(rol_viewer)
                await session.commit()
                print("  [OK] Rol 'viewer' creado")
            else:
                rol_viewer = roles_existentes.get("viewer")
                print("  [OK] Rol 'viewer' ya existe")
            
            # Permisos para viewer
            permisos_viewer = [
            ]
            
            for permiso_nombre in permisos_viewer:
                if permiso_nombre in permisos_dict:
                    await session.execute(
                        text("INSERT INTO sistema.rol_permiso (rol_id, permiso_id) VALUES (:rol_id, :permiso_id)"),
                        {"rol_id": rol_viewer.id, "permiso_id": permisos_dict[permiso_nombre]}
                    )
            
            await session.commit()
            
            # ===== CREAR USUARIO ADMINISTRADOR =====
            print("Creando usuario administrador...")
            
            admin_password = "Admin123!"
            admin_user = Usuario(
                username="admin",
                email="rafadevstack@gmail.com",
                hashed_password=get_password_hash(admin_password),
                nombre_completo="Administrador de CBD Monitor",
                rol="admin",
                activo=True,
                fecha_creacion=datetime.utcnow()
            )
            session.add(admin_user)
            await session.commit()
            
            # Asignar rol admin al usuario admin
            await session.execute(
                text("INSERT INTO sistema.usuario_rol (usuario_id, rol_id) VALUES (:usuario_id, :rol_id)"),
                {"usuario_id": admin_user.id, "rol_id": rol_admin.id}
            )
            
            # ===== CREAR PARÁMETROS DEL SISTEMA =====
            print("Creando parámetros del sistema...")
            
            parametros = [
                # Parámetros de seguridad
                ParametroSistema(
                    codigo="SESSION_TIMEOUT_MINUTES",
                    nombre="Tiempo de sesión (minutos)",
                    valor="480",
                    tipo="integer",
                    descripcion="Tiempo de expiración de sesión en minutos",
                    categoria="seguridad",
                    editable=True
                ),
                ParametroSistema(
                    codigo="MAX_LOGIN_ATTEMPTS",
                    nombre="Máximo intentos de login",
                    valor="5",
                    tipo="integer",
                    descripcion="Número máximo de intentos de login antes del bloqueo",
                    categoria="seguridad",
                    editable=True
                ),
                ParametroSistema(
                    codigo="PASSWORD_EXPIRY_DAYS",
                    nombre="Expiración de contraseña (días)",
                    valor="90",
                    tipo="integer",
                    descripcion="Días antes de que expire la contraseña",
                    categoria="seguridad",
                    editable=True
                ),
                
                # Parámetros de email
                ParametroSistema(
                    codigo="EMAIL_ENABLED",
                    nombre="Email habilitado",
                    valor="true",
                    tipo="boolean",
                    descripcion="Habilitar envío de emails",
                    categoria="email",
                    editable=True
                ),
                ParametroSistema(
                    codigo="EMAIL_FROM_NAME",
                    nombre="Nombre del remitente",
                    valor="CBD Monitor - CID",
                    tipo="string",
                    descripcion="Nombre que aparece como remitente en los emails",
                    categoria="email",
                    editable=True
                ),
                
                # Parámetros del sistema
                ParametroSistema(
                    codigo="SYSTEM_NAME",
                    nombre="Nombre del sistema",
                    valor="CBD Monitor - CID",
                    tipo="string",
                    descripcion="Nombre del sistema",
                    categoria="sistema",
                    editable=True
                ),
                ParametroSistema(
                    codigo="SYSTEM_VERSION",
                    nombre="Versión del sistema",
                    valor="1.0.0",
                    tipo="string",
                    descripcion="Versión actual del sistema",
                    categoria="sistema",
                    editable=False
                ),
                ParametroSistema(
                    codigo="BACKUP_RETENTION_DAYS",
                    nombre="Retención de backups (días)",
                    valor="30",
                    tipo="integer",
                    descripcion="Días que se mantienen los backups",
                    categoria="sistema",
                    editable=True
                ),
            ]
            
            for parametro in parametros:
                session.add(parametro)
            
            await session.commit()
            
            # ===== CREAR CONFIGURACIÓN DE EMAIL POR DEFECTO =====
            print("Creando configuración de email por defecto...")
            config_email = ConfiguracionEmail(
                nombre="Configuración Principal",
                host="smtp.example.com",
                puerto=587,
                username="user@example.com",
                password="password",
                use_tls=True,
                from_email="no-reply@example.com",
                activo=False
            )
            session.add(config_email)
            await session.commit()
            
            print("Base de datos inicializada correctamente!")
            print(f"Usuario administrador creado:")
            print(f"   Usuario: admin")
            print(f"   Contraseña: {admin_password}")
            print(f"   Email: rafadevstack@gmail.com")
            print(f"   Rol: admin")
            print()
            print("Roles creados:")
            print("   - admin: Acceso completo al sistema")
            print("   - manager: Gestión y lectura")
            print("   - user: Operaciones básicas")
            print("   - viewer: Solo lectura")
            print()
            print("Permisos configurados para cada rol")
            print("Parámetros del sistema configurados")
            print("Configuración de email por defecto creada")
            
        except Exception as e:
            await session.rollback()
            print(f"Error al inicializar la base de datos: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
