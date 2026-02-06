# schemas.py
# Esquemas Pydantic para validación de datos

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum

# ===== ENUMS =====

class TipoUsuario(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"

class TipoAccion(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"

class TipoNotificacion(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

# ===== SCHEMAS DE AUTENTICACIÓN =====

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: str
    rol: str = "user"
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if len(v) < 2:
            raise ValueError('El nombre de usuario debe tener al menos 2 caracteres')
        return v

class GoogleLogin(BaseModel):
    credential: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    nombre_completo: str
    rol: str
    activo: bool
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SesionUsuarioResponse(BaseModel):
    id: int
    usuario_id: int
    username: Optional[str] = None
    token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    fecha_inicio: datetime
    fecha_expiracion: datetime
    activa: bool
    fecha_cierre: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ===== SCHEMAS DE CONTRASEÑAS =====

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

# ===== SCHEMAS DE ROLES Y PERMISOS =====

class RolCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    permisos: List[int] = []  # IDs de permisos

class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None
    permisos: Optional[List[int]] = None

class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool
    fecha_creacion: datetime
    permisos: List['PermisoResponse'] = []
    
    class Config:
        from_attributes = True

class PermisoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    modulo: str
    accion: str

class PermisoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    modulo: Optional[str] = None
    accion: Optional[str] = None
    activo: Optional[bool] = None

class PermisoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    modulo: str
    accion: str
    activo: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

# ===== SCHEMAS DE AUDITORÍA =====

class LogAccesoCreate(BaseModel):
    username: str
    accion: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    exitoso: bool = True
    detalles: Optional[Dict[str, Any]] = None

class LogAccesoResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    username: str
    accion: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    fecha: datetime
    exitoso: bool
    detalles: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class LogAuditoriaCreate(BaseModel):
    username: str
    accion: str
    tabla: str
    registro_id: Optional[int] = None
    datos_anteriores: Optional[Dict[str, Any]] = None
    datos_nuevos: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    detalles: Optional[str] = None

class LogAuditoriaResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    username: str
    accion: str
    tabla: str
    registro_id: Optional[int] = None
    datos_anteriores: Optional[Dict[str, Any]] = None
    datos_nuevos: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    fecha: datetime
    detalles: Optional[str] = None
    
    class Config:
        from_attributes = True

# ===== SCHEMAS DE PARÁMETROS =====

class ParametroSistemaCreate(BaseModel):
    codigo: str
    nombre: str
    valor: str
    tipo: str = "string"
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    editable: bool = True

class ParametroSistemaUpdate(BaseModel):
    nombre: Optional[str] = None
    valor: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    editable: Optional[bool] = None
    activo: Optional[bool] = None

class ParametroSistemaResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    valor: str
    tipo: str
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    editable: bool
    activo: bool
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ===== SCHEMAS DE NOTIFICACIONES =====

class NotificacionCreate(BaseModel):
    usuario_id: int
    titulo: str
    mensaje: str
    tipo: TipoNotificacion = TipoNotificacion.INFO
    datos_adicionales: Optional[Dict[str, Any]] = None

class NotificacionUpdate(BaseModel):
    leida: Optional[bool] = None

class NotificacionResponse(BaseModel):
    id: int
    usuario_id: int
    titulo: str
    mensaje: str
    tipo: str
    leida: bool
    fecha_creacion: datetime
    fecha_lectura: Optional[datetime] = None
    datos_adicionales: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# ===== SCHEMAS DE REPORTES =====

class ReporteCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo: str
    parametros: Optional[Dict[str, Any]] = None

class ReporteResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo: str
    parametros: Optional[Dict[str, Any]] = None
    fecha_creacion: datetime
    fecha_ejecucion: Optional[datetime] = None
    estado: str
    ruta_archivo: Optional[str] = None
    creado_por: int
    detalles: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# ===== SCHEMAS DE UTILIDAD =====

class RoleInfo(BaseModel):
    role: str
    permissions: List[str]

class PermissionCheck(BaseModel):
    permission: str
    has_permission: bool
