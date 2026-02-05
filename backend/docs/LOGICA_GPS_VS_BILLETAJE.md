# Lógica de Decisión: GPS vs Billetaje en el Cálculo de IFO

## 📋 Resumen Ejecutivo

El sistema **siempre prioriza los datos de billetaje** (`servicios_diarios`) como fuente principal. Solo consulta GPS (`cbd_detalle_buses`) cuando el billetaje **no alcanza el mínimo requerido**.

## 🔄 Flujo de Decisión

### Paso 1: Consultar Billetaje (Prioridad)
```python
# Siempre se consulta primero servicios_diarios
SELECT COUNT(DISTINCT idsam) as cbd
FROM public.servicios_diarios
WHERE id_eot_catalogo = %s AND fecha = %s AND hora = %s
```

**Resultado:** `cbd_val` = cantidad de buses distintos según billetaje

### Paso 2: Evaluar si se necesita GPS (Condición)
```python
if cbd_val < cbd_min_hora and eot_vmt_hex:
    # Consultar GPS
```

**Condiciones para usar GPS:**
1. ✅ `cbd_val < cbd_min_hora` - El billetaje NO alcanza el mínimo requerido
2. ✅ `eot_vmt_hex` existe - La EOT tiene identificador GPS configurado
3. ✅ `cbd_gps > cbd_val` - El GPS tiene MÁS datos que el billetaje (después de consultarlo)

### Paso 3: Consultar GPS (Fallback)
```python
SELECT COUNT(DISTINCT mean_id) as cbd
FROM control_metricas.cbd_detalle_buses
WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora = %s
```

**Resultado:** `cbd_gps` = cantidad de buses distintos según GPS

### Paso 4: Evaluar si usar GPS
```python
if cbd_gps > cbd_val:
    return cbd_gps  # Usar GPS solo si tiene MÁS datos
return cbd_val  # Si GPS tiene menos o igual, usar billetaje
```

**Lógica final:** Solo se usa GPS si tiene **más datos** que el billetaje. Si GPS tiene menos o igual, se mantiene el billetaje (aunque no cumpla el mínimo).

## 📍 Ubicación en el Código

### 1. `performance.py` - Función `get_cbd_for_hour()`
**Líneas 21-52**

```python
def get_cbd_for_hour(cursor, eot_id: int, eot_vmt_hex: str, fecha, hora: int, 
                     cbd_min_hora: int, cache_val: dict = None, cache_gps: dict = None) -> int:
    # 1. Consultar validaciones (BILLETAJE)
    cbd_val = cache_val.get((eot_id, fecha, hora), 0)  # o consulta directa
    
    # 2. Si no cumple mínimo, consultar GPS
    if cbd_val < cbd_min_hora and eot_vmt_hex:
        cbd_gps = cache_gps.get((eot_vmt_hex, fecha, hora), 0)  # o consulta directa
        # Solo usar GPS si tiene MÁS datos que billetaje
        if cbd_gps > cbd_val:
            return cbd_gps
        # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
        return cbd_val
    
    return cbd_val  # Si cumple mínimo, solo usa billetaje
```

**Usado en:**
- Cálculo de CBD por hora
- Cálculo de IFO por hora (línea 277, 284)

### 2. `performance_detail.py` - Endpoint `/cbd`
**Líneas 273-293**

```python
for hora in range(hora_inicio, hora_fin + 1):
    # 1. Primero consultar CBD de validaciones (BILLETAJE)
    cbd_val = cursor.fetchone()['cbd'] or 0
    
    # 2. Solo si no cumple con el mínimo, consultar GPS
    cbd_observado = cbd_val
    if cbd_val < cbd_min_hora and eot_info['id_eot_vmt_hex']:
        cbd_gps = cursor.fetchone()['cbd'] or 0
        # Solo usar GPS si tiene MÁS datos que billetaje
        if cbd_gps > cbd_val:
            cbd_observado = cbd_gps
        # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
```

### 3. `performance_detail.py` - Endpoint `/ifo`
**Líneas 437-457**

```python
for hora in range(hora_inicio, hora_fin + 1):
    # 1. Primero consultar CBD de validaciones (BILLETAJE)
    cbd_val = cursor.fetchone()['cbd'] or 0
    
    # 2. Solo si no cumple con el mínimo, consultar GPS
    cbd_dia = cbd_val
    if cbd_val < cbd_min_hora:
        cbd_gps = cursor.fetchone()['cbd'] or 0
        # Tomar el MAX entre validaciones y GPS
        cbd_dia = max(cbd_val, cbd_gps)
```

