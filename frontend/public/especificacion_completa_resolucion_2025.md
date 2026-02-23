# Especificación Técnica de Métricas y Casuísticas - Proyecto de Resolución GVMT 2025

Este documento detalla todas las reglas de negocio y algoritmos de cálculo establecidos en el Resolución GVMT N° 120/2025 para la validación de sistemas de monitoreo de transporte.

## 1. Reglas Generales de Cálculo
- **Fuentes de Datos:** Cruce obligatorio entre datos GPS en tiempo real (cada 10 segundos según Res. 65/2024) y validaciones del billetaje electrónico [1, 2].
- **Redondeo:** Originalmente al entero superior, pero según la **Resolución modificatoria de 2026**, los resultados ahora se redondean a **dos dígitos decimales** [3, 4].
- **Omisión de Datos:** Si una EOT no transmite datos GPS, los indicadores se consideran **incumplidos automáticamente** [2, 5].

## 2. Índice de Flota Operativa (IFO)
Mide disponibilidad real vs. media histórica.

### A. Cálculo del Denominador Histórico ($b_{dist}$)
El sistema debe seleccionar el método según el mes analizado:

1. **Meses Típicos (Feb, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov):**
   - Media de buses de las **últimas 4 semanas previas** en el mismo día equivalente [6].
   - **Regla de Outliers (Descarte):** Si uno de esos 4 días fue feriado o tuvo un evento disruptivo, debe ser **descartado y reemplazado** por el mismo día de la semana inmediata anterior hasta completar 4 días válidos [7, 8].

2. **Meses Atípicos (Enero, Marzo, Diciembre):**
   - **Enero:** Media de los días equivalentes de **noviembre del año anterior** × factor **0,80** [9, 10].
   - **Marzo:** Media de los días equivalentes de **noviembre del año anterior** (sin factor) [11, 12].
   - **Diciembre:** Media de los días equivalentes de **noviembre del mismo año** × factor **0,80** [13, 14].
   - *Nota:* Para estas referencias de noviembre, también aplica la regla de descartar días atípicos y retroceder hasta octubre si es necesario [13, 15].

### B. Ajustes por Días Atípicos (Sobre la Flota Esperada)
Independientemente del mes, si el día es especial se aplican estos factores de reducción:
- **Feriados (Lunes a Viernes):** 30% de la flota habitual [16, 17].
- **Feriados (Sábados):** 50% de la flota habitual [18, 19].
- **Días Pre y Pos Feriados:** 70% de la flota habitual [18, 19].
- **Eventos Disruptivos:** La DMT puede autorizar la exclusión del día o tratamiento diferenciado tras comunicación de la EOT [18, 20].

### C. Ajustes por Clima (Lluvias)
Basado en datos de la DINAC (Percentil 75 de las estaciones del AMA) [21, 22]:
- **Tipo A (≤ 5 mm):** Sin factor de ajuste [23].
- **Tipo B (> 5 mm a 20 mm):** Factor de **80%** (0.8) sobre la flota esperada [20, 23].
- **Tipo C (> 20 mm):** Factor de **50%** (0.5) sobre la flota esperada [21].

## 3. Cantidad Mínima de Buses Diferentes (CBDmín)
Establece el piso mínimo por hora y por franja.

- **Restricción de Prevalencia:** Ningún ajuste (por lluvia, feriado o mes atípico) puede resultar en un número de buses inferior al **CBDmín** fijado en la tabla oficial. El CBDmín es el **mínimo vital** innegociable [16, 24].
- **Tabla de Umbrales (Laboral):** Madrugada (3h/3f), Pico (4h/12f), Pos-Pico (3h/9f), Nocturna (2h/4f) [25, 26].

## 4. Índice de Cumplimiento CBD Franja ($IC_{CBD~franja}$)
Fórmula para determinar el grado de infracción:
$$IC_{CBD~franja} = (0.70 \times IH_{franja}) + (0.30 \times IF_{franja})$$
- **Tope Crítico de Compensación:** Tanto el cumplimiento por hora ($IH$) como el de franja ($IF$) tienen un **valor máximo de 1 (100%)**. Un exceso de buses en una hora **NO compensa** la falta de buses en otra [27, 28].

## 5. Fases de Implementación y Sanciones
- **Fase 1-A (2 meses):** Monitoreo de IFO y CBDmín en franjas Pico Mañana, Pos Pico Mañana, Pico Tarde y Sábados Pico. **Sin sanciones** [29-31].
- **Fase 1-B (6 meses):** Cobertura de las 6 franjas laborales + Sábados, Domingos y Feriados. **Con aplicación de sanciones** [29, 31, 32].
- **Fase 2:** Implementación gradual del **ICF** (Índice de Cumplimiento de Frecuencia) a medida que se validen las programaciones operativas (FI-POT) [33, 34].

