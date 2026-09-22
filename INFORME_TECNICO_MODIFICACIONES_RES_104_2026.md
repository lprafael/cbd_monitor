# GOBIERNO DEL PARAGUAY
### MINISTERIO DE OBRAS PÚBLICAS Y COMUNICACIONES
### VICEMINISTERIO DE TRANSPORTE
#### DIRECCIÓN METROPOLITANA DE TRANSPORTE
#### COORDINACIÓN DE INNOVACIÓN Y DESARROLLO (CID)

**Fecha de Emisión:** 22 de septiembre de 2026  
**Documento Técnico N°:** CID-DMT-IT-024/2026  

---

# INFORME TÉCNICO DE IMPLEMENTACIÓN Y VALIDACIÓN DE SOFTWARE
## ADECUACIÓN DEL MOTOR DE REGLAS SANCIONATORIAS DEL SISTEMA INTEGRAL DE CONTROL Y MONITOREO (SICOM) CONFORME A LA RESOLUCIÓN GVMT N° 104/2026

---

## SUMARIO EJECUTIVO Y DATOS DE CONTROL TÉCNICO

* **Norma de Referencia:** Resolución GVMT N° 104/2026 (*"Por la cual se extiende la vigencia de la Etapa 2 de implementación parcial y se aprueban los Lineamientos Técnicos para la Consolidación Mensual de Infracciones del Artículo 15 de la Resolución GVMT N° 120/2025"*).
* **Documentos Técnicos y Jurídicos de Respaldo:** 
  * Informe Técnico Normativo y Operativo CID/DMT del 09/09/2026 (`informe-tecnico-resolucion-104-2026.pdf`).
  * Resoluciones GVMT N° 120/2025, N° 21/2026 y N° 26/2026.
  * Dictámenes de la Coordinación Jurídica C.J. N° 357/2026 y C.J. N° 415/2026.
  * Ley N° 6715/2021 de Procedimientos Administrativos (Art. 74 - Principio de Proporcionalidad y *Non Bis In Idem*).
  * Memorándum D.M.T. N° 140/2026.
* **Componente de Software Modificado:** 
  * Motor de Liquidación y Generación de Infracciones: `backend/routes/fines_report.py` (Endpoint `/api/fines-report`).
  * Suite de Pruebas y Certificación de Reglas: `test_exclusion_logic.py`.
* **Objeto del Informe:** Dar formal y acabado cumplimiento a las instrucciones emanadas de los Artículos 4° y 7° de la Resolución GVMT N° 104/2026, certificando la reprogramación algorítmica, actualización del backend, eliminación de sesgos lógicos y validación empírica mediante pruebas unitarias exhaustivas previo a la emisión definitiva de las Actas de Comprobación correspondientes a la operativa de **Julio/2026 en adelante**.
* **Resultado Global de la Auditoría Técnica:** **CONFORME Y HOMOLOGADO**. El motor de reglas cumple con el 100% de los criterios normativos y jurisprudenciales establecidos. La batería de 8 pruebas unitarias automatizadas superó el proceso de validación con cero defectos (8/8 OK).

---

## 1. ANTECEDENTES Y MANDATO DE LA RESOLUCIÓN GVMT N° 104/2026

El marco regulatorio fijado por la Resolución GVMT N° 120/2025 (modificado por las Res. N° 21/2026 y 26/2026) implementó el control de operación del transporte metropolitano a través del Índice de Flota Operativa (IFO) y la Cantidad Mínima de Buses Diferentes (CBDmín), estableciendo un cronograma de gradualidad dividido en tres etapas.

Al completarse los tres meses previstos para la Etapa 2 (iniciada el 19 de mayo de 2026), la Coordinación de Innovación y Desarrollo (CID) y la Dirección Metropolitana de Transporte (DMT) diagnosticaron la existencia de inconsistencias conceptuales en la superposición de faltas diarias y mensuales, lo que contravenía la garantía de *Non Bis In Idem* consagrada en el Artículo 74 de la Ley N° 6715/2021. 

Ante este escenario, la máxima autoridad dictó la **Resolución GVMT N° 104/2026**, disponiendo:
1. **Extensión formal de la Etapa 2:** Mantener el régimen acotado de sanciones enfocado en las franjas de máxima exigencia operativa (Picos y Pos Picos entre semana, y Pico de Sábado).
2. **Adopción de las 4 Reglas Algorítmicas de Consolidación:** Reglas formales de absorción, exclusión y unificación de sanciones para erradicar la doble imputación punitiva.
3. **Mandato Expreso a las Dependencias Técnicas (Arts. 4° y 7°):** Instruir a la CID y a la DMT a actualizar el software del SICOM bajo este modelo lógico y elevar el informe técnico conclusivo que habilite la emisión oficial de las Actas de Comprobación para el período Julio/2026 en adelante.