**Nota:** La misma lógica se aplica también para el cálculo histórico (líneas 464-482).

## 🎯 Ejemplos Prácticos

### Ejemplo 1: Billetaje Cumple Mínimo
```
cbd_min_hora = 10
cbd_val (billetaje) = 15
eot_vmt_hex = "ABC123"

Resultado: cbd_observado = 15 (solo billetaje)
GPS: NO se consulta
```

### Ejemplo 2: Billetaje NO Cumple Mínimo, GPS Tiene Más
```
cbd_min_hora = 10
cbd_val (billetaje) = 7
cbd_gps = 12
eot_vmt_hex = "ABC123"

Resultado: cbd_observado = 12 (GPS tiene más que billetaje)
GPS: SÍ se consulta y se usa
```

### Ejemplo 2b: Billetaje NO Cumple Mínimo, GPS Tiene Menos
```
cbd_min_hora = 10
cbd_val (billetaje) = 7
cbd_gps = 5
eot_vmt_hex = "ABC123"

Resultado: cbd_observado = 7 (GPS tiene menos, se mantiene billetaje)
GPS: SÍ se consulta pero NO se usa (billetaje es mejor)
```

### Ejemplo 3: Sin Identificador GPS
```
cbd_min_hora = 10
cbd_val (billetaje) = 7
eot_vmt_hex = None  # o ""

Resultado: cbd_observado = 7 (solo billetaje)
GPS: NO se consulta (no hay identificador)
```

## 📊 Aplicación en el Cálculo de IFO

Para el cálculo del IFO, esta lógica se aplica en **dos momentos**:

### 1. CBD del Día Analizado
```python
# Para cada hora de la franja
cbd_dia = get_cbd_for_hour(...)  # Usa billetaje o GPS según condición
```

### 2. CBD Histórico (4 semanas anteriores)
```python
# Para cada fecha histórica y cada hora
for fecha_hist in fechas_historicas:
    cbd_hist = get_cbd_for_hour(...)  # Misma lógica: billetaje primero, GPS si no cumple
```

**Importante:** El factor de ajuste se aplica **después** de obtener el promedio histórico:
```python
promedio_historico_raw = sum_historico / count_historico
promedio_ajustado = round(max(promedio_historico_raw * factor_ajuste, cbd_min_hora), 2)
```

## 🔍 Parámetros Clave

El parámetro que determina el umbral es:
- **`cbd_minimo_hora`**: Mínimo de buses distintos requeridos por hora
- Se obtiene de: `control_metricas.cbd_parametros_minimos`
- Filtrado por: `id_franja` y vigencia de la fecha

## ⚠️ Consideraciones Importantes

1. **Prioridad siempre a billetaje**: El GPS es solo un complemento cuando el billetaje es insuficiente
2. **GPS solo si es mejor**: Solo se usa GPS si tiene **más datos** que el billetaje (`cbd_gps > cbd_val`)
3. **Si GPS es peor, mantener billetaje**: Si GPS tiene menos o igual que billetaje, se mantiene el billetaje aunque no cumpla el mínimo
4. **Requiere identificador GPS**: Si la EOT no tiene `id_eot_vmt_hex`, nunca se consultará GPS
5. **Aplicación consistente**: La misma lógica se usa tanto para el día analizado como para el histórico

## 📝 Resumen de la Lógica

```
┌─────────────────────────────────┐
│  Consultar BILLETAJE            │
│  (servicios_diarios)             │
└──────────────┬──────────────────┘
               │
               ▼
        ¿cbd_val < cbd_min_hora?
               │
        ┌──────┴──────┐
        │             │
       SÍ            NO
        │             │
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ Consultar GPS│  │ Usar solo    │
│ (cbd_detalle)│  │ BILLETAJE    │
└──────┬───────┘  └──────────────┘
       │
       ▼
   ¿cbd_gps > cbd_val?
       │
   ┌───┴───┐
   │       │
  SÍ      NO
   │       │
   ▼       ▼
┌──────────┐  ┌──────────────┐
│ Usar GPS │  │ Usar BILLETAJE│
│ (mejor)  │  │ (GPS peor)    │
└──────────┘  └──────────────┘
```
