# Resolución GVMT N° 120/2025 — Metodología de Cálculo de Indicadores (IFO y CBDmin)

## 1. Marco normativo y alcance
Este documento describe la metodología de cálculo de los indicadores definidos en la **Resolución GVMT N° 120/2025**:
- **Índice de Flota Operativa (IFO)** (Artículo 3.1 y Anexo, Sección 1)
- **Cantidad Mínima de Buses Diferentes (CBDmin)** (Artículo 3.2, Artículo 7 y Anexo, Sección 2)
- **Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Franja (ICCBDM Franja)** (Anexo 2.2)

El objetivo es disponer de un método trazable y auditable para monitoreo, fiscalización, infracciones y emisión de reportes.

## 2. Definiciones relevantes (Resolución, Art. 2)
### 2.1 Definiciones espaciales y operativas
- **Ruta o trazado**: trayecto físico espacial expresado como secuencia ordenada de coordenadas.
- **Cabecera**: punto extremo de inicio o finalización de una ruta.
- **Itinerario**: planificación temporal (horarios, frecuencias, paradas), sin modificar la ruta.
- **Línea**: unidad de servicio que combina ruta e itinerario, identificada.
- **Frecuencia**: cantidad de buses en un periodo (salidas desde cabeceras o puntos de conteo).
- **Intervalo**: minutos entre vehículos consecutivos de la misma línea en el mismo punto y dirección.
- **Programación operativa**: parámetros de horarios, flota, trazados, frecuencias, km operativos/no operativos.

### 2.2 Periodos temporales
- **Periodo de baja demanda**: enero y febrero.
- **Periodo de alta demanda**: marzo a diciembre.

### 2.3 Días y casuísticas
- **Hora reloj**: 60 min consecutivos iniciando en punto (ej.: 5:00-5:59).
- **Día equivalente**: mismo día de la semana (lunes con lunes, etc.).
- **Día con datos válidos**: día con información completa y confiable.
- **Días atípicos**:
  - Feriado día laborable
  - Feriado sábado
  - Día pre/pos feriado
  - Día con lluvia: precipitación > 5 mm (DINAC)
  - Evento disruptivo (validado por la autoridad)

### 2.4 Definiciones de buses
- **Buses diferentes**: vehículos observados el día analizado (GPS y/o validaciones).
- **Buses distintos**: vehículos registrados en días equivalentes anteriores (referencia histórica).
- **Umbral mínimo obligatorio**: límite inferior forzoso de cumplimiento.

## 3. Franjas operativas (Artículo 4)
Las franjas para cómputo de indicadores son:

| Tipo de Día | Franja Operativa | Horario |
|---|---|---|
| Lunes a Viernes | Madrugada | 4:00-4:59 |
|  | Pico (mañana) | 5:00-7:59 |
|  | Pos pico (entre picos) | (según tabla de Art. 4; el documento oficial presenta vacío en el extracto) |
|  | Pico (tarde) | 16:00-18:59 |
|  | Pos pico (tarde) | 19:00-20:59 |
|  | Nocturna | 21:00-22:59 |
| Sábados | Pico | 6:00-15:59 |
|  | Pos pico | 16:00-20:59 |
|  | Nocturna | 21:00-22:59 |
| Domingos/Feriados | Pos pico | 7:00-21:59 |

> Nota: si existiera una parametrización interna adicional (p.ej. base de datos), debe respetar los horarios normativos de la Resolución.

## 4. Indicador 1: Índice de Flota Operativa (IFO)
### 4.1 Propósito (Artículo 3.1 y Anexo 1)
El IFO mide la disponibilidad real de buses en circulación en relación con una referencia histórica comparable (días equivalentes), expresado en porcentaje.

Se aplica a niveles: **hora**, **franja**, **diario** y **mensual**.

### 4.2 IFO por hora (Anexo 1.1)
#### Fórmula
IFOhora [%] = (b_obs^(h,a) / b_dist^(h,d)) * 100

- b_obs: buses diferentes observados en la hora h del día analizado.
- b_dist: media de buses distintos que operaron en la hora h en un día equivalente (referencia).

### 4.3 Obtención de la referencia histórica b_dist (Anexo 1.1.2)
Se distinguen **meses típicos** y **meses atípicos**.

#### Meses típicos
Típicos: **febrero, abril, mayo, junio, julio, agosto, septiembre, octubre, noviembre**.

