# Instrucciones de Integración de Autenticación

## 📋 Resumen

Se ha integrado completamente el sistema de autenticación del sistema base en CBD Monitor. Ahora el sistema requiere login antes de acceder al panel principal.

## 🚀 Pasos para Configurar

### 1. Instalar Dependencias del Backend

```bash
cd backend
pip install -r requirements.txt
```

Las nuevas dependencias incluyen:
- `sqlalchemy[asyncio]` - Para operaciones asíncronas con la base de datos
- `asyncpg` - Driver asíncrono para PostgreSQL
- `python-jose[cryptography]` - Para JWT tokens
- `passlib[bcrypt]` - Para hash de contraseñas
- `email-validator` - Validación de emails
- `google-auth` - Para login con Google (opcional)

### 2. Configurar Variables de Entorno

Asegúrate de tener un archivo `.env` en la carpeta `backend/` con las siguientes variables:

```env
# Base de datos (usar la misma que CBD)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña

# O usar DATABASE_URL directamente (formato asyncpg)
DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost:5432/nombre_bd

# Seguridad
SECRET_KEY=tu_clave_secreta_muy_segura_aqui_cambiar_en_produccion
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Email (opcional, para notificaciones)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=tu_email@gmail.com
EMAIL_PASSWORD=tu_contraseña_de_aplicacion
EMAIL_FROM=tu_email@gmail.com

# Google OAuth (opcional)
GOOGLE_CLIENT_ID=tu_google_client_id
```

### 3. Inicializar la Base de Datos

Ejecuta el script de inicialización para crear las tablas y datos por defecto:

```bash
cd backend
python init_database.py
```

Este script:
- Crea el schema `sistema` si no existe
- Crea todas las tablas de autenticación
- Crea roles por defecto (admin, manager, user, viewer)
- Crea permisos por defecto
- Crea el usuario administrador:
  - **Usuario:** `admin`
  - **Contraseña:** `Admin123!`
  - **Email:** `rafadevstack@gmail.com`

⚠️ **IMPORTANTE:** Cambia la contraseña del admin después del primer login.

### 4. Instalar Dependencias del Frontend

```bash
cd frontend
npm install
```

La nueva dependencia es:
- `@react-oauth/google` - Para login con Google

### 5. Configurar Variables de Entorno del Frontend

Crea un archivo `.env` en la carpeta `frontend/` (opcional, solo si quieres login con Google):

```env
REACT_APP_GOOGLE_CLIENT_ID=tu_google_client_id
```

Si no configuras Google Client ID, el login con Google no estará disponible, pero el login tradicional funcionará.

### 6. Ejecutar el Sistema

**Backend:**
```bash
cd backend
python main.py
```

**Frontend:**
```bash
cd frontend
npm start
```

## 🔐 Flujo de Autenticación

1. Al acceder a la aplicación, se muestra primero la pantalla de login
2. El usuario puede:
   - Iniciar sesión con usuario y contraseña
   - Iniciar sesión con Google (si está configurado)
   - Solicitar recuperación de contraseña
3. Una vez autenticado, se muestra el panel principal de CBD Monitor
4. El token se guarda en `localStorage` y se verifica en cada carga
5. El usuario puede cerrar sesión desde el botón en el header

## 📁 Archivos Creados/Modificados

### Backend:
- `backend/auth_models.py` - Modelos de base de datos
- `backend/auth_schemas.py` - Esquemas Pydantic
- `backend/auth_security.py` - Seguridad y JWT
- `backend/auth_database.py` - Conexión a base de datos
- `backend/auth_email_service.py` - Servicio de emails
- `backend/auth_audit_utils.py` - Utilidades de auditoría
- `backend/init_database.py` - Script de inicialización
- `backend/routes/auth.py` - Endpoints de autenticación
- `backend/routes/notify.py` - Endpoints de notificaciones
- `backend/main.py` - Actualizado para incluir routers de auth
- `backend/requirements.txt` - Actualizado con nuevas dependencias

### Frontend:
- `frontend/src/components/Login.jsx` - Componente de login
- `frontend/src/components/Login.css` - Estilos del login
- `frontend/src/components/AuthWrapper.jsx` - Wrapper de autenticación
- `frontend/src/components/Header.jsx` - Actualizado con botón de logout
- `frontend/src/components/Header.css` - Estilos actualizados
- `frontend/src/App.jsx` - Actualizado para recibir props de auth
- `frontend/src/index.jsx` - Actualizado para usar AuthWrapper
- `frontend/package.json` - Actualizado con @react-oauth/google

## 🔒 Seguridad

- Las contraseñas se hashean con bcrypt
- Los tokens JWT expiran después de 8 horas (configurable)
- Los tokens se verifican en cada petición al backend
- Los logs de acceso y auditoría se registran automáticamente
- Los usuarios nuevos por Google se crean inactivos hasta aprobación del admin

## 📝 Notas Importantes

1. **No se modificó `App.jsx`** - El componente principal de CBD no fue modificado en su funcionalidad, solo se agregaron props opcionales para logout y usuario.

2. **Base de datos compartida** - El sistema de autenticación usa la misma base de datos que CBD, pero con un schema separado (`sistema`).

3. **Google OAuth opcional** - Si no configuras `GOOGLE_CLIENT_ID`, el login con Google no estará disponible, pero el sistema funcionará normalmente con login tradicional.

4. **Email opcional** - Si no configuras las variables de email, las notificaciones por email no funcionarán, pero el resto del sistema funcionará normalmente.

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'asyncpg'"
```bash
pip install asyncpg
```

### Error: "ModuleNotFoundError: No module named 'jose'"
```bash
pip install python-jose[cryptography]
```

### Error: "Google OAuth components must be used within GoogleOAuthProvider"
- Asegúrate de que `AuthWrapper.jsx` envuelva el componente `Login` con `GoogleOAuthProvider`
- Si no quieres usar Google, simplemente no configures `REACT_APP_GOOGLE_CLIENT_ID`

### Error: "DATABASE_URL no está configurada"
- Asegúrate de tener `DATABASE_URL` o las variables `DB_*` en tu archivo `.env`
- El formato debe ser: `postgresql+asyncpg://usuario:contraseña@host:puerto/nombre_bd`

## ✅ Verificación

Para verificar que todo funciona:

1. Ejecuta `python init_database.py` y verifica que se crean las tablas
2. Inicia el backend y verifica que no hay errores
3. Inicia el frontend y verifica que aparece la pantalla de login
4. Inicia sesión con `admin` / `Admin123!`
5. Verifica que puedes acceder al panel de CBD
6. Verifica que el botón de logout funciona
