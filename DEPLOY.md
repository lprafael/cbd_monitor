# 🚀 Guía de Despliegue - CBD Monitor

Esta guía te ayudará a desplegar CBD Monitor en el servidor 172.16.222.222 usando Docker.

## 📋 Prerequisitos

- Acceso SSH al servidor 172.16.222.222
- Docker y Docker Compose instalados en el servidor
- Acceso a la base de datos PostgreSQL
- Credenciales de la base de datos

## 📦 Paso 1: Preparar los archivos en tu máquina local

1. Asegúrate de tener todos los archivos necesarios:
   - `docker-compose.yml` (en la raíz del proyecto)
   - `backend/Dockerfile`
   - `frontend/Dockerfile`
   - `.env.example`

## 📤 Paso 2: Subir el proyecto a GitHub y desplegar

### Paso 2.1: Subir el proyecto a GitHub (desde tu máquina local)

1. **Inicializar el repositorio Git** (si aún no lo has hecho):
```bash
# En tu máquina local, en el directorio del proyecto
git init
git add .
git commit -m "Initial commit: CBD Monitor"
```

2. **Crear un repositorio en GitHub**:
   - Ve a https://github.com y crea un nuevo repositorio
   - No inicialices con README, .gitignore o licencia (ya los tenemos)

3. **Conectar y subir a GitHub**:
```bash
# Reemplaza <tu-usuario> y <nombre-repo> con tus valores
git remote add origin https://github.com/<tu-usuario>/<nombre-repo>.git
git branch -M main
git push -u origin main
```

### Paso 2.2: Clonar y desplegar en el servidor

1. **Conecta al servidor y clona el repositorio**:
```bash
ssh user@172.16.222.222
cd /home/user
git clone https://github.com/<tu-usuario>/<nombre-repo>.git cbd_monitor
cd cbd_monitor
```

**Nota**: Si el repositorio es privado, necesitarás configurar autenticación SSH o usar un token de acceso personal.

## ⚙️ Paso 3: Configurar variables de entorno en el servidor

1. Conecta al servidor:
```bash
ssh user@172.16.222.222
cd /home/user/cbd_monitor
```

2. Crea el archivo `.env` basado en `.env.example`:
```bash
cp .env.example .env
nano .env  # o usa el editor que prefieras
```

3. Edita el archivo `.env` con tus credenciales reales:
```env
# Configuración de Base de Datos PostgreSQL
DB_HOST=localhost  # o la IP de tu servidor de BD
DB_PORT=5432
DB_NAME=nombre_de_tu_base_de_datos
DB_USER=tu_usuario_db
DB_PASSWORD=tu_contraseña_db

# URL de la API para el frontend
REACT_APP_API_URL=http://172.16.222.222:5000
```

**⚠️ IMPORTANTE:** 
- Si tu base de datos está en otro servidor, cambia `DB_HOST` a la IP correspondiente
- Asegúrate de que el puerto 5000 esté disponible (no está siendo usado por otro servicio)

## 🐳 Paso 4: Construir y ejecutar los contenedores

1. Construir las imágenes Docker:
```bash
docker-compose build
```

2. Iniciar los contenedores:
```bash
docker-compose up -d
```

3. Verificar que los contenedores estén corriendo:
```bash
docker-compose ps
```

4. Ver los logs para verificar que todo funcione correctamente:
```bash
# Logs del backend
docker-compose logs -f cbd-monitor-backend

# Logs del frontend
docker-compose logs -f cbd-monitor-frontend

# Todos los logs
docker-compose logs -f
```

## ✅ Paso 5: Verificar el despliegue

1. **Backend**: Abre en tu navegador:
   - API: http://172.16.222.222:5000
   - Health check: http://172.16.222.222:5000/health
   - Documentación: http://172.16.222.222:5000/docs

2. **Frontend**: Abre en tu navegador:
   - Aplicación: http://172.16.222.222:8080
   
**Nota**: El frontend está configurado en el puerto 8080 porque el puerto 80 está ocupado por `validaciones-frontend`.

## 🔄 Comandos útiles para gestión

### Detener los contenedores
```bash
docker-compose down
```

### Reiniciar los contenedores
```bash
docker-compose restart
```

### Ver el estado de los contenedores
```bash
docker-compose ps
```

### Ver los logs
```bash
docker-compose logs -f [nombre-servicio]
```

### Reconstruir después de cambios
```bash
# Detener y eliminar contenedores
docker-compose down

# Reconstruir imágenes
docker-compose build --no-cache

# Iniciar de nuevo
docker-compose up -d
```

### Actualizar solo el código (sin reconstruir)
```bash
# Si solo cambiaste código Python o React, puedes hacer:
docker-compose restart
```

## 🛠️ Solución de problemas

### El backend no se conecta a la base de datos

1. Verifica las credenciales en `.env`
2. Verifica que PostgreSQL esté corriendo y accesible:
```bash
# Desde el servidor
psql -h localhost -U tu_usuario -d tu_base_de_datos
```

3. Verifica los logs:
```bash
docker-compose logs cbd-monitor-backend
```

### El frontend no puede comunicarse con el backend

1. Verifica que `REACT_APP_API_URL` en `.env` sea correcta
2. Verifica que el backend esté corriendo:
```bash
curl http://172.16.222.222:5000/health
```

3. Si cambiaste `REACT_APP_API_URL`, necesitas reconstruir el frontend:
```bash
docker-compose build --no-cache cbd-monitor-frontend
docker-compose up -d cbd-monitor-frontend
```

### Puerto 80 ya está en uso

El puerto 80 ya está siendo usado por `validaciones-frontend`, por lo que el proyecto está configurado para usar el puerto **8080** para el frontend. Esto ya está configurado en `docker-compose.yml`.

Si necesitas cambiar a otro puerto, edita `docker-compose.yml`:
```yaml
cbd-monitor-frontend:
  ports:
    - "8080:80"  # Cambiar 8080 por el puerto que prefieras
```

### Actualizar desde GitHub

Para actualizar el proyecto en el servidor con los últimos cambios:

```bash
# En el servidor
cd /home/user/cbd_monitor
git pull origin main

# Reconstruir y reiniciar los contenedores
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Los contenedores muestran "unhealthy"

1. Verifica los health checks:
```bash
docker inspect cbd-monitor-backend | grep -A 10 Health
docker inspect cbd-monitor-frontend | grep -A 10 Health
```

2. Revisa los logs para ver qué está fallando:
```bash
docker-compose logs [nombre-servicio]
```

## 📝 Notas importantes

- Los contenedores se reiniciarán automáticamente si fallan (`restart: unless-stopped`)
- Los health checks verifican que los servicios estén funcionando correctamente
- El frontend está configurado para hacer proxy de las peticiones `/api` al backend
- Asegúrate de tener suficiente espacio en disco para las imágenes Docker

## 🔒 Seguridad

- **Nunca** subas el archivo `.env` al control de versiones
- Usa contraseñas seguras para la base de datos
- Considera usar un firewall para proteger los puertos expuestos
- En producción, configura CORS en el backend para dominios específicos

## 📞 Soporte

Si encuentras problemas durante el despliegue, revisa:
1. Los logs de los contenedores
2. La configuración de `.env`
3. La conectividad de red y puertos
4. Los permisos de la base de datos

---

¡Listo! Tu aplicación CBD Monitor debería estar corriendo en el servidor. 🎉