## 6. Escala de Penalizaciones (Res. 07/2024)
- **IFO Mensual < (Sistema anterior - 5%):** Infracción Gravísima [35].
- **CBDmín Hora Incumplido:** Infracción Intermedia [35, 36].
- **CBDmín Franja Incumplido:** Infracción Grave [35, 37].
- **IFO Franja Pico < 80%:** Infracción Intermedia [35, 38].

Aquí tienes el texto íntegro de la **Resolución GVMT Nº 120/2025**, consolidada con las modificaciones introducidas por la **Resolución GVMT Nº ____/2026**, en formato Markdown:

---

# RESOLUCIÓN GVMT Nº 120/2025

**"POR LA CUAL SE ESTABLECEN NUEVOS INDICADORES DE DESEMPEÑO, NIVELES DE SERVICIO Y PARÁMETROS DE EVALUACIÓN DE RENDIMIENTO PARA EL SERVICIO DE TRANSPORTE PÚBLICO METROPOLITANO DE PASAJEROS Y SE IMPLEMENTA UN SISTEMA INTEGRAL DE CONTROL Y MONITOREO"**.

---

### **CAPÍTULO I: GENERALIDADES**

**Artículo 1º.- ALCANCE.** Establecer nuevos indicadores de desempeño, niveles de servicio y parámetros de evaluación de rendimiento, además de un sistema integral de control y monitoreo y un régimen de infracciones y sanciones aplicables a las empresas operadoras de transporte (EOT).

**Artículo 2º.- DEFINICIONES.** Establecer las definiciones espaciales, temporales y técnicas (Ruta, Cabecera, Itinerario, Línea, Frecuencia, Intervalo, Kilómetro operativo, etc.). Se destacan:
*   **Día equivalente:** Día de la semana similar al día observado utilizado como referencia histórica.
*   **Días atípicos:** Feriados, días pre/pos feriado, días con lluvia (> 5 mm) y eventos disruptivos.
*   **Buses diferentes:** Vehículos distintos identificados por transmisión GPS y/o validaciones en el SNBE.

---

### **CAPÍTULO II: INDICADORES DE DESEMPEÑO Y NIVELES DE SERVICIO**

**Artículo 3º.- INDICADORES DE DESEMPEÑO.**
1.  **Índice de Flota Operativa (IFO):** Mide la disponibilidad real de buses comparando buses diferentes actuales vs. promedio histórico.
2.  **Cantidad Mínima de Buses Diferentes (CBDmin):** Número mínimo de buses exigido por hora y franja operativa.
3.  **Índice de Cumplimiento de Frecuencia (ICF):** Compara salidas realizadas vs. programadas.

**Artículo 4º.- DETERMINACIÓN DE FRANJAS OPERATIVAS.** Define las franjas: Madrugada (4:00-4:59), Pico Mañana (5:00-7:59), Entre Picos (8:00-15:59), Pico Tarde (16:00-18:59), Pos Pico Tarde (19:00-20:59) y Nocturna (21:00-22:59).

**Artículo 5º.- NIVELES DE SERVICIO IFO FRANJA OPERATIVA.** (Modificado por Res. 2026):
1.  **Nivel A:** Cumplimiento igual o mayor a 90%.
2.  **Nivel B:** Cumplimiento igual o mayor que 80% e inferior a 90%.
3.  **Nivel C:** Cumplimiento inferior a 80%.

**Artículo 6º.- UMBRALES MÍNIMOS OBLIGATORIOS DEL IFO.**
1.  **IFO Mensual:** No inferior al IFO del sistema del mes anterior menos 5 puntos porcentuales.
2.  **IFO por franja:** Ninguna EOT podrá tener menos del 80% de su propio IFO de referencia.

**Artículo 7º.- CANTIDAD MÍNIMA DE BUSES DIFERENTES (CBDmin).** Establece la tabla de buses mínimos (Ej: 12 buses en franja Pico para Lunes a Viernes).

**Artículos 8º al 11º.-** Establecen la vigencia del ICF supeditada a programaciones aprobadas, la exclusión de líneas Búho del cálculo de IFO/CBDmin y el uso de un umbral del 95% para constancias de subsidio.

---

### **CAPÍTULO III: SISTEMA INTEGRAL DE CONTROL Y MONITOREO**