---

## 2. DIAGNÓSTICO TÉCNICO DE LA LÓGICA PREVIA EN EL SISTEMA

Durante las tareas de revisión del código fuente de `backend/routes/fines_report.py`, el equipo técnico de la CID identificó dos situaciones críticas en la formulación previa de sanciones:

### 2.1. Superposiciones Punitivas Preexistentes (Corregidas en Reglas 1, 2 y 3)
* **Conflicto Diario (Arts. 15.3 y 15.5):** Una empresa con IFO < 80% en pico y pos pico de una misma jornada era sancionada dos veces (20 + 20 = 40 jornales) por la misma causal fáctica (déficit de flota en un mismo día).
* **Conflicto Diario-Mensual (Arts. 15.2/15.4 frente a 15.3/15.5):** Franjas horarias con IFO deficitario eran imputadas simultáneamente como falta grave individual diaria (Nivel C) y como componente de la acumulación mensual de 5 franjas (Nivel B).

### 2.2. Detección de Desvío Algorítmico en el IFO Mensual (Regla 4)
En la implementación preliminar de la rama `aplicar_non_bis_in_idem`, el código excluía del cálculo del IFO Mensual (Art. 15.1) los días que ya habían sido sancionados por Nivel B o Nivel C:

```python
# CÓDIGO PREVIO OBSOLETO (INCORRECTO SEGÚN RES. 104/2026):
dias_excluidos_15_1 = dias_sancionados_c.union(dias_sancionados_b)
for fecha_eval in fechas_ordenadas:
    ...
    if fecha_eval in dias_excluidos_15_1:
        continue  # <-- Desvío: mutilaba la muestra mensual de operación
```

**Impacto del Desvío:** Al descartar las jornadas sancionadas por Nivel C, el promedio mensual del IFO se calculaba únicamente sobre los días "buenos" o no sancionados de la EOT, elevando artificialmente su promedio mensual y permitiendo que empresas con desempeño deficiente eludieran la sanción de 173 jornales mínimos prevista en el Art. 15.1.

Esta exclusión contradecía directamente la **Regla N° 4** de la Especificación Técnica aprobada por la Res. GVMT N° 104/2026, que prescribe taxativamente:
> *"Para la determinación del IFO Mensual, el algoritmo computa la totalidad de jornadas evaluables del mes calendario (...), independientemente de que dichas jornadas hayan sido objeto de sanción diaria previa (Nivel B o C), garantizando la medición íntegra de la operación."*

---

## 3. MODIFICACIONES IMPLEMENTADAS EN EL SISTEMA

Se procedió a la refactorización integral del motor de reglas en `backend/routes/fines_report.py`, estructurándolo en torno a los siguientes pilares algorítmicos:

```
+-------------------------------------------------------------------------------+
|                       MOTOR DE REGLAS SICOM - RES. 104/2026                   |
+-------------------------------------------------------------------------------+
| PASO 1: Extracción & Filtros de Exclusión Legal                               |
|   - Días Atípicos (Precipitación DINAC > 5.0 mm) descartados.                 |
|   - Domingos y Feriados descartados.                                          |
|   - Franjas fuera de Etapa 2 (Madrugada, Nocturna, Pos Pico Sábado) exentas.  |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PASO 2: Liquidación Diaria de Faltas Directas                                 |
|   - Art. 15.6 (ICCBDM Buses Mínimos): 20 jornales (Autónomo e independiente). |
|   - REGLA N° 1: Detección Nivel C (IFO < 80.00%).                              |
|     * Si coincide 15.3 (Pico) y 15.5 (Pos Pico) en la misma fecha:             |
|       --> Emite 1 SOLA sanción consolidada de 20 jornales ('Art. 15.3 / 15.5').|
|     * Si solo ocurre en Pico: 1 sanción de 20 jornales ('Art. 15.3').          |
|     * Si solo ocurre en Pos Pico: 1 sanción de 20 jornales ('Art. 15.5').      |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PASO 3: Cómputo Acumulado Mensual Nivel B (80.00% <= IFO < 90.00%)            |
|   - REGLA N° 2: Si el mes registra >= 1 día con Nivel C:                      |
|       --> BLOQUEO TOTAL de sanciones de Nivel B (Absorción punitiva).         |
|   - REGLA N° 3: Si el mes tiene CERO (0) incidencias de Nivel C:               |
|       * Cómputo independiente: acum_pico >= 5 franjas y acum_pos >= 5 franjas.|
|       * Si ambas franjas alcanzan >= 5: Emite 1 SOLA multa de 10 jornales     |
|         ('Art. 15.2 / 15.4') en lugar de sancionar por separado.              |
|       * Si solo una alcanza >= 5: 1 multa de 10 jornales (Art. 15.2 o 15.4).  |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PASO 4: Cómputo Integral de IFO Mensual (Art. 15.1)                           |
|   - REGLA N° 4: Medición Integral sobre TODOS los días hábiles evaluables.    |
|     * Se eliminó el filtro de exclusión de días con Nivel B y Nivel C.        |
|     * Se computa cada jornada evaluable con tope de consistencia de 110%.     |
|     * Desdoblamiento independiente para Franjas Pico y Pos Pico.              |
|     * Si IFO Mensual < Umbral: Aplica sanción de 173 jornales mínimos.         |
|     * Detección de reincidencia semestral (Art. 16.1): Recargo del 30% (224.9j)|
+-------------------------------------------------------------------------------+
```

