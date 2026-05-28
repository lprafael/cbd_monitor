import re

with open('auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace imports
if 'from sqlalchemy.orm import selectinload' not in content:
    content = content.replace('from sqlalchemy.future import select', 
        'from sqlalchemy.future import select\nfrom sqlalchemy.orm import selectinload\nfrom auth_models import UsuarioSistemaRol')

# Add populate function
populate_func = """
def populate_cbd_rol(user):
    if not user: return user
    cbd_rol = "viewer"
    for hab in getattr(user, 'habilitaciones_sistemas', []):
        if getattr(hab, 'sistema_id', None) == 1 and getattr(hab, 'activo', True):
            cbd_rol = getattr(getattr(hab, 'rol', None), 'nombre', "viewer")
            break
    user.rol = cbd_rol
    return user
"""
if 'def populate_cbd_rol' not in content:
    content = content.replace('def generate_random_password', populate_func + '\ndef generate_random_password')

# Fix login
content = re.sub(
    r'result = await session\.execute\(\s*select\(Usuario\)\.where\(Usuario\.username == user_credentials\.username\)\s*\)',
    r'result = await session.execute(\n        select(Usuario)\n        .options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol))\n        .where(Usuario.username == user_credentials.username)\n    )',
    content
)

# Fix google_login
content = re.sub(
    r'result = await session\.execute\(\s*select\(Usuario\)\.where\(Usuario\.email == email\)\s*\)',
    r'result = await session.execute(\n            select(Usuario)\n            .options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol))\n            .where(Usuario.email == email)\n        )',
    content
)

# Fix list_users
content = re.sub(
    r'result = await session\.execute\(select\(Usuario\)\)',
    r'result = await session.execute(select(Usuario).options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol)))',
    content
)

# Fix get_user
content = re.sub(
    r'result = await session\.execute\(select\(Usuario\)\.where\(Usuario\.id == user_id\)\)',
    r'result = await session.execute(select(Usuario).options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol)).where(Usuario.id == user_id))',
    content
)

# Fix update_user
content = re.sub(
    r'result = await session\.execute\(select\(Usuario\)\.where\(Usuario\.id == user_id\)\)',
    r'result = await session.execute(select(Usuario).options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol)).where(Usuario.id == user_id))',
    content
)

# Fix delete_user
content = re.sub(
    r'result = await session\.execute\(select\(Usuario\)\.where\(Usuario\.id == user_id\)\)',
    r'result = await session.execute(select(Usuario).options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol)).where(Usuario.id == user_id))',
    content
)

# Fix get_current_user_info
content = re.sub(
    r'result = await session\.execute\(\s*select\(Usuario\)\.where\(Usuario\.id == current_user\["user_id"\]\)\s*\)',
    r'result = await session.execute(\n        select(Usuario)\n        .options(selectinload(Usuario.habilitaciones_sistemas).selectinload(UsuarioSistemaRol.rol))\n        .where(Usuario.id == current_user["user_id"])\n    )',
    content
)

# Replace all UserResponse.from_orm(user) with UserResponse.from_orm(populate_cbd_rol(user))
content = re.sub(r'UserResponse\.from_orm\((new_user|user)\)', r'UserResponse.from_orm(populate_cbd_rol(\1))', content)

# But wait, create_access_token uses user.rol directly!
# I need to call populate_cbd_rol(user) BEFORE create_access_token!
content = content.replace('user.ultimo_acceso = datetime.utcnow()', 'populate_cbd_rol(user)\n        user.ultimo_acceso = datetime.utcnow()')

# Create user needs a reload since we insert first, but wait! create_user doesn't link the user to the system by default in cbd_monitor!
# We can just let it be. 

with open('auth.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("auth.py updated.")