Referencia: **media de buses distintos observados por hora** en **4 días equivalentes válidos** de las últimas 4 semanas previas.
- Si alguna semana contiene un día atípico que afectó la operación normal, se descarta ese día y se reemplaza por el mismo día de la semana anterior, manteniendo siempre 4 equivalentes válidos.

#### Meses atípicos
Atípicos: **enero, marzo, diciembre**.

- **Enero**: referencia = media de noviembre del año anterior * factor 0,80.
- **Marzo**: referencia = media de noviembre del año anterior (sin factor, 1,00).
- **Diciembre**: referencia = media de noviembre del mismo año * factor 0,80.
- En noviembre de referencia, si un día fue atípico, se reemplaza por el día equivalente anterior aunque caiga en octubre.

### 4.4 Ajustes por días atípicos (Anexo 1.1.2)
Independientemente del mes, si el día analizado es atípico:

- **Feriado día laborable**: b_dist = 30% de la flota habitual por hora en un día equivalente.
- **Feriado sábado**: b_dist = 50% de la flota habitual por hora.
- **Día pre/pos feriado**: b_dist = 70% de la flota habitual por hora.
- **Día con lluvia** (>5 mm) en franjas afectadas: b_dist = 50% del promedio de la misma hora en día equivalente.
- **Evento disruptivo**: puede excluirse o tratarse diferenciado según criterio técnico de DMT.

### 4.5 IFO por franja (Anexo 1.2)
IFOfranja [%] = (1/ha) * Σ IFOhora

- ha: cantidad de horas en la franja.
- IFOhora: IFO por hora dentro de la franja.

### 4.6 IFO diario (Anexo 1.3)
IFOdiario [%] = (1/fa) * Σ IFOfranja

- fa: cantidad de franjas del tipo de día.
- IFOfranja: IFO por franja del día.

### 4.7 IFO mensual (Anexo 1.4)
IFOmensual [%] = (1/dm) * Σ IFOdiario

- dm: cantidad de días del mes con datos válidos.

### 4.8 IFO sistema (Anexo 1.5)
IFOsistema [%] = (1/nEOT) * Σ IFOmensual(EOT)

Para el control del IFO mensual, la referencia es el **IFO del sistema del mes anterior con reducción del 5%** (ej.: sistema 100% ⇒ umbral 95%).

## 5. Niveles de servicio y umbrales mínimos del IFO (Art. 5 y 6)
### 5.1 Niveles IFO por franja (Art. 5)
- Nivel A: 90% a 100%
- Nivel B: 80% a 89%
- Nivel C: < 80%

### 5.2 Umbrales mínimos obligatorios (Art. 6)
- **IFO mensual**: ninguna EOT puede tener IFO mensual menor a 80% del IFO del sistema del mes anterior (aplicando reducción del 5% según Anexo 1.5).
- **IFO por franja**: ninguna EOT puede tener menos de 80% de su propio IFO de franjas similares contra las que se compare (según fórmulas del anexo).

## 6. Indicador 2: Cantidad Mínima de Buses Diferentes (CBDmin) (Art. 7)
La CBDmin define mínimos obligatorios por **hora** y por **franja**:

| Tipo de Día | Franja Operativa | CBDmin Hora | CBDmin Franja |
|---|---|---:|---:|
| Lunes a Viernes | Madrugada | 3 | 3 |
|  | Pico (mañana) | 4 | 12 |
|  | Pos pico | 3 | 9 |
|  | Pico (tarde) | 4 | 12 |
|  | Pos pico (tarde) | 3 | 6 |
|  | Nocturna | 2 | 4 |
| Sábados | Pico | 3 | 12 |
|  | Pos pico | 2 | 10 |
|  | Nocturna | 2 | 4 |
| Domingos/Feriados | Pos pico | 2 | 9 |

## 7. Verificación de cumplimiento CBDmin (Anexo 2.1)
### 7.1 Cumplimiento por hora
Se verifica:
b_obs^(EOT,h,d) >= CBDmin^(hora,d)

### 7.2 Cumplimiento por franja
Se verifica:
b_obs^(EOT,f,d) >= CBDmin^(franja,d)

## 8. ICCBDM Franja (Anexo 2.2)
El ICCBDM Franja se usa para construir indicadores diario/mensual que sirven para rendimiento operativo (y también para infracciones de CBDmin).

