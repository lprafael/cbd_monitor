PROMPT PARA GENERACIÓN DE SCRIPT PYTHON
Resolución GVMT N° 120/2025 — Verificación diaria de desempeño (IFO y CBDmin/ICCBDM)

Crea un script Python llamado `verificacion_desempeno_diario_gvmt120.py` para calcular y verificar diariamente, por Empresa Operadora de Transporte (EOT), los indicadores definidos en la Resolución GVMT N° 120/2025:
1) Índice de Flota Operativa (IFO) a nivel hora y franja (y agregados diario/mensual si corresponde)
2) Cantidad Mínima de Buses Diferentes (CBDmin) y el Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Franja (ICCBDM Franja)

El script debe conectarse a PostgreSQL y procesar FECHA_ANALISIS (por defecto: día anterior), generando un dataset de resultados por EOT y franja operativa.

REQUISITOS NORMATIVOS OBLIGATORIOS (no inventar reglas fuera de esto):
- Franjas horarias: usar Art. 4 de la Resolución GVMT 120/2025.
- CBDmin: usar la tabla de Art. 7 (CBDmin hora y CBDmin franja por tipo de día y franja).
- IFO: usar Anexo Sección 1 (meses típicos/atípicos, días equivalentes, ajustes por días atípicos).
- Días atípicos: usar definiciones del Art. 2 y ajustes del Anexo 1.1.2.
- Niveles de servicio IFO franja: Art. 5 (A:90-100, B:80-89, C:<80).
- Umbrales mínimos obligatorios del IFO: Art. 6 (IFO mensual y IFO franja).
- ICCBDM Franja: usar fórmula del Anexo 2.2 con pesos 70% hora / 30% franja y tope máximo 1.0 en cada componente.
- Redondeo: resultados decimales que deban consolidarse en enteros aplicar redondeo al entero superior inmediato, sin excepción, según Anexo sección “Redondeo”.
- Incumplimiento automático: si faltan datos por incumplimiento de provisión de datos operativos (Res. 65/2024 u otra), marcar indicadores dependientes como incumplidos automáticamente (Art. 13).

1) INPUTS / PARÁMETROS
- FECHA_ANALISIS (YYYY-MM-DD). Por defecto, ayer.
- Conexión PostgreSQL mediante variables de entorno: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.

2) FUENTES DE DATOS
El cálculo de “buses diferentes observados” debe poder usar fuentes:
- SNBE / validaciones (si existe una tabla operacional equivalente a `public.servicios_diarios`: id_eot_catalogo, fecha, hora, idsam)
- GPS / monitoreo (si existe una tabla equivalente a `control_metricas.cbd_detalle_buses`: id_eot_vmt_hex, fecha, hora, mean_id)
El script debe unificar ambas fuentes a un identificador único de EOT mediante `public.eots` (campos típicos: cod_catalogo, id_eot_vmt_hex, eot_id).

Regla de buses observados por hora (b_obs):
- Para cada EOT + FECHA_ANALISIS + hora reloj, calcular:
  - b_obs_val = COUNT(DISTINCT idsam) desde validaciones
  - b_obs_gps = COUNT(DISTINCT mean_id) desde GPS
  - b_obs = MAX(b_obs_val, b_obs_gps)
- También debe guardarse el origen (si ganó validaciones, ganó GPS, o empate).

3) DETERMINACIÓN DE TIPO DE DÍA Y CASUÍSTICAS
- Determinar tipo de día base: Lunes-Viernes, Sábado, Domingo/Feriado.
- Identificar feriados desde tabla tipo `public.feriados`.
- Identificar “día con lluvia” según el criterio normativo: precipitaciones > 5mm (DINAC). Si se tiene tabla interna de lluvia, usarla como proxy, pero el criterio lógico debe representar “>5mm”.
- Identificar “día pre/pos feriado” y “evento disruptivo” si existen registros. Si no existen, dejar el flag en False.
- Reportar qué ajuste se aplicó.

4) CÁLCULO DE IFO POR HORA (Anexo 1.1)
IFOhora[%] = (b_obs(h) / b_dist(h)) * 100

