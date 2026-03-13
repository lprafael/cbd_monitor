# auth.py
# Endpoints de autenticación y gestión de usuarios

import secrets
import string
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from auth_models import Usuario, PasswordReset, LogAcceso
from auth_schemas import (
    UserLogin, UserCreate, UserUpdate, UserResponse, Token, 
    PasswordChange, PasswordResetRequest, PasswordResetConfirm,
    LogAccesoCreate, LogAccesoResponse, RoleInfo, GoogleLogin
)
from auth_security import (
    verify_password, get_password_hash, create_access_token, 
    verify_token, get_current_user, check_permission, ROLES
)
from auth_email_service import email_service
from auth_database import get_session
from auth_audit_utils import log_audit_action, get_client_ip, get_user_agent

# Importar Google Auth de forma opcional
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    google_auth_available = True
except ImportError:
    google_auth_available = False
    print("ADVERTENCIA: google-auth no está instalado. El login con Google no estará disponible.")

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Función para generar contraseña aleatoria
def generate_random_password(length: int = 12) -> str:
    """Genera una contraseña aleatoria segura"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

# Función para registrar logs de acceso
async def log_access(session: AsyncSession, log_data: LogAccesoCreate, usuario_id: int = None):
    """Registra un log de acceso"""
    log = LogAcceso(**log_data.dict())
    
    # Si no se proporciona usuario_id, intentar obtenerlo del username
    if not usuario_id and log_data.username:
        try:
            result = await session.execute(
                select(Usuario).where(Usuario.username == log_data.username)
            )
            user = result.scalar_one_or_none()
            if user:
                usuario_id = user.id
        except Exception as e:
            print(f"Error obteniendo usuario_id para log: {e}")
    
    if usuario_id:
        log.usuario_id = usuario_id
    
    session.add(log)
    await session.commit()

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin, 
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Inicio de sesión de usuario"""
    # Buscar usuario
    result = await session.execute(
        select(Usuario).where(Usuario.username == user_credentials.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo"
        )
    
    # Actualizar último acceso
    user.ultimo_acceso = datetime.utcnow()
    await session.commit()
    
    # Crear token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.rol, "user_id": user.id}
    )
    
    # Registrar log
    await log_access(session, LogAccesoCreate(
        username=user.username,
        accion="login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    ), usuario_id=user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/google-login", response_model=Token)
async def google_login(
    data: GoogleLogin,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Inicio de sesión con Google OAuth2"""
    if not google_auth_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El login con Google no está disponible. Instale google-auth para habilitarlo."
        )
    
    try:
        # Verificar el token de Google
        id_info = id_token.verify_oauth2_token(
            data.credential, 
            google_requests.Request(), 
            os.getenv("GOOGLE_CLIENT_ID")
        )
        
        email = id_info['email']
        full_name = id_info.get('name', '')
        
        # Buscar usuario por email
        result = await session.execute(
            select(Usuario).where(Usuario.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Si el usuario no existe, lo creamos automáticamente
            # Generamos un username basado en el email
            username = email.split('@')[0]
            
            # Verificar si el username ya existe
            username_check = await session.execute(
                select(Usuario).where(Usuario.username == username)
            )
            if username_check.scalar_one_or_none():
                username = f"{username}_{secrets.token_hex(2)}"
            
            new_user = Usuario(
                username=username,
                email=email,
                hashed_password=get_password_hash(secrets.token_urlsafe(16)), # Password random inutilizable
                nombre_completo=full_name,
                rol="user",
                activo=False # El usuario se crea inactivo por defecto
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            user = new_user

            # Enviar notificación al administrador
            # Usaremos el email configurado en el .env como remitente para recibir también la notificación
            admin_email = os.getenv("EMAIL_FROM")
            if admin_email:
                email_service.send_admin_notification_email(
                    admin_email=admin_email,
                    new_user_email=email,
                    new_user_name=full_name
                )
            
            # Registrar auditoría de creación
            await log_audit_action(
                session=session,
                username="SYSTEM",
                user_id=None,
                action="create",
                table="usuarios",
                record_id=user.id,
                new_data={"username": user.username, "email": user.email, "metodo": "google"},
                details=f"Usuario creado vía Google Login: {user.username}"
            )

        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Su cuenta está pendiente de aprobación por un administrador"
            )
        
        # Actualizar último acceso
        user.ultimo_acceso = datetime.utcnow()
        await session.commit()
        
        # Crear token del sistema
        access_token = create_access_token(
            data={"sub": user.username, "role": user.rol, "user_id": user.id}
        )
        
        # Registrar log de acceso
        await log_access(session, LogAccesoCreate(
            username=user.username,
            accion="login_google",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        ), usuario_id=user.id)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
    except ValueError as e:
        # Token inválido
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token de Google inválido: {str(e)}"
        )
    except HTTPException:
        # Re-lanzar excepciones de FastAPI para que lleguen al frontend
        raise
    except Exception as e:
        print(f"Error en google_login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando autenticación de Google"
        )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cerrar sesión"""
    # Registrar log
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="logout",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    ), usuario_id=current_user.get("user_id"))
    
    return {"message": "Sesión cerrada exitosamente"}

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(check_permission("usuarios_manage")),
    session: AsyncSession = Depends(get_session)
):
    """Crear nuevo usuario (solo administradores)"""
    # Verificar si el usuario ya existe
    result = await session.execute(
        select(Usuario).where(
            (Usuario.username == user_data.username) | (Usuario.email == user_data.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario o email ya existe"
        )
    
    # Generar contraseña aleatoria
    password = generate_random_password()
    hashed_password = get_password_hash(password)
    
    # Crear usuario
    new_user = Usuario(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        nombre_completo=user_data.nombre_completo,
        rol=user_data.rol,
        creado_por=current_user["user_id"]
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    # Enviar email con credenciales
    email_service.send_welcome_email(
        user_data.email, 
        user_data.username, 
        password, 
        user_data.rol
    )
    
    # Registrar log de acceso
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="create_user",
        detalles={"mensaje": f"Usuario creado: {user_data.username}"}
    ), usuario_id=current_user.get("user_id"))
    # Registrar log de auditoría
    await log_audit_action(
        session=session,
        username=current_user["sub"],
        user_id=current_user["user_id"],
        action="create",
        table="usuarios",
        record_id=new_user.id,
        new_data={
            "username": new_user.username,
            "email": new_user.email,
            "rol": new_user.rol,
            "activo": new_user.activo,
        },
        details=f"Usuario creado: {new_user.username}"
    )
    
    return UserResponse.model_validate(new_user)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(check_permission("usuarios_read")),
    session: AsyncSession = Depends(get_session)
):
    """Listar usuarios (solo administradores)"""
    result = await session.execute(select(Usuario))
    users = result.scalars().all()
    return [UserResponse.model_validate(user) for user in users]

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(check_permission("usuarios_read")),
    session: AsyncSession = Depends(get_session)
):
    """Obtener usuario por ID"""
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserResponse.model_validate(user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(check_permission("usuarios_write")),
    session: AsyncSession = Depends(get_session)
):
    """Actualizar usuario (Solo Administradores)"""
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar campos
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
        
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError as e:
        await session.rollback()
        if 'email' in str(e.orig):
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
        raise HTTPException(status_code=400, detail="Error de integridad de datos")
    
    # Registrar log de acceso
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="update_user",
        detalles={"mensaje": f"Usuario actualizado: {user.username}"}
    ), usuario_id=current_user.get("user_id"))
    
    # Registrar log de auditoría
    await log_audit_action(
        session=session,
        username=current_user["sub"],
        user_id=current_user["user_id"],
        action="update",
        table="usuarios",
        record_id=user.id,
        new_data={k: v for k, v in update_data.items() if k != "hashed_password"},
        details=f"Usuario actualizado: {user.username}"
    )
    return UserResponse.model_validate(user)