Se define:

ICCBDM_franja = P_hora * I_H(franja,d) + P_franja * I_F(franja,d)

Donde:
- P_hora = 70%
- P_franja = 30%

### 8.1 Componente I_H(franja,d)
I_H(franja,d) = (1/n) * Σ_h ( min( b_obs(EOT,h,d) / CBDmin(h,d), 1 ) )

- n = cantidad de horas de la franja.
- Cada término se “capa” a 1 para evitar compensación.

### 8.2 Componente I_F(franja,d)
I_F(franja,d) = min( b_obs(EOT,f,d) / CBDmin(franja,d), 1 )

También se “capa” a 1 para evitar compensación.

## 9. ICCBDM Diario y Mensual (Anexo 2.3 y 2.4)
- ICCBDM_diario = promedio de ICCBDM_franja del día.
- ICCBDM_mensual = promedio de ICCBDM_diario del mes (días con datos válidos).

## 10. Regla de redondeo (Anexo, Sección 2)
Todos los resultados decimales derivados de fórmulas deben ser **redondeados al número entero superior inmediato**, sin excepción, cuando aplique.

## 11. Reportes, control y “incumplimiento automático” (Art. 12, 13 y 14)
- Fuentes para monitoreo: SNBE (validaciones), sistema GPS (Res. 65/2024), fiscalización excepcional y otros sistemas institucionales.
- Si una EOT incumple provisión de datos (Res. 65/2024 u otra), los indicadores dependientes se consideran **incumplidos automáticamente**.
- Reportes: se emiten por DMT/CID (Centro de Control y Monitoreo) y se envían por correo. Plazo: hasta 7 días corridos luego del día supervisado; IFO mensual hasta 7 días luego del mes.

## 12. Infracciones y sanciones (Art. 15 y 16)
Este documento describe el cálculo. La clasificación sancionatoria se rige por:
- Art. 15 (infracciones por indicador: IFO mensual, IFO franja, ICCBDM Franja, etc.)
- Art. 16 (reincidencias y recargos)

## 13. Implementación gradual (Art. 21)
Entra en vigor: **1 de febrero de 2026**.
- Etapa 1: 2 meses, sin sanciones (solo reporte).
- Etapa 2: 3 meses, con sanciones para L-V (picos y pos picos) y sábados pico.
- Etapa 3: plena, sanciones para todos los indicadores y franjas.

## 14. Ajustes ya realizados
El archivo 
calcular_ifo.py
 ha sido completamente reescrito para ajustarse a la Resolución GVMT N° 120/2025 y a las especificaciones del prompt.

Cambios Implementados
Lógica de Referencia Histórica (Normal vs. Atípica):
Meses Típicos (Feb, Abr-Nov): Usa el promedio de 4 días equivalentes de las últimas 4 semanas.
Meses Atípicos (Ene, Mar, Dic): Implementada la lógica que toma Noviembre como base (del año anterior o actual según corresponda) con los factores de ajuste (0.80 para Ene/Dic, 1.00 para Mar).
Cálculo de 
b_obs
 (Buses Observados):
Se implementó la comparación entre fuentes: MAX(Validaciones, GPS).
Consulta tanto public.servicios_diarios como control_metricas.cbd_detalle_buses (con manejo de errores si la tabla GPS no existe aún).
Indicadores Nuevos y Niveles:
CBD Mínimo: Se verifica el cumplimiento frente a la tabla normativa del Art. 7.
ICCBDM Franja: Se calcula la fórmula combinada (70% Hora + 30% Franja) del Anexo 2.2.
Niveles IFO: Clasificación automática en Niveles A, B y C (<80%).
Ajustes por Días Atípicos:
Se incluyó la lógica para aplicar factores de reducción (30%, 50%, 70%) en casos de feriados o lluvia (aunque los "flags" de lluvia actualmente están por defecto en False hasta que se integre una fuente de datos climáticos).
Ejecución
El script mantiene la compatibilidad con los argumentos de línea de comandos anteriores:

powershell
# Calcular para el día de ayer (defecto)
python calcular_ifo.py
# Calcular para una fecha específica
python calcular_ifo.py --fecha 2026-01-06
# Calcular para un rango
python calcular_ifo.py --desde 2026-01-01 --hasta 2026-01-31