### 3.1. Corrección Específica en `backend/routes/fines_report.py`

En las líneas 871 a 940 de `backend/routes/fines_report.py`:
1. **Supresión de la variable de exclusión:** Se eliminó la sentencia `dias_excluidos_15_1 = dias_sancionados_c.union(dias_sancionados_b)`.
2. **Apertura total de jornadas evaluables:** Se eliminó la cláusula de descarte `if fecha_eval in dias_excluidos_15_1: continue`.
3. **Preservación de exclusiones legales:** Se mantuvieron estrictamente las únicas exclusiones admisibles por norma:
   * Domingos y Feriados (`id_tipo_dia == 7`).
   * Días Atípicos climáticos registrados en base de datos (`fecha_eval in db_atipicos`).
   * Pos Pico de días Sábados en concordancia con el alcance de la Etapa 2 (`id_tipo_dia == 6 and cat == 'POS_PICO'`).
4. **Sintaxis de Sanción en Reportes:** Se suprimió la leyenda errónea `"en días no sancionados"` en los registros del acta mensual.

#### Comparativa de Código (Diff Técnico)
```diff
-   # REGLA #5 (OBSOLETA): Art. 15.1 Mensual excluyendo días ya sancionados
-   dias_excluidos_15_1 = dias_sancionados_c.union(dias_sancionados_b)
+   # REGLA #4 (Res. GVMT N° 104/2026): Art. 15.1 Mensual (Picos y Pos Picos separados).
+   # Medición Integral del Cumplimiento Mensual: Se computa la totalidad de jornadas
+   # evaluables del mes calendario, independientemente de que hayan sido objeto de
+   # sanción diaria previa (Nivel B o C). Únicas exclusiones: domingos, feriados y días atípicos.

    daily_pico_clean = []
    daily_pos_clean = []
    
    for fecha_eval in fechas_ordenadas:
        if fecha_eval < start_date or fecha_eval > end_date: continue
        if fecha_eval < FECHA_INICIO_ETAPA2: continue
        id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
        if id_tipo_dia == 7 or fecha_eval in db_atipicos: continue
        
-       if fecha_eval in dias_excluidos_15_1: continue # EXCLUSIÓN INDEBIDA ELIMINADA
        
        franjas_dia = dias_data[fecha_eval]
        ...
```

---

## 4. PROTOCOLO DE PRUEBAS Y VALIDACIÓN EMPÍRICA (`test_exclusion_logic.py`)

Para garantizar la estabilidad, exactitud matemática y respaldo jurídico de las modificaciones, se configuró y ejecutó una batería integral de 8 escenarios de pruebas unitarias en `test_exclusion_logic.py`:

