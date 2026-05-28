import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import os
from dotenv import load_dotenv

# Importar modelos
from auth_models import Usuario, Rol, UsuarioSistemaRol, SistemaApp

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cbd_monitor")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def migrate_roles():
    async with async_session() as session:
        # 1. Asegurarse que el sistema_id = 1 (CBD Monitor) exista
        result_sis = await session.execute(select(SistemaApp).where(SistemaApp.id == 1))
        sistema_cbd = result_sis.scalar_one_or_none()
        if not sistema_cbd:
            print("Creando registro para Sistema CBD Monitor (id=1)...")
            sistema_cbd = SistemaApp(id=1, nombre="CBD Monitor", descripcion="Monitor de Control de Buses Distintos")
            session.add(sistema_cbd)
            await session.commit()
            
        # 2. Obtener todos los usuarios
        result_users = await session.execute(select(Usuario))
        usuarios = result_users.scalars().all()
        
        # 3. Obtener todos los roles disponibles
        result_roles = await session.execute(select(Rol))
        roles_dict = {r.nombre: r.id for r in result_roles.scalars().all()}
        
        count = 0
        for user in usuarios:
            # Buscar si ya tiene habilitación para CBD
            result_hab = await session.execute(
                select(UsuarioSistemaRol)
                .where((UsuarioSistemaRol.usuario_id == user.id) & (UsuarioSistemaRol.sistema_id == 1))
            )
            hab = result_hab.scalar_one_or_none()
            
            if not hab:
                # Obtener el rol actual de la columna plana, por defecto 'user' o 'viewer'
                rol_nombre = user.rol if user.rol else 'viewer'
                rol_id = roles_dict.get(rol_nombre)
                
                if rol_id:
                    print(f"Migrando usuario {user.username} (rol: {rol_nombre}) a UsuarioSistemaRol...")
                    nueva_hab = UsuarioSistemaRol(
                        usuario_id=user.id,
                        sistema_id=1,
                        rol_id=rol_id
                    )
                    session.add(nueva_hab)
                    count += 1
                else:
                    print(f"WARNING: Rol '{rol_nombre}' no encontrado en la tabla roles para el usuario {user.username}")
                    
        if count > 0:
            await session.commit()
            print(f"Migración completada. {count} usuarios migrados.")
        else:
            print("No fue necesario migrar ningún usuario (todos tienen su registro).")

if __name__ == "__main__":
    asyncio.run(migrate_roles())
