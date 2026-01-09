# Especificación Técnica de Métricas y Casuísticas - Proyecto de Resolución GVMT 2025

Este documento detalla todas las reglas de negocio y algoritmos de cálculo establecidos en el Memorándum DMT N° 130/2025 para la validación de sistemas de monitoreo de transporte.

## 1. Reglas Generales de Cálculo
- **Fuentes de Datos:** Cruce obligatorio entre datos GPS en tiempo real (cada 10 segundos según Res. 65/2024) y validaciones del billetaje electrónico [1, 2].
- **Redondeo:** Todos los resultados decimales de las fórmulas deben redondearse al **entero superior inmediato** (Ceil), sin excepciones [3, 4].
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