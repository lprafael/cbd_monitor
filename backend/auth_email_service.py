# email_service.py
# Servicio para envío de emails

import smtplib
import imaplib
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
        self.imap_host = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False, delete_after_send: bool = False, cc_emails: Optional[list] = None) -> bool:
        """Envía un email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Añadir CC si se proporcionan o están configurados en .env
            final_cc = []
            if cc_emails:
                final_cc.extend(cc_emails)
            
            # También añadir CC globales del .env
            env_cc = os.getenv("EMAIL_CC", "")
            if env_cc:
                final_cc.extend([email.strip() for email in env_cc.split(",") if email.strip()])
            
            if final_cc:
                msg['Cc'] = ", ".join(final_cc)

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            
            # Solo loguear si hay credenciales
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Todos los destinatarios para sendmail
            all_recipients = [to_email] + final_cc
            
            text = msg.as_string()
            server.sendmail(self.from_email, all_recipients, text)
            server.quit()
            
            # Si se solicita borrar de Enviados (para mayor seguridad)
            if delete_after_send:
                self._delete_sent_email(to_email, subject)
                
            return True
        except Exception as e:
            print(f"Error enviando email a {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _delete_sent_email(self, to_email: str, subject: str):
        """Intenta eliminar el mensaje recién enviado de la carpeta 'Enviados' vía IMAP"""
        try:
            # Conectar vía IMAP
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.username, self.password)
            
            # Gmail usa una estructura específica para Enviados
            # Intentamos las carpetas más comunes
            sent_folders = ['"[Gmail]/Sent Mail"', '"[Gmail]/Enviados"', 'Sent', 'Enviados']
            
            for folder in sent_folders:
                try:
                    res, _ = mail.select(folder)
                    if res == 'OK':
                        # Buscar el mensaje por destinatario y asunto
                        search_criteria = f'(TO "{to_email}" SUBJECT "{subject}")'
                        typ, data = mail.search(None, search_criteria)
                        
                        for num in data[0].split():
                            # Marcar para borrar
                            mail.store(num, '+FLAGS', '\\Deleted')
                        
                        # Ejecutar borrado
                        mail.expunge()
                        break
                except:
                    continue
            
            mail.logout()
        except Exception as e:
            print(f"No se pudo limpiar el buzón de enviados: {e}")

    def send_welcome_email(self, to_email: str, username: str, password: str, role: str, delete_after_send: bool = False) -> bool:
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
            <p>Puedes acceder al sistema desde el siguiente enlace:</p>
            <p><a href="https://sistemas.mopc.gov.py/cbd_monitor">https://sistemas.mopc.gov.py/cbd_monitor</a></p>
            <p>Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.</p>
            <p>Saludos,<br>Equipo de Desarrollo</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body, is_html=True, delete_after_send=delete_after_send)

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
        
        return self.send_email(to_email, subject, html_body, is_html=True, delete_after_send=True)

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
