# security.py
# Configuración de seguridad para autenticación y autorización

import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_muy_segura_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")) # Default: 8 horas

# Configuración de email
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")

# Contexto para hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token para autenticación
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT de acceso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verifica y decodifica un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtiene el usuario actual basado en el token"""
    token = credentials.credentials
    payload = verify_token(token)
    return payload

# Roles y permisos (Hardcoded para validación rápida, idealmente usar base de datos)
ROLES = {
    "admin": {
        "description": "Administrador del sistema",
        "permissions": [
            "read", "write", "delete", "manage_users", "manage_roles",
            "usuarios_read", "usuarios_write", "usuarios_delete", "usuarios_manage",
            "roles_read", "roles_write", "roles_delete", "roles_manage",
            "auditoria_read", "auditoria_export",
            "sistema_config", "sistema_backup", "sistema_reportes"
        ]
    },
    "manager": {
        "description": "Gerente con acceso completo a datos",
        "permissions": ["read", "write", "delete", "usuarios_read", "auditoria_read", "sistema_backup"]
    },
    "user": {
        "description": "Usuario básico",
        "permissions": ["read", "write"]
    },
    "viewer": {
        "description": "Solo lectura",
        "permissions": ["read"]
    }
}

def check_permission(required_permission: str):
    """Decorador para verificar permisos"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        role = current_user.get("role", "viewer")
        user_permissions = ROLES.get(role, {}).get("permissions", [])
        print(f"DEBUG: Checking permission '{required_permission}' for role '{role}'")
        print(f"DEBUG: User permissions: {user_permissions}")
        if required_permission not in user_permissions:
            print(f"DEBUG: Permission denied!")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción"
            )
        return current_user
    return permission_checker

def check_database_permission(required_permission: str):
    """Verifica permisos desde la base de datos"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        # Esta función solo verifica el token, la verificación de permisos se hará en el endpoint
        return current_user
    
    return permission_checker
