from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from auth_models import Usuario
from auth_database import get_session
from auth_email_service import email_service
from pydantic import BaseModel

router = APIRouter(prefix="/notify", tags=["Notificaciones"])

class ForgotPasswordRequest(BaseModel):
    username: str

@router.post("/forgot-password")
async def notify_admin_forgot_password(
    data: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session)
):
    """Notifica al admin que un usuario olvidó su contraseña"""
    username = data.username
    # Buscar usuario admin
    result = await session.execute(select(Usuario).where(Usuario.username == 'admin', Usuario.rol == 'admin'))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="No se encontró el usuario admin")
    # Enviar email
    email_service.send_email(
        to_email=admin.email,
        subject="Solicitud de restablecimiento de contraseña",
        body=f"El usuario '{username}' ha solicitado recuperar su contraseña. Favor de contactarlo para asistirlo."
    )
    return {"message": "Se ha notificado al administrador"}
