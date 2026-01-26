# 🚌 CBD Monitor - Sistema de Monitoreo de Control de Buses Distintos

Sistema full-stack completo para monitorear el Control de Buses Distintos (CBD) de empresas operadoras de transporte público.

## 📋 Descripción

CBD Monitor es una aplicación web que permite visualizar y analizar la disponibilidad de buses en operación para diferentes empresas operadoras de transporte (EOT). El sistema compara datos de dos fuentes (`servicios_diarios` y `cbd_detalle_buses`) y valida contra parámetros mínimos establecidos.

## ✨ Características Principales

- 📊 **Visualización Flexible**: Ver datos por franja horaria o por hora
- 🏢 **Múltiples EOTs**: Seleccionar y comparar varias empresas simultáneamente
- ✅ **Validación Automática**: Checks visuales cuando se cumplen parámetros mínimos
- 📅 **Análisis por Fecha**: Consultar datos históricos por día
- 🎨 **Interfaz Moderna**: Diseño responsivo y atractivo
- 📱 **Responsive**: Funciona en móviles, tablets y escritorio

## 🏗️ Arquitectura

El proyecto está dividido en dos componentes principales:

### Backend (FastAPI + PostgreSQL)
- **Framework**: FastAPI
- **Base de Datos**: PostgreSQL
- **ORM/Driver**: psycopg2
- **Validación**: Pydantic

### Frontend (React)
- **Framework**: React 18
- **Estilo**: CSS personalizado
- **Build Tool**: Create React App

```
cbd_monitor/
├── backend/              # API REST con FastAPI
│   ├── config/          # Configuración y variables de entorno
│   ├── database/        # Conexión a PostgreSQL
│   ├── models/          # Modelos Pydantic
│   ├── routes/          # Endpoints de la API
│   └── main.py          # Aplicación principal
│
├── frontend/            # Aplicación React
│   ├── src/
│   │   ├── components/  # Componentes React
│   │   ├── App.jsx      # Componente principal
│   │   └── index.jsx    # Punto de entrada
│   └── public/          # Archivos estáticos
│
└── README.md            # Este archivo
```

## 🚀 Inicio Rápido

### Prerequisitos

- Python 3.8 o superior
- Node.js 14 o superior
- PostgreSQL 12 o superior
- npm o yarn

### Instalación Completa

#### 1. Clonar o descargar el proyecto

```bash
cd /home/ubuntu/cbd_monitor
```

#### 2. Configurar Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL

# Ejecutar servidor
python main.py
```

El backend estará disponible en: `http://localhost:8000`

#### 3. Configurar Frontend

```bash
cd ../frontend

# Instalar dependencias
npm install

# Configurar variables de entorno (opcional)
cp .env.example .env

# Ejecutar aplicación
npm start
```

El frontend estará disponible en: `http://localhost:3000`

## 📊 Estructura de Base de Datos

El sistema utiliza las siguientes tablas de PostgreSQL:

### Schema: `public`
- **eots**: Empresas operadoras de transporte
- **servicios_diarios**: Registro de servicios diarios de buses

### Schema: `control_metricas`
- **cbd_detalle_buses**: Detalle de buses en CBD
- **cbd_parametros_minimos**: Parámetros mínimos de validación
- **franjas_operativas**: Definición de franjas horarias
- **tipo_dia**: Tipos de día (LABORAL, SABADO, NO LABORAL)

### Relaciones Principales

```
public.eots.cod_catalogo = public.servicios_diarios.id_eot_catalogo
control_metricas.franjas_operativas.id_tipo_dia = control_metricas.tipo_dia.id_tipo_dia
control_metricas.cbd_parametros_minimos.id_tipo_dia = control_metricas.tipo_dia.id_tipo_dia
```

## 🔌 API Endpoints

### GET `/api/eots`
Obtiene lista de todas las empresas operadoras.

### GET `/api/tipo-dia/{fecha}`
Determina el tipo de día basado en una fecha.

**Parámetros:**
- `fecha`: YYYY-MM-DD

### GET `/api/franjas/{id_tipo_dia}`
Obtiene franjas operativas activas para un tipo de día.

**Parámetros:**
- `id_tipo_dia`: 5=LABORAL, 6=SABADO, 7=NO LABORAL

### POST `/api/cbd-data`
Obtiene datos completos de CBD.

