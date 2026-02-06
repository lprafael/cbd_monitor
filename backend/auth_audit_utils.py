#!/usr/bin/env python3
"""
Utilidades para el registro de logs de auditoría
"""

from sqlalchemy.ext.asyncio import AsyncSession
from auth_models import LogAuditoria
from auth_schemas import LogAuditoriaCreate
from typing import Optional, Dict, Any
from datetime import datetime

async def log_audit_action(
    session: AsyncSession,
    username: str,
    user_id: Optional[int],
    action: str,
    table: str,
    record_id: Optional[int] = None,
    previous_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None
):
    """
    Registra una acción de auditoría en la tabla logs_auditoria
    
    Args:
        session: Sesión de base de datos
        username: Nombre de usuario que realizó la acción
        user_id: ID del usuario (opcional)
        action: Tipo de acción (create, update, delete, export)
        table: Nombre de la tabla afectada
        record_id: ID del registro afectado (opcional)
        previous_data: Datos anteriores al cambio (opcional)
        new_data: Datos nuevos después del cambio (opcional)
        ip_address: Dirección IP del cliente (opcional)
        user_agent: User agent del navegador (opcional)
        details: Detalles adicionales (opcional)
    """
    try:
        log_data = LogAuditoriaCreate(
            username=username,
            accion=action,
            tabla=table,
            registro_id=record_id,
            datos_anteriores=previous_data,
            datos_nuevos=new_data,
            ip_address=ip_address,
            user_agent=user_agent,
            detalles=details
        )
        
        log = LogAuditoria(**log_data.dict())
        log.usuario_id = user_id
        log.fecha = datetime.utcnow()
        
        session.add(log)
        await session.commit()
        return {"status": "success", "log_id": log.id}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error al registrar log de auditoría: {str(e)}\n{error_details}"
        print(error_msg)
        await session.rollback()
        return {"status": "error", "error": str(e), "details": error_details}

async def log_activity(
    session: AsyncSession,
    request: Any,
    current_user: Dict[str, Any],
    action: str,
    table: str,
    record_id: Optional[int] = None,
    previous_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    details: Optional[str] = None
):
    """
    Versión simplificada de log_audit_action que extrae automáticamente
    IP, User-Agent y datos del usuario de los objetos request y current_user.
    """
    return await log_audit_action(
        session=session,
        username=current_user.get("sub", "unknown"),
        user_id=current_user.get("user_id"),
        action=action,
        table=table,
        record_id=record_id,
        previous_data=previous_data,
        new_data=new_data,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=details
    )

def get_client_ip(request) -> Optional[str]:
    """
    Obtiene la dirección IP del cliente desde la request
    """
    if hasattr(request, 'client') and request.client:
        return request.client.host
    return None

def get_user_agent(request) -> Optional[str]:
    """
    Obtiene el user agent desde la request
    """
    return request.headers.get("user-agent")
