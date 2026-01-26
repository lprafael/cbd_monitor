# CBD Monitor - Frontend React

Aplicación frontend desarrollada con React para monitorear el Control de Buses Distintos (CBD) de empresas operadoras de transporte.

## 🚀 Características

- **React 18**: Framework moderno para construir interfaces de usuario
- **Diseño Responsivo**: Adaptable a diferentes tamaños de pantalla
- **Componentes Modulares**: Arquitectura limpia y reutilizable
- **Estilos Modernos**: CSS personalizado con gradientes y animaciones
- **Integración con API**: Comunicación fluida con el backend FastAPI

## 📚 Estructura del Proyecto

```
frontend/
├── public/
│   ├── index.html           # HTML base
│   └── manifest.json        # Configuración PWA
├── src/
│   ├── components/
│   │   ├── Header.jsx       # Componente de header con controles
│   │   ├── Header.css       # Estilos del header
│   │   ├── CBDTable.jsx     # Componente de tabla de datos
│   │   └── CBDTable.css     # Estilos de la tabla
│   ├── App.jsx              # Componente principal
│   ├── App.css              # Estilos de la app
│   ├── index.jsx            # Punto de entrada
│   └── index.css            # Estilos globales
├── package.json             # Dependencias y scripts
├── .env.example             # Ejemplo de variables de entorno
├── .gitignore               # Archivos ignorados por git
└── README.md                # Este archivo
```

## 🛠️ Instalación

### Prerequisitos

- Node.js 14 o superior
- npm (incluido con Node.js) o yarn
- Backend API ejecutándose (ver carpeta backend)

### Pasos de Instalación

1. **Navegar a la carpeta del frontend**

```bash
cd frontend
```

2. **Instalar dependencias**

```bash
npm install
```

O si prefieres usar yarn:

```bash
yarn install
```

3. **Configurar variables de entorno (opcional)**

Copiar el archivo `.env.example` a `.env` si necesitas cambiar la URL de la API:

```bash
cp .env.example .env
```

Editar `.env` si tu backend está en una URL diferente:

```env
REACT_APP_API_URL=http://localhost:8000
```

## 🚀 Ejecución

### Modo Desarrollo

```bash
npm start
```

O con yarn:

```bash
yarn start
```

La aplicación se abrirá automáticamente en: `http://localhost:3000`

### Compilar para Producción

```bash
npm run build
```

Esto creará una carpeta `build/` con los archivos optimizados para producción.

### Ejecutar Tests

```bash
npm test
```

## 📱 Uso de la Aplicación

### 1. Seleccionar EOTs

En el header, selecciona una o más Empresas Operadoras de Transporte (EOT):
- Mantén presionado **Ctrl** (Windows) o **Cmd** (Mac) para seleccionar múltiples
- También puedes mantener **Shift** para seleccionar un rango

### 2. Seleccionar Fecha

Elige la fecha para la cual deseas ver los datos de CBD.

### 3. Modo de Visualización

Selecciona cómo quieres visualizar los datos:
- **Por Franja**: Agrupa los datos por franjas operativas (Pico mañana, Valle, Pico tarde, etc.)
- **Por Hora**: Muestra los datos hora por hora (0:00 - 23:00)

### 4. Obtener Datos

Haz clic en el botón **"Obtener Datos"** para cargar los datos.

### 5. Interpretar la Tabla

La tabla muestra para cada EOT seleccionado:

- **Fila 1 (Servicios Diarios)**: Cantidad de buses según `servicios_diarios`
- **Fila 2 (CBD Detalle Buses)**: Cantidad de buses según `cbd_detalle_buses`

Cada celda muestra:
- **Número**: Cantidad de buses
- **✓ (Check verde)**: Cumple con el parámetro mínimo
- **⚠️ (Advertencia)**: No cumple con el parámetro mínimo
- **Min: X**: Parámetro mínimo requerido

## 🎨 Componentes

### Header