**Artículo 12º.- ALCANCE INTEGRAL.** Conformado por el SNBE, el sistema de transmisión de datos operativos (Res. 65/2024), fiscalizaciones en calle y otros registros institucionales.

**Artículo 13º.- INCUMPLIMIENTO AUTOMÁTICO.** El incumplimiento de la Res. 65/2024 (transmisión GPS) implica que los indicadores se consideren incumplidos automáticamente.

**Artículo 14º.- REPORTES.** La DMT enviará reportes diarios por correo electrónico a las EOT en un plazo máximo de 7 días corridos tras la supervisión.

---

### **CAPÍTULO IV: INFRACCIONES Y SANCIONES**

**Artículo 15º.- INFRACCIONES.** (Modificado por Res. 2026):

| Orden | Indicador | Infracción | Clasificación | Sanción (Jornales) |
| :--- | :--- | :--- | :--- | :--- |
| **15.1** | IFO Mensual | IFO EOT < (IFO Sistema Mes Anterior - 5 pts) | Gravísima | 173 |
| **15.2** | IFO Franja | Nivel B en 5 o más franjas Pico en el mes | Leve | 10 |
| **15.3** | IFO Franja | Nivel C en una o más franjas Pico en el día | Intermedia | 20 |
| **15.4** | IFO Franja | Nivel B en 5 o más franjas Pos Pico en el mes | Leve | 10 |
| **15.5** | IFO Franja | Nivel C en una o más franjas Pos Pico en el día | Intermedia | 20 |
| **15.6** | CBDmin | Incumplimiento del ICCBDM Franja en el día | Intermedia | 20 |

**Artículo 16º.- REINCIDENCIAS.** (Modificado por Res. 2026):
*   **16.1 (Base 15.1):** Reiteración en los siguientes 6 meses: 173 jornales + 30% recargo.
*   **16.2 (Base 15.2):** Reiteración en los siguientes 6 meses: 20 jornales.
*   **16.3 (Base 15.4):** Reiteración en los siguientes 6 meses: 20 jornales.

**Artículo 17º.-** (Derogado por Res. 2026).

**Artículo 18º.- INFRACCIONES QUE AUTORIZAN SUMARIO.**
1.  Segunda reiteración de IFO Mensual en 6 meses (3 incumplimientos totales).
2.  Suma de 20 infracciones (leves, intermedias o graves) en un trimestre.

**Artículo 19º.- ACTAS DE COMPROBACIÓN.** Los incumplimientos detectados por la CID requieren **aprobación de la DMT** para tener validez como infracción.

**Artículo 20º.- EFECTOS DEL PAGO.** El pago de multas no excluye la infracción del cómputo para reincidencias ni sumarios.

---

### **CAPÍTULO V: DISPOSICIONES TRANSITORIAS Y FINALES**

**Artículo 21º.- ENTRADA EN VIGOR Y GRADUALIDAD.**
1.  **Etapa 1 (Adaptación):** 01/02/2026 - 31/03/2026. Sin sanciones.
2.  **Etapa 2 (Parcial):** 01/04/2026 - 30/06/2026. Sanciones solo en Picos y Pos Picos (L-V) y Picos (Sáb).
3.  **Etapa 3 (Plena):** Desde 01/07/2026. Todas las franjas operativas.

**Artículo 24º y 25º.- DEROGACIONES.** Abroga la Res. 11/2024 y deroga las Res. 42/2022 (salvo Art. 2), 177/2023 y puntos específicos de la 07/2024.

---

### **ANEXO: FÓRMULAS DE APLICACIÓN**

*   **IFO Hora:** $IFO_{hora} [\%] = (b_{obs}^{h,a} / b_{dist}^{h,d}) * 100$.
*   **Redondeo:** (Modificado por Res. 2026) Los números decimales serán redondeados a **dos dígitos**.
*   **Ajuste Meses Atípicos:** En enero y diciembre se aplica un factor de corrección de **0,80**.
*   **ICCBDM Franja:** $(0,70 * IH_{franja,d}) + (0,30 * IF_{franja,d})$.

Aquí tienes el **Anexo de la Resolución GVMT Nº 120/2025** sobre fórmulas de aplicación de indicadores de desempeño, presentado en formato Markdown y consolidado con las actualizaciones de la resolución modificatoria de 2026.

---

# ANEXO DE LA RESOLUCIÓN GVMT Nº 120/2025
## SOBRE FÓRMULAS DE APLICACIÓN DE INDICADORES DE DESEMPEÑO