@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: int,
    current_user: dict = Depends(check_permission("usuarios_manage")),
    session: AsyncSession = Depends(get_session)
):
    """Reactiva un usuario inactivo (activo=True)"""
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.activo:
        raise HTTPException(status_code=400, detail="El usuario ya está activo")
    user.activo = True
    await session.commit()
    # Registrar log de acceso
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="reactivate_user",
        detalles={"mensaje": f"Usuario reactivado: {user.username}"}
    ), usuario_id=current_user.get("user_id"))
    # Registrar log de auditoría
    await log_audit_action(
        session=session,
        username=current_user["sub"],
        user_id=current_user["user_id"],
        action="update",
        table="usuarios",
        record_id=user.id,
        previous_data={"activo": False},
        new_data={"activo": True},
        details=f"Usuario reactivado: {user.username}"
    )
    return {"message": "Usuario reactivado exitosamente"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(check_permission("usuarios_delete")),
    session: AsyncSession = Depends(get_session)
):
    """Eliminar usuario (desactivar)"""
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Proteger admin
    if user.username == 'admin' and user.rol == 'admin':
        raise HTTPException(status_code=403, detail="No se puede eliminar el usuario admin")
    # Desactivar usuario en lugar de eliminarlo
    user.activo = False
    await session.commit()
    # Registrar log de acceso
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="delete_user",
        detalles={"mensaje": f"Usuario desactivado: {user.username}"}
    ), usuario_id=current_user.get("user_id"))
    # Registrar log de auditoría
    await log_audit_action(
        session=session,
        username=current_user["sub"],
        user_id=current_user["user_id"],
        action="delete",
        table="usuarios",
        record_id=user.id,
        previous_data={
            "username": user.username,
            "email": user.email,
            "rol": user.rol,
        },
        details=f"Usuario desactivado: {user.username}"
    )
    return {"message": "Usuario desactivado exitosamente"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cambiar contraseña del usuario actual"""
    result = await session.execute(
        select(Usuario).where(Usuario.id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()
    
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    user.hashed_password = get_password_hash(password_data.new_password)
    await session.commit()
    
    # Registrar log
    await log_access(session, LogAccesoCreate(
        username=current_user["sub"],
        accion="change_password"
    ), usuario_id=current_user.get("user_id"))
    
    return {"message": "Contraseña cambiada exitosamente"}

@router.post("/reset-password-request")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    session: AsyncSession = Depends(get_session)
):
    """Solicitar restablecimiento de contraseña"""
    result = await session.execute(
        select(Usuario).where(Usuario.email == reset_request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # No revelar si el email existe o no
        return {"message": "Si el email existe, se enviará un enlace de restablecimiento"}
    
    # Generar token
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    
    # Guardar token
    reset_record = PasswordReset(
        email=reset_request.email,
        token=token,
        expira_en=expires
    )
    session.add(reset_record)
    await session.commit()
    
    # Enviar email
    email_service.send_password_reset_email(
        reset_request.email, 
        user.username, 
        token
    )
    
    return {"message": "Si el email existe, se enviará un enlace de restablecimiento"}

@router.post("/reset-password-confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session)
):
    """Confirmar restablecimiento de contraseña"""
    result = await session.execute(
        select(PasswordReset).where(
            and_(
                PasswordReset.token == reset_confirm.token,
                PasswordReset.usado == False,
                PasswordReset.expira_en > datetime.utcnow()
            )
        )
    )
    reset_record = result.scalar_one_or_none()
    
    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    # Buscar usuario
    result = await session.execute(
        select(Usuario).where(Usuario.email == reset_record.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar contraseña
    user.hashed_password = get_password_hash(reset_confirm.new_password)
    reset_record.usado = True
    await session.commit()
    
    return {"message": "Contraseña restablecida exitosamente"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Obtener información del usuario actual"""
    result = await session.execute(
        select(Usuario).where(Usuario.id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()
    return UserResponse.model_validate(user)

@router.get("/roles", response_model=List[RoleInfo])
async def get_roles():
    """Obtener información de roles disponibles"""
    return [
        RoleInfo(role=role, permissions=info.get("permissions", [])) 
        for role, info in ROLES.items()
    ]

@router.get("/logs", response_model=List[LogAccesoResponse])
async def get_logs(
    current_user: dict = Depends(check_permission("auditoria_read")),
    session: AsyncSession = Depends(get_session),
    limit: int = 100,
    offset: int = 0,
    username: Optional[str] = None,
    accion: Optional[str] = None,
    exitoso: Optional[bool] = None
):
    """Obtener logs de acceso con filtros opcionales (solo administradores)"""
    from sqlalchemy import desc
    
    query = select(LogAcceso)
    
    # Aplicar filtros
    if username:
        query = query.where(LogAcceso.username.ilike(f"%{username}%"))
    if accion:
        query = query.where(LogAcceso.accion == accion)
    if exitoso is not None:
        query = query.where(LogAcceso.exitoso == exitoso)
    
    # Ordenar por fecha descendente y aplicar paginación
    query = query.order_by(desc(LogAcceso.fecha)).offset(offset).limit(limit)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    return [LogAccesoResponse.model_validate(log) for log in logs]

@router.get("/google-client-id")
async def get_google_client_id():
    """Obtener el Google Client ID para el frontend (público)"""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    return {"google_client_id": client_id}
