# Cálculo del IFO Sistema - Resolución GVMT N° 120/2025

## Definición

El **IFO Sistema** es el promedio del Índice de Flota Operativa de todas las Empresas Operadoras de Transporte (EOT) del sistema de transporte público durante un mes calendario específico.

Este indicador se utiliza como **base de referencia** para calcular el **IFO Objetivo** del mes siguiente, que es el umbral mínimo obligatorio que cada EOT debe cumplir.

---

## Jerarquía de Cálculo

El cálculo del IFO Sistema sigue una jerarquía de agregación en **4 niveles**:

```
IFO Franja (nivel base)
    ↓
IFO Día = Promedio(IFO Franja por día)
    ↓
IFO Mensual EOT = Promedio(IFO Día)
    ↓
IFO Sistema = Promedio(IFO Mensual de todas las EOTs)
```

---

## Procedimiento Detallado

### **Nivel 1: IFO Franja**
- **Fuente**: Tabla `control_metricas.ifo_historico`
- **Descripción**: Índice de Flota Operativa calculado para cada franja horaria operativa
- **Formato**: Valor decimal entre 0 y ~1.05 (0% a ~105%)
- **Almacenamiento**: Ya está precalculado en la base de datos

### **Nivel 2: IFO Día**
- **Fórmula**: 
  ```
  IFO Día (EOT, Fecha) = AVG(IFO Franja) para todas las franjas del día
  ```
- **Agrupación**: Por `id_eot_vmt_hex` y `fecha`
- **Exclusiones aplicadas**:
  - ❌ Domingos (isodow = 7)
  - ❌ Feriados (tabla `public.feriados`)
  - ❌ Días atípicos (tabla `control_metricas.dias_atipicos`)

### **Nivel 3: IFO Mensual EOT**
- **Fórmula**:
  ```
  IFO Mensual (EOT) = AVG(IFO Día) para todos los días válidos del mes
  ```
- **Agrupación**: Por `id_eot_vmt_hex`
- **Período**: Mes calendario completo (día 1 al último día del mes)
- **Conversión**: Se multiplica por 100 para expresar en porcentaje

### **Nivel 4: IFO Sistema**
- **Fórmula**:
  ```
  IFO Sistema (Mes) = AVG(IFO Mensual EOT) para todas las EOTs activas
  ```
- **Descripción**: Promedio simple de los IFO Mensuales de todas las empresas
- **Resultado**: Valor en porcentaje (0-100+)

---

## Filtros y Exclusiones

### **Días Excluidos**
1. **Domingos**: `extract(isodow from fecha) = 7`
2. **Feriados**: Fechas presentes en `public.feriados`
3. **Días Atípicos**: Fechas presentes en `control_metricas.dias_atipicos`
   - Ejemplos: Días con eventos extraordinarios, manifestaciones, clima extremo, etc.

### **Franjas Incluidas**
- ✅ Todas las franjas operativas definidas en `control_metricas.franjas_operativas`
- ✅ Incluye: Madrugada, Pico Mañana, Entre Picos, Pico Tarde, Pos Pico, Nocturna

### **EOTs Incluidas**
- ✅ Todas las EOTs activas con datos en el período
- ❌ EOT 72 (excluida por configuración)

---

## Cálculo del IFO Objetivo

Una vez calculado el IFO Sistema del mes anterior, se determina el **IFO Objetivo** para el mes actual:

### **Fórmula del IFO Objetivo**
```
IFO Objetivo (Mes n) = IFO Sistema (Mes n-1) - 5 puntos porcentuales
```

### **Ejemplo Práctico**
- **Mes anterior (noviembre 2025)**: IFO Sistema = 106.35%
- **Mes actual (diciembre 2025)**: IFO Objetivo = 106.35% - 5 = **101.35%**

### **Regla de Validación (Infracción 15.1)**
- Si `IFO Mensual EOT < IFO Objetivo` → **Infracción Gravísima** (173 jornales)
- Base legal: Artículo 15.1, Resolución GVMT N° 120/2025