### 1. Índice de Flota Operativa (IFO)
El IFO se basa en los datos históricos de operación de los servicios de transporte público para servir de base para el control y monitoreo de la operativa de cada empresa.

#### 1.1. IFO Hora
Este indicador es el resultado del cálculo, por cada hora reloj, de la relación entre los buses diferentes en circulación durante una hora determinada y la media de los buses distintos que operaron en días equivalentes a la misma hora, según los datos históricos.

**Fórmula:**
$$IFO_{hora} [\%] = \frac{b_{obs}^{h,a}}{b_{dist}^{h,d}} * 100$$

**Donde:**
*   $b_{obs}^{h,a}$: buses diferentes observados en la hora $h$, del día objeto de análisis.
*   $b_{dist}^{h,d}$: media de buses distintos que operaron en la hora $h$, en un día $d$.

**Consideraciones para la media de buses ($b_{dist}$):**
*   **Meses típicos:** (Feb, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov). La cantidad se obtiene del promedio de las últimas cuatro semanas previas al día objeto de análisis.
*   **Meses atípicos:** (Ene, Mar, Dic). Se aplican factores de corrección. Para **Enero** y **Diciembre**, la referencia es la media de buses de noviembre del año anterior multiplicado por un factor de **0,80**.

**Criterios de ajuste para días atípicos:**
*   **Feriado día laborable:** Se exige el **30%** de la flota promedio por hora en un día equivalente.
*   **Feriado sábado:** Se exige el **50%** de la flota promedio por hora en un día equivalente.
*   **Días pre y pos feriados:** Se exige el **70%** de la flota habitual por hora en un día equivalente.
*   **Día con lluvia (> 5 mm):** Se considerará el **50%** del promedio de la misma hora en un día equivalente.

#### 1.2. IFO Franja operativa
Es el promedio de los $IFO_{hora}$ de todas las horas comprendidas en cada franja operativa.
**Fórmula:** $IFO_{franja} [\%] = \frac{1}{h_d} \sum IFO_{hora}^f$

#### 1.3. IFO Diario
Promedio de los $IFO_{franja}$ correspondientes al tipo de día objeto de análisis.
**Fórmula:** $IFO_{diario} [\%] = \frac{1}{f_d} \sum IFO_{franja}^d$

#### 1.4. IFO Mensual
Promedio de los índices diarios registrados durante un mes calendario completo, considerando únicamente los días con datos válidos.
**Fórmula:** $IFO_{mensual} [\%] = \frac{1}{d_m} \sum IFO_{diario}^m$

#### 1.5. IFO Sistema
Promedio de los índices mensuales de cada empresa operadora de transporte (EOT) en el mismo mes.
**Fórmula:** $IFO_{sistema} [\%] = \frac{1}{n_{EOT}} \sum IFO_{mensual, EOT}$

---

### 2. Cantidad mínima de buses diferentes (CBDmin)
Establece la exigencia por niveles de hora y franja operativa según el tipo de día.

#### 2.1. Fórmulas de control
*   **Por hora:** $b_{obs}^{EOT,h,d} \geq CBD_{min}^{hora,d}$
*   **Por franja:** $b_{obs}^{EOT,f,d} \geq CBD_{min}^{franja,d}$

#### 2.2. Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Franja (ICCBDM Franja)
Este índice combina datos observados y exigidos en un solo indicador ponderado.
**Fórmula:** $(P_{CBD hora} * IH_{franja,d}) + (P_{CBD franja} * IF_{franja,d}) = ICCBDM_{franja}$

**Ponderación:**
*   $P_{CBD hora}$ (Peso del cumplimiento por hora): **70%**.
*   $P_{CBD franja}$ (Peso del cumplimiento por franja): **30%**.
*   $IH_{franja,d}$: promedio de cumplimiento horario (máximo valor posible = 1).
*   $IF_{franja,d}$: índice de la franja (máximo valor posible = 1).

#### 2.3. ICCBDM Diario e ICCBDM Mensual
Calculados como el promedio de los índices de las franjas que componen el día (diario) y el promedio de los índices diarios del mes (mensual).

---

### 3. Transformación y Redondeo de Datos
*   **Articulación:** Los insumos de GPS y billetaje se integran en una herramienta de cálculo que realiza depuración y combinación.
*   **Regla de Redondeo:** Originalmente la norma preveía el redondeo al entero superior. Sin embargo, según la **Resolución modificatoria de 2026 (Art. 2)**, la regla vigente establece: **"Los números decimales serán redondeados a dos dígitos"**.