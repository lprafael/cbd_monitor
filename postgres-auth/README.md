# Postgres Auth (Opción A)

PostgreSQL en contenedor para **autenticación/usuarios** (login). Se despliega por separado en el servidor y las aplicaciones (p. ej. cbd_monitor) se conectan por red.

## Despliegue en el servidor (172.16.222.222)

1. Crear directorio y copiar este contenido, por ejemplo:
   ```bash
   mkdir -p /home/user/postgres-auth
   # Copiar docker-compose.yml, .env.example y la carpeta init/
   ```

2. Configurar variables:
   ```bash
   cd /home/user/postgres-auth
   cp .env.example .env
   # Editar .env y definir POSTGRES_PASSWORD (y opcionalmente POSTGRES_USER, POSTGRES_DB, POSTGRES_PORT)
   ```

3. Levantar y dejar activo:
   ```bash
   docker compose up -d
   ```

4. Comprobar:
   ```bash
   docker compose ps
   docker compose logs -f postgres-auth
   ```

El servicio queda escuchando en **puerto 5433** del host (configurable con `POSTGRES_PORT`). En el primer arranque se ejecuta `init/00_schema_sistema.sql` (crea el schema `sistema`).

### Inicializar tablas de auth para cbd_monitor (obligatorio)

El backend de cbd_monitor usa **schema `sistema`** y la tabla **`sistema.usuarios`** (no `public.usuarios`). Hay que ejecutar **una vez** el script de inicialización del backend contra esta BD:

Desde el servidor (o desde tu PC con acceso a la BD):

```bash
cd /ruta/a/cbd_monitor/backend
export AUTH_DB_HOST=172.16.222.222   # o el host donde corre postgres-auth
export AUTH_DB_PORT=5433
export AUTH_DB_NAME=cbd_auth
export AUTH_DB_USER=cbd_auth
export AUTH_DB_PASSWORD=tu_password_del_.env_de_postgres-auth
python init_database.py
```

Si el backend corre en Docker y postgres-auth está en el mismo host, desde dentro del contenedor (con las mismas variables que ya usa el backend):

```bash
docker exec -it cbd-monitor-backend python init_database.py
```

Eso crea las tablas `sistema.usuarios`, `sistema.roles`, etc. y un usuario **admin** (la contraseña se muestra en la salida del script). Sin este paso, el login falla con `relation "sistema.usuarios" does not exist`.

## Conexión desde pgAdmin (u otro cliente)

Desde tu PC, usando la IP del servidor donde corre postgres-auth:

| Campo | Valor |
|-------|--------|
| **Host** | `172.16.222.222` (IP del servidor) |
| **Port** | `5433` |
| **Database** | `cbd_auth` |
| **Username** | `cbd_auth` |
| **Password** | El valor de `POSTGRES_PASSWORD` del `.env` de postgres-auth |

## Conexión desde cbd_monitor

En el `.env` del proyecto cbd_monitor (junto a `docker-compose.yml`) añadir:

```env
# BD de autenticación (Postgres local en el servidor)
AUTH_DB_HOST=172.16.222.222
AUTH_DB_PORT=5433
AUTH_DB_NAME=cbd_auth
AUTH_DB_USER=cbd_auth
AUTH_DB_PASSWORD=el_mismo_password_del_.env_de_postgres-auth
```

Si cbd_monitor se ejecuta **en el mismo host** que postgres-auth, se puede usar `AUTH_DB_HOST=172.16.222.222` o `localhost`.

## Reinicio con el servidor

El contenedor usa `restart: unless-stopped`, por lo que se mantendrá activo y se iniciará al arrancar el servidor.

## Problemas frecuentes

- **WARN: The "uH" variable is not set**  
  Suele deberse a un `.env` con line endings de Windows (CRLF) o a nombres de variable incorrectos. Asegurate de que el `.env` use **solo LF** (no CRLF) y que las claves sean exactamente: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`.

- **FATAL: password authentication failed for user "cbd_auth"**  
  La contraseña que usa el cliente no coincide con la de Postgres. Comprobá que:
  1. En **postgres-auth/.env** tenés `POSTGRES_PASSWORD=tu_password`.
  2. En el **.env de cbd_monitor** (donde está el docker-compose del backend) tenés `AUTH_DB_PASSWORD=el_mismo_password`.
  3. Si acabás de cambiar la contraseña en postgres-auth, reiniciá el contenedor: `docker compose down && docker compose up -d` (cambiar la contraseña después del primer init requiere reconfigurar Postgres o cambiar el usuario desde dentro del contenedor).

  Probar conexión desde el servidor:
  ```bash
  PGPASSWORD=tu_password psql -h 127.0.0.1 -p 5433 -U cbd_auth -d cbd_auth -c "SELECT 1"
  ```

## Backup del volumen

Los datos persisten en el volumen `postgres_auth_data`. Para backup:

```bash
docker exec postgres-auth pg_dump -U cbd_auth cbd_auth > backup_auth_$(date +%Y%m%d).sql
```