---

## Variante: IFO Sistema Topeado

Para ciertos análisis, se calcula también el **IFO Sistema Topeado**:

### **Fórmula**
```
IFO Mensual EOT Topeado = AVG(MIN(IFO Día, 1.05))
IFO Sistema Topeado = AVG(IFO Mensual EOT Topeado)
```

### **Propósito**
- Limita el impacto de valores excepcionalmente altos (>105%)
- Proporciona una visión más conservadora del rendimiento del sistema
- Útil para análisis de tendencias y comparaciones históricas

---

## Implementación SQL

### **Query Completo**
```sql
-- Nivel 4: IFO Sistema
SELECT 
    AVG(eot_monthly_ifo) as ifo_sistema,
    AVG(eot_monthly_ifo_topeado) as ifo_sistema_topeado
FROM (
    -- Nivel 3: IFO Mensual por EOT
    SELECT 
        id_eot_vmt_hex,
        AVG(daily_ifo) as eot_monthly_ifo,
        AVG(LEAST(daily_ifo, 1.05)) as eot_monthly_ifo_topeado
    FROM (
        -- Nivel 2: IFO Día
        SELECT 
            id_eot_vmt_hex,
            fecha, 
            AVG(franja_avg) as daily_ifo
        FROM (
            -- Nivel 1: IFO Franja (agregado por día)
            SELECT 
                id_eot_vmt_hex,
                fecha, 
                h.id_franja,
                AVG(ifo) as franja_avg
            FROM control_metricas.ifo_historico h
            JOIN control_metricas.franjas_operativas f 
                ON h.id_franja = f.id_franja
            WHERE h.fecha BETWEEN :inicio_mes AND :fin_mes
              AND extract(isodow from h.fecha) < 7  -- Excluir domingos
              AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
              AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
            GROUP BY id_eot_vmt_hex, fecha, h.id_franja
        ) franja_level
        GROUP BY id_eot_vmt_hex, fecha
    ) daily_avgs
    GROUP BY id_eot_vmt_hex
) eot_avgs;
```

---

## Endpoints API

### **GET /api/reports/res120/system-ifo-baseline/{fecha}**
- **Descripción**: Obtiene el IFO Sistema del mes anterior a la fecha especificada
- **Respuesta**:
  ```json
  {
    "ifo_sistema_mes_anterior": 106.35,
    "anio": 2025,
    "mes": 11
  }
  ```

### **GET /api/reports/res120/system-ifo-breakdown/{year}/{month}**
- **Descripción**: Obtiene el desglose completo del IFO Sistema para un mes específico
- **Respuesta**: Incluye IFO Mensual de cada EOT y el promedio del sistema

---

## Consideraciones Técnicas

### **Precisión Numérica**
- Los valores en la base de datos se almacenan como decimales (0-1.05)
- Se convierten a porcentaje (0-105) para presentación al usuario
- El redondeo final se aplica a **2 decimales** para el IFO Sistema

### **Performance**
- El cálculo puede ser costoso para períodos largos
- Se recomienda cachear resultados mensuales una vez cerrado el mes
- Las subconsultas están optimizadas con índices en `fecha` e `id_eot_vmt_hex`

### **Validación de Datos**
- Si no hay datos para una EOT en el período, se excluye del promedio
- Si no hay datos para ninguna EOT, el IFO Sistema retorna 0.0
- Los días sin datos completos no afectan el cálculo (se promedian solo días válidos)

---

## Referencias

- **Resolución GVMT N° 120/2025**: Marco normativo del IFO
- **Artículo 6.1**: Definición del IFO Objetivo
- **Artículo 15.1**: Infracción por incumplimiento del IFO Mensual
- **Artículo 22**: Período de socialización y capacitación

---

**Última actualización**: 2026-02-03  
**Versión**: 1.0  
**Autor**: Coordinación de Innovación y Desarrollo (CID) - DMT
