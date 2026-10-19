# Resumen Ejecutivo: Exclusiones en el Cálculo del IFO Mes

Para el cálculo del **IFO Mensual** (que define la evaluación de desempeño y la infracción gravísima del **Art. 15.1 de 173 jornales**), el marco normativo de las **Resoluciones GVMT N° 120/2025, 21/2026 y 104/2026** establece dos niveles estrictos de depuración: **exclusión por calendario (días)** y **exclusión por franja horaria**.

---

## 1. Cuadro General de Exclusiones

| Categoría | Elemento / Condición | ¿Se incluye en el IFO Mes? | Base Legal / Criterio Técnico | Filtro en el Sistema (BD / SQL) |
| :--- | :--- | :---: | :--- | :--- |
| **Días del Calendario** | **Días Hábiles (Lunes a Viernes)** | ✅ **SÍ** | Operación ordinaria base | `EXTRACT(ISODOW) BETWEEN 1 AND 5` |
| | **Sábados** | ✅ **SÍ** | Operación de fin de semana (solo picos) | `EXTRACT(ISODOW) = 6` |
| | **Domingos** | ❌ **EXCLUIDO** | Regla 4 (Res. 104/2026) y Res. 21/2026 | `EXTRACT(ISODOW FROM fecha) < 7` |
| | **Feriados Oficiales / Decretados** | ❌ **EXCLUIDO** | Días no laborales nacionales | `fecha NOT IN (SELECT fecha FROM public.feriados)` |
| | **Pre y Pos Feriados** | ❌ **EXCLUIDO** | Considerados días atípicos en el cierre mensual (Res. 120/2025) | `fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos WHERE tipo_atipico = 'PRE_POS_FERIADO')` |
| | **Días Lluviosos (> 5 mm DINAC)** | ❌ **EXCLUIDO** | Días atípicos por contingencia climática | `fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos WHERE tipo_atipico = 'LLUVIA')` |
| | **Eventos Extraordinarios / Asuetos** | ❌ **EXCLUIDO** | Días atípicos por fuerza mayor declarada | `control_metricas.dias_atipicos` |
| **Franjas Horarias** | **Pico (Mañana y Tarde)** | ✅ **SÍ** | Franjas principales reguladas | Denominación contiene `PICO` |
| *(Etapa 2 Vigente)* | **Pos Pico Lunes a Viernes** | ✅ **SÍ** | Entre Picos y Pos Pico Tarde | Denominación contiene `POS PICO` |
| | **Pos Pico de Sábados** | ❌ **EXCLUIDO** | Prórroga Etapa 2 (Res. 104/2026) | `dia = 6 AND cat = 'POS_PICO'` se descarta |
| | **Madrugada (04:00 - 04:59)** | ❌ **EXCLUIDO** | Fuera del régimen sancionatorio | `denominacion NOT LIKE '%MADRUGADA%'` |
| | **Nocturna (21:00 - 22:59)** | ❌ **EXCLUIDO** | Fuera del régimen sancionatorio | `denominacion NOT LIKE '%NOCTURN%'` |
| | **Franjas de Domingos y Feriados** | ❌ **EXCLUIDO** | Jornadas inhábiles | Descarte total de la jornada |
| **Comportamiento Operativo** | **Días con Multa Diaria (Nivel C / 15.3 / 15.5)** | ✅ **SE COMPUTAN** | **Regla N° 4 Oficial (Res. 104/2026):** Se evalúan todos los días hábiles, sin exclusión adicional por faltas previas. | No se descartan del promedio |

---

## 2. Detalle de Criterios Clave

### A. Tratamiento de Pre y Pos Feriados
* **En el día a día (Evaluación Diaria por Franja):** Se fiscalizan en calle, pero con un **Factor de Ajuste del 70%** (se exige el 70% de la flota mínima habitual).
* **En el cierre mensual (Art. 15.1):** **Quedan desconsiderados del promedio**, para evitar que días con demanda atípica o exigencia reducida distorsionen la media mensual estructural de la empresa.

### B. Franjas no computables (Madrugada, Noche y Pos Pico Sábado)
* Estas franjas se monitorean exclusivamente a título informativo y estadístico.
* **No suman ni restan** en el IFO Diario computable ni en el IFO Mensual puncionable.

### C. Tope Diario Individual
* Cada día evaluable que ingresa al promedio mensual tiene un tope normativo de **1,10 (110%)**:
  $$\text{IFO Día Topeado} = \min(\text{Promedio Franjas Computables}, 110\%)$$
* Esto evita que sobrecumplimientos extraordinarios en un solo día compensen artificialmente caídas graves de servicio en otras jornadas.

---

## 3. Caso Práctico de Depuración: Septiembre 2026 (30 días calendario)

* **Total Días Mes Calendario:** 30 días
  * **- 4 Domingos** (6, 13, 20, 27)
  * **- 1 Feriado Nacional:** 28/09 (Boquerón)
  * **- 1 Pos-Feriado Atípico:** 29/09
  * **- 6 Días Atípicos Lluvia > 5mm DINAC** (4, 10, 18, 19, 21, 30)
* **Días descartados del promedio:** **12 días** (4 domingos + 1 feriado + 1 pos-feriado + 6 lluvias).
* **Días efectivos en la base del promedio:** **18 días hábiles/sábados evaluables.**