Donde b_dist(h) es la “media de buses distintos” esperada para esa hora, calculada según:
- Meses típicos: Feb, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov => usar 4 días equivalentes válidos de las últimas 4 semanas previas. Si algún equivalente fue atípico, reemplazar por el equivalente anterior.
- Meses atípicos:
  - Enero: media noviembre año anterior * 0.80
  - Marzo: media noviembre año anterior
  - Diciembre: media noviembre mismo año * 0.80
- Ajustes por días atípicos:
  - Feriado día laborable: 30% de la flota habitual por hora
  - Feriado sábado: 50%
  - Pre/pos feriado: 70%
  - Lluvia: 50% del promedio de la misma hora en día equivalente (solo franjas afectadas)
  - Evento disruptivo: excluir o tratar diferenciado según criterio (si no hay dato, marcar como “requiere validación DMT”)

El script debe “simular” o materializar b_dist usando una tabla histórica disponible (ej.: una tabla de histórico de buses por EOT/hora/día). Si no existe, el script debe dejar encapsulada una función `get_b_dist(...)` con SQL claramente indicado para el repositorio real.

5) IFO POR FRANJA (Anexo 1.2)
IFOfranja = promedio de los IFOhora dentro de la franja operativa de Art. 4.

Clasificar nivel de servicio según Art. 5:
- A: 90-100
- B: 80-89
- C: <80

6) CBDmin Y CUMPLIMIENTO (Art. 7 + Anexo 2.1)
- Para cada hora y franja, obtener CBDmin hora y CBDmin franja de la tabla normativa (Art. 7).
- Cumplimiento hora: b_obs(EOT,h) >= CBDmin(h)
- Cumplimiento franja: b_obs(EOT,franja) >= CBDmin(franja)

7) ICCBDM FRANJA (Anexo 2.2)
ICCBDM_franja = 0.70 * I_H(franja,d) + 0.30 * I_F(franja,d)
- I_H = promedio de min(b_obs(h)/CBDmin(h), 1) en las horas de la franja
- I_F = min(b_obs(franja)/CBDmin(franja), 1)
No permitir compensación: capar cada ratio a 1.

8) OUTPUT DEL REPORTE DIARIO
Generar una tabla/estructura (para insertar o exportar a CSV/JSON) con un registro por EOT + franja:
- fecha_analisis
- eot_id
- tipo_dia (LV / SAB / DOMFER)
- franja_operativa (id y nombre)
- horas_en_franja
- b_obs_promedio_franja (promedio b_obs por hora en esa franja)
- b_obs_min_hora_franja, b_obs_max_hora_franja
- origen_b_obs (resumen: % horas ganó GPS vs validaciones vs empate)
- b_dist_promedio_franja (promedio de b_dist por hora usado en IFO)
- ifo_franja
- ifo_nivel_servicio (A/B/C)
- cbdmin_hora (valor normativo aplicable por hora; si cambia por hora, incluir resumen)
- cbdmin_franja
- iccbdm_franja
- flags_atipico: feriado, prepos, lluvia, disruptivo
- ajuste_aplicado (texto)
- datos_validos (True/False)
- incumplimiento_automatico (True/False y motivo si aplica)

9) CALIDAD / ROBUSTEZ
- Manejo de horas sin datos: considerar b_obs=0 (pero distinguir “sin datos” vs “0 real” si la fuente lo permite).
- Validar días con datos válidos (Art. 2) y marcar los que no.
- Logging claro por pasos.
- SQL organizado y parametrizado.
- No hardcodear umbrales de ICF (Art. 8 dice que se definirá por resolución separada).

ENTREGABLE
- Proveer el script completo en Python, con funciones separadas:
  - load_params()
  - get_franjas_por_tipo_dia()
  - get_cbdmin_normativo()
  - compute_b_obs_por_hora()
  - compute_b_dist_por_hora()
  - compute_ifo_hora_y_franja()
  - compute_iccbdm_franja()
  - build_output()
  - main()