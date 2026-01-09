# 📋 Instrucciones para usar el workflow de n8n - Calcular IFO

## 🎯 Descripción

Este workflow de n8n permite calcular IFO según Resolución 120/2025 de forma automatizada, llamando al endpoint de la API del backend.

## 📦 Archivos necesarios

1. **`n8n_workflow_calcular_ifo.json`** - Workflow de n8n para importar
2. **Endpoint del backend**: `POST /api/ifo/calcular` (ya está implementado)

## 🚀 Pasos para configurar en n8n

### 1. Importar el workflow

1. Accede a n8n: http://172.16.222.222:5678/home/workflows
2. Haz clic en **"Import from File"** o **"Import from URL"**
3. Selecciona el archivo `n8n_workflow_calcular_ifo.json`
4. El workflow se importará con todos los nodos configurados

### 2. Configurar el endpoint (si es necesario)

El workflow ya está configurado para usar:
- **URL**: `http://172.16.222.222:5001/api/ifo/calcular`
- **Método**: POST
- **Parámetros**:
  - `fecha`: Fecha a procesar (formato YYYY-MM-DD). Por defecto usa el día anterior.
  - `solo_calculo`: `true` para solo calcular, `false` para incluir detalles de incumplimientos

### 3. Personalizar el Schedule Trigger

El workflow está configurado para ejecutarse automáticamente todos los días a las 2:00 AM. Puedes modificarlo:

1. Haz clic en el nodo **"Schedule Trigger"**
2. Cambia la expresión cron según necesites:
   - `0 2 * * *` - Todos los días a las 2:00 AM
   - `0 0 * * *` - Todos los días a medianoche
   - `0 8 * * 1-5` - Lunes a Viernes a las 8:00 AM

### 4. Ejecutar manualmente

Para probar el workflow:

1. Haz clic en el botón **"Execute Workflow"** (▶️)
2. El workflow llamará al endpoint y procesará el cálculo
3. Revisa los resultados en el nodo **"Guardar Resultado"**

## 📊 Estructura del workflow

```
Schedule Trigger
    ↓
Calcular IFO (HTTP Request)
    ↓
¿Hay incumplimientos? (IF)
    ├─→ Preparar JSON (sin incumplimientos)
    └─→ Preparar JSON Incumplimientos (con detalles)
    ↓
Guardar Resultado
```

## 🔧 Parámetros del endpoint

### Request Body (JSON):

```json
{
  "fecha": "2025-01-08",        // Opcional: fecha específica (YYYY-MM-DD)
  "desde": "2025-01-01",         // Opcional: fecha inicio rango
  "hasta": "2025-01-31",         // Opcional: fecha fin rango
  "solo_calculo": true           // true: solo calcular, false: incluir detalles
}
```

**Notas:**
- Si no especificas `fecha`, `desde` o `hasta`, procesa el día anterior por defecto
- `solo_calculo=true`: Retorna solo resumen (más rápido)
- `solo_calculo=false`: Incluye detalles de incumplimientos (más lento)

### Response (JSON):

```json
{
  "fecha_procesada": "2025-01-08",
  "tipo_dia": "LABORAL",
  "eots_procesados": 25,
  "registros_guardados": 150,
  "registros_actualizados": 0,
  "total_registros": 150,
  "incumplimientos_detectados": 5,
  "resultados": [
    {
      "fecha": "2025-01-08",
      "tipo_dia": "LABORAL",
      "eots_procesados": 25,
      "registros_guardados": 150,
      "registros_actualizados": 0,
      "incumplimientos": 5,
      "detalle_incumplimientos": [
        {
          "eot_nombre": "Empresa XYZ",
          "eot_id": 123,
          "franja": "07:00-09:00",
          "ifo_observado": 75.5,
          "ifo_minimo": 80.0,
          "diferencia": "-4.50"
        }
      ]
    }
  ]
}
```

## 🎨 Personalizar el workflow

### Agregar notificaciones por email

1. Agrega un nodo **"Email"** después de **"Preparar JSON Incumplimientos"**
2. Configura el servidor SMTP
3. Envía un correo cuando hay incumplimientos

### Guardar resultados en base de datos

1. Agrega un nodo **"PostgreSQL"** después de **"Guardar Resultado"**
2. Inserta los resultados en una tabla de logs

### Enviar a webhook externo

1. Agrega un nodo **"HTTP Request"** después de **"Guardar Resultado"**
2. Envía los resultados a otro sistema

## 🔍 Verificar que el endpoint funciona

Antes de usar el workflow, verifica que el endpoint esté disponible:

```bash
# Desde el servidor o tu máquina local
curl -X POST http://172.16.222.222:5001/api/ifo/calcular \
  -H "Content-Type: application/json" \
  -d '{"fecha": "2025-01-08", "solo_calculo": true}'
```

O desde el navegador, ve a:
- Documentación API: http://172.16.222.222:5001/docs
- Busca el endpoint `/api/ifo/calcular` y prueba desde ahí

## ⚠️ Notas importantes

1. **Timeout**: El workflow tiene un timeout de 5 minutos (300 segundos). Si procesas muchas fechas o EOTs, puede que necesites aumentarlo.

2. **Puerto**: Asegúrate de que el backend esté corriendo en el puerto 5001 (verifica con `docker compose ps`)

3. **Base de datos**: El endpoint guarda automáticamente los resultados en `control_metricas.ifo_historico`

4. **Ejecución automática**: El workflow se ejecuta automáticamente según el schedule configurado. Puedes desactivarlo desde n8n si no lo necesitas.

## 🐛 Solución de problemas

### El workflow no se ejecuta

- Verifica que el schedule trigger esté activado
- Revisa los logs de n8n

### Error de conexión al endpoint

- Verifica que el backend esté corriendo: `docker compose ps`
- Verifica la URL: `http://172.16.222.222:5001/api/ifo/calcular`
- Prueba el endpoint manualmente con curl

### Timeout en la ejecución

- Aumenta el timeout en el nodo "Calcular IFO"
- Procesa menos fechas a la vez (usa `fecha` en lugar de `desde`/`hasta`)

---

¡Listo! Ya puedes usar el workflow en n8n para calcular IFO de forma automatizada. 🎉
