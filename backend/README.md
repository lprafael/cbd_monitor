# CBD Monitor - Backend API

API desarrollada con FastAPI para monitorear el Control de Buses Distintos (CBD) de empresas operadoras de transporte.

## 🚀 Características

- **FastAPI**: Framework moderno y rápido para construir APIs
- **PostgreSQL**: Base de datos relacional para almacenar información operativa
- **Pydantic**: Validación de datos con modelos tipados
- **CORS**: Habilitado para integración con frontend

## 📚 Estructura del Proyecto

```
backend/
├── app/
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuración y variables de entorno
├── database/
│   ├── __init__.py
│   └── connection.py        # Conexión a PostgreSQL
├── models/
│   ├── __init__.py
│   └── schemas.py           # Modelos Pydantic
├── routes/
│   ├── __init__.py
│   ├── eots.py              # Endpoints de EOTs
│   ├── tipo_dia.py          # Endpoints de tipo de día
│   ├── franjas.py           # Endpoints de franjas operativas
│   └── cbd_data.py          # Endpoints de datos CBD
├── main.py                  # Aplicación principal
├── requirements.txt         # Dependencias
├── .env.example             # Ejemplo de variables de entorno
└── README.md                # Este archivo
```

## 🛠️ Instalación

### Prerequisitos

- Python 3.8 o superior
- PostgreSQL 12 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio o navegar a la carpeta del backend**

```bash
cd backend
```

2. **Crear un entorno virtual (recomendado)**

```bash
python -m venv venv

# En Linux/Mac
source venv/bin/activate

# En Windows
venv\Scripts\activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Copiar el archivo `.env.example` a `.env` y configurar las credenciales:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales de PostgreSQL:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña

PORT=8000
HOST=0.0.0.0
```

## 🚀 Ejecución

### Modo Desarrollo

```bash
python main.py
```

O usando uvicorn directamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Modo Producción
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

La API estará disponible en: `http://localhost:8000`

## 📜 Documentación de la API

FastAPI genera documentación automática interactiva:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔌 Endpoints Disponibles

### 1. EOTs (Empresas Operadoras de Transporte)

```
GET /api/eots
```

Obtiene la lista de todas las empresas operadoras.

### 2. Tipo de Día

```
GET /api/tipo-dia/{fecha}
```

Determina el tipo de día (LABORAL, SABADO, NO LABORAL) basado en una fecha.

**Parámetros:**
- `fecha`: Fecha en formato YYYY-MM-DD

### 3. Franjas Operativas

```
GET /api/franjas/{id_tipo_dia}
```

Obtiene las franjas operativas activas para un tipo de día.

**Parámetros:**
- `id_tipo_dia`: ID del tipo de día (5=LABORAL, 6=SABADO, 7=NO LABORAL)

### 4. Datos CBD

```
POST /api/cbd-data
```

Obtiene datos completos de CBD para EOTs seleccionados.

**Body (JSON):**
```json
{
  "eot_ids": [1, 2, 3],
  "fecha": "2025-12-05",
  "modo_visualizacion": "franja"  // "hora" o "franja"
}
```

**Respuesta:**
- Franjas operativas según tipo de día
- Para cada EOT: dos filas de datos (servicios_diarios y cbd_detalle_buses)
- Conteo de buses por franja/hora
- Validación contra parámetros mínimos

## 📊 Estructura de Base de Datos

### Tablas Utilizadas

1. **public.eots**: Empresas operadoras
2. **public.servicios_diarios**: Servicios diarios de buses
3. **control_metricas.cbd_detalle_buses**: Detalle de buses en CBD
4. **control_metricas.cbd_parametros_minimos**: Parámetros mínimos de validación
5. **control_metricas.franjas_operativas**: Franjas horarias operativas
6. **control_metricas.tipo_dia**: Tipos de día

## ⚠️ Notas Importantes

- Asegúrate de que tu base de datos PostgreSQL tenga las tablas mencionadas
- Las credenciales en `.env` son sensibles, nunca las subas al control de versiones
- En producción, configura CORS con dominios específicos en lugar de `*`

## 🐛 Troubleshooting

### Error de conexión a la base de datos

Verifica:
1. Que PostgreSQL esté ejecutándose
2. Las credenciales en el archivo `.env`
3. Que el usuario tenga permisos en las tablas

### Error de importación de módulos

Asegúrate de haber activado el entorno virtual y ejecuta:
```bash
pip install -r requirements.txt
```

## 📝 Lógica de Negocio

### Determinación de Tipo de Día

- **Lunes a Viernes**: `id_tipo_dia = 5` (LABORAL)
- **Sábado**: `id_tipo_dia = 6` (SABADO)
- **Domingo**: `id_tipo_dia = 7` (NO LABORAL)

### Validación de CBD

Cada celda muestra un check (✓) si la cantidad de buses cumple con:
- `cbd_minimo_franja` cuando `modo_visualizacion = "franja"`
- `cbd_minimo_hora` cuando `modo_visualizacion = "hora"`

## 💬 Soporte

Para reportar problemas o solicitar funcionalidades, por favor contacta al equipo de desarrollo.