**Body:**
```json
{
  "eot_ids": [1, 2, 3],
  "fecha": "2025-12-05",
  "modo_visualizacion": "franja"
}
```

## 📖 Documentación de la API

FastAPI genera documentación automática interactiva:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 Lógica de Negocio

### Determinación de Tipo de Día

El sistema determina automáticamente el tipo de día:

| Día de la Semana | id_tipo_dia | Nombre |
|------------------|-------------|---------|
| Lunes - Viernes  | 5           | LABORAL |
| Sábado           | 6           | SABADO  |
| Domingo          | 7           | NO LABORAL |

### Validación de Parámetros Mínimos

Para cada celda en la tabla:
- **Modo Franja**: Se valida contra `cbd_minimo_franja`
- **Modo Hora**: Se valida contra `cbd_minimo_hora`

Si la cantidad de buses cumple o supera el mínimo, se muestra un check (✓).

### Doble Fila por EOT

El sistema muestra dos filas por cada empresa:
1. **Servicios Diarios**: Datos de `public.servicios_diarios`
2. **CBD Detalle Buses**: Datos de `control_metricas.cbd_detalle_buses`

Esto permite comparar ambas fuentes de información.

## 🎨 Capturas de Pantalla

### Header con Controles
- Selector múltiple de EOTs
- Selector de fecha
- Radio buttons para modo de visualización
- Botón "Obtener Datos"

### Tabla de Datos
- Dos filas por EOT (servicios_diarios y cbd_detalle_buses)
- Columnas dinámicas según franjas u horas
- Checks verdes cuando se cumplen parámetros
- Advertencias cuando no se cumplen
- Totales por fila

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **Pydantic**: Validación de datos
- **psycopg2**: Driver de PostgreSQL
- **uvicorn**: Servidor ASGI
- **python-dotenv**: Gestión de variables de entorno

### Frontend
- **React**: Librería para interfaces de usuario
- **CSS3**: Estilos personalizados con gradientes
- **Fetch API**: Comunicación con el backend

## ⚙️ Configuración

### Variables de Entorno del Backend

Archivo: `backend/.env`

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
PORT=8000
HOST=0.0.0.0
```

### Variables de Entorno del Frontend

Archivo: `frontend/.env`

```env
REACT_APP_API_URL=http://localhost:8000
```

## 🧪 Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

## 📦 Despliegue en Producción

### Backend

1. Configurar servidor (Ubuntu/Debian):

```bash
# Instalar dependencias
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Configurar aplicación
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar con gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. Configurar nginx como proxy reverso

### Frontend

```bash
# Compilar para producción
npm run build

# Servir con nginx o cualquier servidor web
```

## 🐛 Troubleshooting

### Backend no se conecta a la base de datos

1. Verifica las credenciales en `.env`
2. Confirma que PostgreSQL esté ejecutándose
3. Verifica permisos del usuario en las tablas

### Frontend no puede conectar con el backend

1. Verifica que el backend esté ejecutándose en el puerto correcto
2. Revisa la URL en `REACT_APP_API_URL`
3. Confirma que CORS esté habilitado en el backend

### Errores de permisos en tablas

Ejecuta en PostgreSQL:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tu_usuario;
GRANT SELECT ON ALL TABLES IN SCHEMA control_metricas TO tu_usuario;
```

## 📝 Notas Importantes

- ⚠️ **Nunca subas** el archivo `.env` al control de versiones
- 🔒 En producción, configura CORS con dominios específicos
- 🔑 Usa contraseñas seguras para la base de datos
- 🚀 Considera usar un gestor de procesos como `systemd` o `supervisor` para el backend
- 📊 Configura logs adecuados para monitoreo en producción

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es para uso interno. Todos los derechos reservados.

## 👥 Equipo de Desarrollo

Desarrollado para el monitoreo y control de operaciones de transporte público.

## 📞 Soporte

Para soporte técnico o preguntas, contacta al equipo de desarrollo.

---

**Nota sobre localhost:** El localhost mencionado en este documento se refiere al localhost de la computadora donde ejecutas la aplicación, no tu máquina local. Para acceder desde tu máquina, necesitarás desplegar la aplicación en tu propio sistema o configurar un túnel/proxy apropiado.

---

Hecho con ❤️ para mejorar el monitoreo del transporte público
