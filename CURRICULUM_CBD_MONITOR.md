# CBD Monitor — Texto para currículum

Puedes copiar y adaptar las siguientes secciones según el formato de tu CV (experiencia laboral, proyectos, competencias).

---

## Título corto (una línea)

**Desarrollo full-stack del sistema CBD Monitor — monitoreo de Control de Buses Distintos para transporte público**

---

## Descripción para "Experiencia" o "Proyectos" (párrafo)

Desarrollo y mantenimiento del **CBD Monitor**, sistema web full-stack para el monitoreo del Control de Buses Distintos (CBD) de empresas operadoras de transporte público. Responsable del diseño de la arquitectura, backend API REST con **FastAPI** y **PostgreSQL**, y frontend con **React 18**. El sistema cruza datos de servicios diarios y CBD detalle de buses, valida contra parámetros mínimos por franja/hora y tipo de día (laboral, sábado, no laboral), y expone múltiples vistas: datos en vivo por franja u hora, dashboards de desempeño e índices, desempeño mensual y verificación 290. Incluye contenedorización con **Docker** y **Docker Compose**, documentación OpenAPI (Swagger/ReDoc), temas de interfaz y exportación a PDF.

---

## Descripción breve (2–3 líneas, para listas)

- **CBD Monitor**: sistema full-stack (FastAPI + React + PostgreSQL) para monitoreo de Control de Buses Distintos; arquitectura en contenedores (Docker), API REST modular, dashboards de desempeño e índices, validación por parámetros mínimos y franjas operativas.

---

## Puntos por competencias (para listas con viñetas)

### Arquitectura y backend
- Diseño e implementación de arquitectura **full-stack** desacoplada (API REST + SPA).
- **Backend** en **FastAPI** (Python): rutas modulares (EOTs, tipo de día, franjas, CBD, desempeño, verify-290), **Pydantic** para validación, **psycopg2**/SQLAlchemy para **PostgreSQL**.
- Uso de **múltiples schemas** en PostgreSQL (`public`, `control_metricas`) y lógica de negocio por tipo de día y franjas operativas.
- Documentación automática de la API (**Swagger UI**, **ReDoc**), health checks y CORS.

### Frontend
- **Frontend** en **React 18** (Create React App): componentes reutilizables (Header, tablas, dashboards).
- Múltiples **vistas/dashboards**: datos CBD en vivo (por franja/hora), desempeño, índices, desempeño mensual, verificación 290.
- Interfaz **responsive**, temas configurables (ejecutivo, institucional, nocturno, etc.) y persistencia en `localStorage`.
- Integración con API (fetch), manejo de estados, carga y errores; exportación a PDF (jsPDF, html2canvas).

### DevOps e infraestructura
- **Docker** y **Docker Compose**: dos servicios (backend y frontend), red bridge, variables de entorno y health checks en los contenedores.
- Configuración por entornos (`.env`), preparado para despliegue en servidor (por ejemplo con Nginx y Gunicorn).

### Dominio
- Conocimiento del dominio de **transporte público**: CBD, EOTs, parámetros mínimos, franjas operativas, Resolución GVMT Nº 120/2025.

---

## Tecnologías (para sección "Tecnologías" del CV)

**Backend:** Python, FastAPI, Pydantic, PostgreSQL, psycopg2, SQLAlchemy, Uvicorn  
**Frontend:** React 18, JavaScript (JSX), CSS3  
**Infraestructura:** Docker, Docker Compose  
**Herramientas:** Git, OpenAPI/Swagger, jsPDF  

---

## Ejemplo de entrada en "Experiencia laboral"

**Desarrollador Full-Stack — Proyecto CBD Monitor**  
*[Fecha inicio] – [Fecha fin / Actualidad]*

- Desarrollo del sistema **CBD Monitor** para monitoreo del Control de Buses Distintos (CBD) de empresas operadoras de transporte.
- Arquitectura: backend **FastAPI** + **PostgreSQL**, frontend **React 18**, despliegue con **Docker Compose**.
- Implementación de API REST modular (EOTs, franjas, CBD, desempeño, verify-290), validación con Pydantic y consultas multi-schema.
- Diseño de interfaz con múltiples dashboards (datos en vivo, desempeño, índices, mensual, verificación 290), temas y exportación a PDF.
- Documentación de API (Swagger/ReDoc), health checks y configuración por entornos.

---

## Ejemplo para "Proyectos personales / técnicos"

**CBD Monitor**  
Sistema web de monitoreo de Control de Buses Distintos (transporte público).  
Stack: FastAPI, React 18, PostgreSQL, Docker. Incluye API REST modular, varios dashboards (CBD en vivo, desempeño, índices, mensual, verify-290), validación por parámetros mínimos y franjas operativas, y documentación OpenAPI.

---

*Documento generado a partir del repositorio CBD Monitor. Ajusta fechas, empresa y nivel de detalle según tu CV.*