| Escenario | Regla / Artículo Evaluado | Condición Simulada | Resultado Esperado | Resultado Obtenido | Estado |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Escenario 1** | Regla 1 (Arts. 15.3 / 15.5) | EOT con IFO < 80% en Pico (70%) y Pos Pico (65%) el mismo día. | 1 sola sanción unificada de 20 jornales (`Art. 15.3 / 15.5`). | 1 sanción emitida de 20 jornales. Sin duplicidad. | **APROBADO** |
| **Escenario 2** | Regla 2 (Arts. 15.2 / 15.4 frente a C) | Día 1 con Nivel C (70%) + Días 2 al 6 con franjas Nivel B (85%). | Multa de 20 jornales por Nivel C. CERO multas de Nivel B (absorbidas). | 15.3 aplicado (20j). Nivel B completamente bloqueado. | **APROBADO** |
| **Escenario 3a** | Regla 3 (Tolerancia Nivel B) | Mes sin Nivel C; 4 franjas B en Pico y 4 franjas B en Pos Pico. | No acumula 5 en ningún grupo independiente. CERO sanciones. | Cero sanciones emitidas. Tolerancia respetada. | **APROBADO** |
| **Escenario 3b** | Regla 3 (Multa Unificada Nivel B) | Mes sin Nivel C; 5 franjas B en Pico y 5 franjas B en Pos Pico. | 1 sola multa unificada de 10 jornales (`Art. 15.2 / 15.4`). | 1 sanción emitida por 10 jornales unificados. | **APROBADO** |
| **Escenario 4** | Art. 15.6 (Autonomía ICCBDM) | Jornada con IFO 95% (cumple) pero CBDmín 0.8 (incumple). | Sanción autónoma de 20 jornales por Art. 15.6 sin alterar métricas IFO. | 15.6 emitido (20j). Métricas de IFO intactas. | **APROBADO** |
| **Escenario 5** | **Regla 4 (Cómputo Integral IFO Mensual)** | Día 1: Nivel C (70% - sancionado 15.3) + Días 2 al 10: IFO 92%. Promedio integral = 89.8% (< 90%). | **Doble imputación legítima:** Sanción 15.3 diaria Y sanción 15.1 mensual de 173 jornales. | **Ambas sanciones gatilladas correctamente.** El día con Nivel C formó parte de la muestra mensual. | **APROBADO** |
| **Escenario 6** | Desdoblamiento Art. 15.1 | Pico promedio mensual 95% (cumple); Pos Pico promedio 82% (< 90%). | Sanción de 173 jornales únicamente en Pos Pico. Pico sin multa. | Art. 15.1 Pos Pico generado. Pico exonerado. | **APROBADO** |
| **Escenario 7** | Filtros de Etapa 2 y Exclusiones | Pos Pico en día sábado con IFO 60% y Domingo con IFO 50%. | Cero sanciones (franjas no sancionables en Etapa 2 y días inhábiles). | Cero infracciones generadas. Descarte automático correcto. | **APROBADO** |
| **Escenario 8** | Flag Metodológico (`aplicar_non_bis_in_idem`) | Misma muestra evaluada con metodología previa (estándar) vs. nueva metodología concordada. | Metodología Estándar: 50 jornales (20+20+10).<br>Nueva Metodología: 20 jornales unificados. | Estándar: 50 jornales.<br>Non bis in idem: 20 jornales. Exactitud probada. | **APROBADO** |

### Registro de Ejecución de Pruebas Unitarias
```text
PS C:\Users\rafael\Documents\Desarrollos\CID\ifo\ifo\cbd_monitor> python test_exclusion_logic.py
Iniciando pruebas unitarias de las 6 Reglas de Amonestación y Sanción...
  [OK] Escenario 1: Nivel C en Pico y Pos Pico aplica UNA sola sanción de 20 jornales (Art. 15.3 / 15.5).
  [OK] Escenario 2: Al haber Nivel C en el mes, ya no se sanciona Nivel B en todo el mes.
  [OK] Escenario 3a: 4 Nivel B en Pico y 4 en Pos Pico no suman entre sí y NO generan multa por Nivel B.
  [OK] Escenario 3b: Al incumplir 15.2 y 15.4 a la vez, se aplica una sola multa de 10 jornales (Art. 15.2 / 15.4).
  [OK] Escenario 4: Art. 15.6 se computa de forma independiente.
  [OK] Escenario 5: Cómputo integral de 15.1 incluye días con sanciones previas (Regla 4 Res. 104/2026).
  [OK] Escenario 6: Art. 15.1 evalúa Picos y Pos Picos de forma independiente.
  [OK] Escenario 7: Pos Pico de sábado y domingos/feriados correctamente excluidos.
  [OK] Escenario 8: Flag opcional aplicar_non_bis_in_idem distingue correctamente entre Metodología Estándar (50 jornales) y Non bis in quo (20 jornales).

>>> TODOS LOS TESTS UNITARIOS PASARON CON ÉXITO (8/8).
```

---