Componente que contiene todos los controles de selección:
- Selector múltiple de EOTs
- Selector de fecha
- Radio buttons para modo de visualización
- Botón de consulta

### CBDTable

Componente que renderiza la tabla de datos:
- Cabeceras dinámicas según modo de visualización
- Dos filas por EOT
- Validación visual con checks
- Columnas sticky para mejor navegación
- Leyenda explicativa

### App

Componente principal que:
- Gestiona el estado global
- Realiza llamadas a la API
- Maneja errores y loading
- Coordina los componentes

## 🔌 Integración con API

La aplicación consume los siguientes endpoints del backend:

- `GET /api/eots` - Obtener lista de EOTs
- `POST /api/cbd-data` - Obtener datos de CBD

El formato de la solicitud POST:

```json
{
  "eot_ids": [1, 2, 3],
  "fecha": "2025-12-05",
  "modo_visualizacion": "franja"
}
```

## 🎨 Personalización

### Cambiar Colores

Los colores principales están definidos en `src/index.css`:

```css
:root {
  --primary-color: #667eea;
  --secondary-color: #764ba2;
  --dark-color: #2c3e50;
  /* ... más variables */
}
```

### Modificar Estilos

Cada componente tiene su propio archivo CSS:
- `Header.css` - Estilos del header
- `CBDTable.css` - Estilos de la tabla
- `App.css` - Estilos globales de la app

## 📱 Responsive

La aplicación es totalmente responsive y se adapta a:
- 📱 Móviles (< 768px)
- 📱 Tablets (768px - 1024px)
- 💻 Escritorio (> 1024px)

## ⚠️ Notas Importantes

- Asegúrate de que el backend esté ejecutándose antes de iniciar el frontend
- El frontend por defecto busca el backend en `http://localhost:8000`
- Si cambias el puerto del backend, actualiza la variable de entorno `REACT_APP_API_URL`

## 🐛 Troubleshooting

### Error de conexión con la API

**Problema**: "No se pudieron cargar las empresas operadoras"

**Solución**:
1. Verifica que el backend esté ejecutándose
2. Confirma la URL de la API en `.env`
3. Revisa la consola del navegador para más detalles

### La aplicación no inicia

**Problema**: Errores al ejecutar `npm start`

**Solución**:
1. Elimina `node_modules` y `package-lock.json`
2. Ejecuta `npm install` nuevamente
3. Asegúrate de tener Node.js 14 o superior

### Estilos no se aplican correctamente

**Problema**: La aplicación se ve sin estilos

**Solución**:
1. Verifica que los archivos CSS estén en las carpetas correctas
2. Limpia la caché del navegador (Ctrl + Shift + R)
3. Reinicia el servidor de desarrollo

## 🌐 Despliegue

### Despliegue en Netlify

1. Ejecuta `npm run build`
2. Sube la carpeta `build/` a Netlify
3. Configura las variables de entorno en Netlify

### Despliegue en Vercel

1. Conecta tu repositorio a Vercel
2. Vercel detectará automáticamente que es una app React
3. Configura `REACT_APP_API_URL` en las variables de entorno

### Servidor propio

1. Ejecuta `npm run build`
2. Sirve la carpeta `build/` con un servidor web (nginx, Apache, etc.)

Ejemplo con `serve`:
```bash
npm install -g serve
serve -s build -p 3000
```

## 📝 Scripts Disponibles

- `npm start` - Inicia el servidor de desarrollo
- `npm run build` - Compila la aplicación para producción
- `npm test` - Ejecuta los tests
- `npm run eject` - Expone la configuración de webpack (⚠️ irreversible)

## 💡 Mejoras Futuras

- [ ] Exportar datos a Excel/PDF
- [ ] Gráficos interactivos con Chart.js
- [ ] Comparación entre múltiples fechas
- [ ] Filtros avanzados
- [ ] Notificaciones push
- [ ] Modo oscuro

## 📧 Soporte

Para reportar problemas o solicitar funcionalidades, por favor contacta al equipo de desarrollo.

---

Desarrollado con ❤️ usando React