He actualizado completamente 
calcular_ifo.py
 para que sea dinámico y dependa de la configuración en su base de datos, en lugar de usar valores fijos en el código.

Cambios realizados:
Tablas de Configuración:
Ahora el script consulta control_metricas.franjas_operativas para saber qué franjas aplican (Madrugada, Pico, etc.) según el tipo de día (Laboral=5, Sábado=6, Domingo=7) y si están activas.
Consulta control_metricas.cbd_parametros_minimos para obtener los valores exigidos de CBD por hora y franja.
Consulta control_metricas.parametros_ifo para obtener el porcentaje mínimo de cumplimiento requerido (ej. 80% o 90%).
Manejo de Lluvia:
Mantiene la lógica implementada anteriormente: suma la columna mm_caidos de t_casuisticas_lluvia.
Si el total diario es ≥ 5mm, aplica el factor de corrección del 50% al IFO de todo el día.
Tipos de Día:
Se actualizó para usar los IDs numéricos (5, 6, 7) que corresponden a su base de datos.
Detecta automáticamente si es Laboral, Sábado o Domingo/Feriado consultando la tabla de feriados y el calendario.

The script 
calcular_ifo.py
 has been updated to dynamically fetch holidays and "asuetos" from the public.feriados table, as requested.

Key Changes:

Dynamic "Tipo de Día" Identification:
The function 
identificar_tipo_dia
 now queries public.feriados for the specific date.
It checks the descripcion field:
If it contains "asueto" (case-insensitive), it flags the day as an Asueto.
Otherwise, if a record exists, it flags it as a Feriado.
Granular Adjustments:
Asueto: Applies a 50% adjustment factor (0.50) to the historical reference (
b_dist
), treating it similarly to a "Saturday Holiday" or "Rainy Day" in terms of fleet reduction.
Feriado (Normal): Maintains the standard logic (30% for Weekday Feriados, 50% for Saturday Feriados).
Removed Hardcoding: The manual override for 2025-12-30 has been removed. The script now relies entirely on the database to determine if that date (or any other) is an Asueto or Feriado.
To verify: Ensure that 2025-12-30 is inserted into your public.feriados table with a description containing the word "asueto" (e.g., "Declarado asueto"). The script will then automatically apply the 50% factor.

The calculation is currently running in the background for 2025-12-30 to verify stability.

Se ha producido un cambio significativo en la metodología de comparación para los feriados entre lo que dictaba el documento técnico previo (METODO_CALCULO_IFO.md) y lo que establece la nueva Resolución GVMT N° 120/2025.
Aquí te detallo la evolución del criterio según las fuentes:
1. El criterio anterior (Agrupación)
En el documento de metodología anterior, los feriados se clasificaban dentro del tipo de día "No Laboral" junto con los domingos. El cálculo se basaba en:
• Agrupación: Se promediaban todos los domingos y feriados del mes anterior para crear una única base de comparación.
• Justificación: Se hacía de esta manera para evitar comparaciones con "muy pocos datos" al haber pocos feriados en un mes.
2. El criterio actual (Día Equivalente + Factor de Ajuste)
La Resolución GVMT N° 120/2025 cambia esta lógica por una mucho más específica que utiliza el concepto de "Día Equivalente" (comparar lunes con lunes, martes con martes, etc.). Ahora, si un feriado cae en un día de semana, no se compara con un domingo, sino con el promedio histórico de ese mismo día de la semana, aplicando los siguientes factores de ajuste al denominador:
• Feriado en día laborable (Lunes a Viernes): El número de buses esperados se ajusta al 30% de la flota promedio por hora de un día equivalente.
• Feriado en día sábado: El número de buses esperados se ajusta al 50% de la flota promedio por hora de un día equivalente.
• Días Pre y Pos Feriado: También se introdujo un ajuste nuevo, donde la exigencia baja al 70% de la flota habitual.
Resumen del cambio
Característica
Metodología Anterior (MD)
Resolución GVMT N° 120/2025
Comparación
Contra el promedio de todos los domingos/feriados del mes.
Contra su Día Equivalente (mismo día de la semana).
Exigencia
Variable según el promedio del grupo "No Laboral".
Fija mediante factores de ajuste (30%, 50% o 70%).
Este nuevo enfoque de la resolución permite una medición más precisa, reconociendo que la operación de un "lunes feriado" tiene una base histórica distinta a la de un "domingo", aunque ambos sean días no laborables.