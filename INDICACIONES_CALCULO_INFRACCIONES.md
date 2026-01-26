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

### 4. Flujo de Procesamiento del Sistema
1.  **Filtro Inicial:** El sistema descarta automáticamente cualquier dato correspondiente a Domingos, Feriados o franjas fuera del espectro Pico/Pos Pico (Madrugada/Nocturna).
2.  **Identificación:** El sistema clasifica las franjas restantes como Nivel A, B o C según el IFO calculado.
3.  **Contabilización:**
    *   Para Niveles C y CBD: Se evalúa el día actual.
    *   Para Niveles B: Se verifica si se alcanzó el umbral de 5 franjas acumuladas en el mes.
4.  **Evaluación de Reincidencia:** Se busca retrospectivamente en el historial si ya existía una infracción en la ventana de tiempo definida.
5.  **Cálculo:** `Cantidad de Jornales * 111,502`.
