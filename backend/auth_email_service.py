# email_service.py
# Servicio para envío de emails

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("EMAIL_PORT", "587"))
        self.username = os.getenv("EMAIL_USERNAME", "")
        self.password = os.getenv("EMAIL_PASSWORD", "")
        self.from_email = os.getenv("EMAIL_FROM", "")

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Envía un email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            return True
        except Exception as e:
            print(f"Error enviando email: {e}")
            return False

    def send_welcome_email(self, to_email: str, username: str, password: str, role: str) -> bool:
        """Envía email de bienvenida con credenciales"""
        subject = "Bienvenido al Sistema"
        
        html_body = f"""
        <html>
        <body>
            <h2>Bienvenido al Sistema</h2>
            <p>Hola <strong>{username}</strong>,</p>
            <p>Tu cuenta ha sido creada exitosamente con los siguientes datos:</p>
            <ul>
                <li><strong>Usuario:</strong> {username}</li>
                <li><strong>Contraseña:</strong> {password}</li>
                <li><strong>Rol:</strong> {role}</li>
            </ul>
            <p>Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.</p>
            <p>Saludos,<br>Equipo de Desarrollo</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body, is_html=True)

    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """Envía email para restablecer contraseña"""
        subject = "Restablecimiento de Contraseña - Sistema"
        
        html_body = f"""
        <html>
        <body>
            <h2>Restablecimiento de Contraseña</h2>
            <p>Hola <strong>{username}</strong>,</p>
            <p>Has solicitado restablecer tu contraseña. Usa el siguiente token:</p>
            <h3>{reset_token}</h3>
            <p>Este token expira en 1 hora.</p>
            <p>Si no solicitaste este cambio, ignora este email.</p>
            <p>Saludos,<br>Equipo de Desarrollo</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body, is_html=True)

    def send_admin_notification_email(self, admin_email: str, new_user_email: str, new_user_name: str) -> bool:
        """Notifica al administrador de una nueva solicitud de acceso"""
        subject = "Nueva Solicitud de Acceso - Sistema"
        
        html_body = f"""
        <html>
        <body>
            <h2>Nueva Solicitud de Acceso</h2>
            <p>Hola Administrador,</p>
            <p>Se ha registrado un nuevo usuario a través de Google y está pendiente de aprobación:</p>
            <ul>
                <li><strong>Nombre:</strong> {new_user_name}</li>
                <li><strong>Email:</strong> {new_user_email}</li>
            </ul>
            <p>Para activar este usuario, ingresa al panel de administración del sistema.</p>
            <p>Saludos,<br>Equipo de Desarrollo</p>
        </body>
        </html>
        """
        
        return self.send_email(admin_email, subject, html_body, is_html=True)

# Instancia global del servicio de email
email_service = EmailService()
