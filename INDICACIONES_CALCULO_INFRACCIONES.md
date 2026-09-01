# Motor de Reglas - Resolución GVMT N° 120/2025
## Especificaciones para el Cálculo de Infracciones y Reincidencias

Este documento detalla la lógica interna aplicada por el sistema para la detección automática de infracciones y el cálculo de sanciones pecuniarias basadas en el desempeño de la flota.

---

### 1. Definiciones de Base
*   **Nivel B:** Cumplimiento de **IFO** entre **80.00% y 89.99%**.
*   **Nivel C:** Cumplimiento de **IFO** inferior al **80.00%**.
*   **Franjas Pico:**
    *   Pico Mañana (Laboral)
    *   Pico Tarde (Laboral)
    *   Pico Sábado
*   **Franjas Pos Pico:**
    *   Pos Pico - Entre Picos (Laboral)
    *   Pos Pico Tarde (Laboral)
    *   Pos Pico Sábado
*   **Exclusiones:** Quedan excluidas del cálculo de infracciones las franjas **Madrugada**, **Nocturna**, y la totalidad de la operación en **Domingos y Feriados**.
*   **Valor del Jornal:** **111.502 Gs.**

---

### 2. Lógica de Infracciones (Artículo 15)

| Regla | Concepto | Criterio de Activación | Sanción | Límite |
| :--- | :--- | :--- | :--- | :--- |
| **15.2** | Picos - Nivel B | Acumular **5 franjas pico** en Nivel B durante el mes calendario. | 10 Jornales | Max. 1 vez al mes. |
| **15.3** | Picos - Nivel C | Al menos **una franja pico** en Nivel C en el día. | 20 Jornales | 1 diaria (por día con falta). |
| **15.4** | Pos Pico - Nivel B | Acumular **5 franjas pos pico** en Nivel B durante el mes calendario. | 10 Jornales | Max. 1 vez al mes. |
| **15.5** | Pos Pico - Nivel C | Al menos **una franja pos pico** en Nivel C en el día. | 20 Jornales | 1 diaria (por día con falta). |
| **15.6** | ICCBDM (Buses) | Incumplimiento del buses mínimos (**índice < 100%**) en franjas Pico o Pos Pico. | 20 Jornales | 1 diaria (por día con falta). |

---

### 3. Lógica de Reincidencias (Artículo 16)
*Requiere la existencia previa de una infracción confirmada bajo el Artículo 15.*

| Regla | Concepto | Criterio de Reincidencia | Sanción |
| :--- | :--- | :--- | :--- |
| **16.2** | Picos - Nivel B | Tras cumplir las 5 faltas iniciales (Art. 15.2), acumular **5 adicionales** dentro de los **7 días** posteriores. | 20 Jornales |
| **16.3** | Picos - Nivel C | Nueva falta Nivel C en picos dentro de los **7 días** posteriores a la infracción del Art. 15.3. | 45 Jornales |
| **16.4** | Pos Pico - Nivel B | Tras cumplir las 5 faltas iniciales (Art. 15.4), acumular **5 adicionales** dentro de los **7 días** posteriores. | 20 Jornales |
| **16.5** | Pos Pico - Nivel C | Nueva falta Nivel C en pos picos dentro de los **7 días** posteriores a la infracción del Art. 15.5. | 45 Jornales |
| **16.6** | ICCBDM (Buses) | Reincidir en falta de CBD dentro de los **2 días** posteriores a la falta del Art. 15.6. | 45 Jornales |

---

### 4. Regla de Exclusión Diaria por Non Bis In Idem (Ley N° 6715/2021)
Para garantizar el principio de proporcionalidad y evitar la doble sanción sobre una misma jornada operativa:
*   **Franjas Pico:** Si en un día se aplica sanción directa de Nivel C (**Art. 15.3**), las franjas Pico de esa jornada **no se contabilizan** en el acumulador mensual de Nivel B (**Art. 15.2**). Sin embargo, las franjas Pos Pico en Nivel B de ese día sí se acumulan para el **Art. 15.4** (salvo que también haya Nivel C en Pos Pico).
*   **Franjas Pos Pico:** Si en un día se aplica sanción directa de Nivel C (**Art. 15.5**), las franjas Pos Pico de esa jornada **no se contabilizan** en el acumulador mensual de Nivel B (**Art. 15.4**). Las franjas Pico en Nivel B siguen acumulando para el **Art. 15.2**.
*   **ICCBDM (Art. 15.6):** Es independiente y evalúa flota mínima de buses; no interfiere ni es bloqueado por las exclusiones de IFO.

---

### 5. Flujo de Procesamiento del Sistema
1.  **Filtro Inicial:** El sistema descarta automáticamente cualquier dato correspondiente a Domingos, Feriados, días atípicos o franjas fuera del espectro regulado (Madrugada/Nocturna).
2.  **Identificación Diaria:** El sistema clasifica las franjas restantes como Nivel A, B o C según el IFO calculado y verifica el ICCBDM.
3.  **Liquidación y Exclusión Diaria:**
    *   Se liquidan las faltas diarias directas (Arts. 15.3, 15.5 y 15.6).
    *   Se aplica el filtro excluyente de días sancionados con Nivel C antes de acumular franjas de Nivel B.
4.  **Acumulación Mensual:** Se verifica si el acumulador de franjas limpias de Nivel B alcanza el umbral de 5 franjas para gatillar el Art. 15.2 o 15.4.
5.  **Evaluación de Reincidencias:** Se evalúa el historial en la ventana de 6 meses para aplicar los agravantes de los Arts. 16.1, 16.2 o 16.4.
6.  **Cálculo:** `Cantidad de Jornales * Valor Jornal Vigente`.