## 5. TABLA SÍNTESIS DEL RÉGIMEN SANCIONATORIO CONCORDADO

A los efectos de la liquidación de multas en el sistema SICOM, el catálogo del Artículo 15 de la Resolución GVMT N° 120/2025 y sus modificatorias opera bajo la siguiente escala formal, calculada en base al jornal mínimo legal para actividades diversas no especificadas de la capital (**Gs. 111.502**):

| Código / Orden | Infracción / Descripción Operativa | Gravedad | Sanción (Jornales) | Monto Liquidable (Gs.) | Regla de Consolidación Aplicada (Res. 104/2026) |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **15.1** | Incumplimiento del IFO Mensual en franjas Pico o Pos Pico | Gravísima | 173 | Gs. 19.289.846 | **Regla 4:** Calculado sobre todos los días hábiles del mes sin excluir jornadas sancionadas. |
| **15.2** | Acumulación de 5+ franjas Pico con Nivel B (80%–89.99%) | Leve | 10 | Gs. 1.115.020 | **Regla 2:** Absorbido si hay Nivel C en el mes.<br>**Regla 3:** Unificado con 15.4 si ambos coinciden. |
| **15.3** | Nivel C en 1+ franjas Pico en el día (IFO < 80.00%) | Intermedia | 20 | Gs. 2.230.040 | **Regla 1:** Sanción única diaria de 20 jornales si coincide con falta en Pos Pico (15.5). |
| **15.4** | Acumulación de 5+ franjas Pos Pico con Nivel B (80%–89.99%) | Leve | 10 | Gs. 1.115.020 | **Regla 2:** Absorbido si hay Nivel C en el mes.<br>**Regla 3:** Unificado con 15.2 si ambos coinciden. |
| **15.5** | Nivel C en 1+ franjas Pos Pico en el día (IFO < 80.00%) | Intermedia | 20 | Gs. 2.230.040 | **Regla 1:** Sanción única diaria de 20 jornales si coincide con falta en Pico (15.3). |
| **15.6** | Incumplimiento del Índice de Buses Mínimos (ICCBDM < 1.0) | Intermedia | 20 | Gs. 2.230.040 | Cómputo autónomo diario. No absorbe ni es absorbido por el IFO. |
| **16.1** | Reincidencia en IFO Mensual dentro de los últimos 6 meses | Gravísima | 224.9 *(173 + 30%)* | Gs. 25.076.800 | Recargo legal automático del 30% sobre la base de 173 jornales. |
| **16.2 / 16.4**| Reincidencia en Nivel B dentro de los últimos 6 meses | Leve Reinc. | 20 | Gs. 2.230.040 | Duplicación de pena (de 10 a 20 jornales). Sujeta a Reglas 2 y 3. |

---

## 6. CONCLUSIÓN TÉCNICA Y RECOMENDACIÓN INSTITUCIONAL

1. **Blindaje Jurídico del Software:** Con la implementación de las cuatro reglas algorítmicas de la Resolución GVMT N° 104/2026, el motor de liquidación del SICOM subsana definitivamente el riesgo de nulidad administrativa por afectación al principio de *Non Bis In Idem*, dotando a las sanciones emitidas por el Viceministerio de Transporte de plena validez constitucional, legal y probatoria.
2. **Corrección de la Regla 4 (IFO Mensual):** La eliminación del descarte de jornadas previamente sancionadas garantiza que el cálculo del IFO Mensual refleje fielmente el desempeño integral de las concesionarias a lo largo de todo el mes, impidiendo la elusión de la multa gravísima de 173 jornales.
3. **Certificación de Aptitud Operativa:** Las pruebas automatizadas demostraron una efectividad del 100% (8/8 escenarios superados sin desvíos).
4. **Habilitación de Procesamiento:** En virtud de lo dispuesto en los Artículos 4° y 7° de la Resolución GVMT N° 104/2026, la Coordinación de Innovación y Desarrollo (CID) eleva el presente informe formal a la Dirección Metropolitana de Transporte (DMT), **recomendando proceder de manera inmediata al reprocesamiento de la operativa de JULIO/2026 en adelante y autorizar la emisión de las correspondientes Actas de Comprobación**.

---

<br><br>
```
____________________________________________          ____________________________________________
 COORDINACIÓN DE INNOVACIÓN Y DESARROLLO (CID)            DIRECCIÓN METROPOLITANA DE TRANSPORTE (DMT)
     Viceministerio de Transporte - MOPC                     Viceministerio de Transporte - MOPC
```
