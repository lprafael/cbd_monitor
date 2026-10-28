from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import date, timedelta
from database.connection import DatabaseConnection, get_db_connection
from collections import defaultdict
from routes.monthly_performance import get_month_range, get_previous_month

router = APIRouter(prefix="/api/fines-report", tags=["Fines Report"])

class FinesReportRequest(BaseModel):
    month: int
    year: int
    evaluar_reincidencia: bool = True
    excluir_nivel_b: bool = False
    aplicar_non_bis_in_idem: bool = True
    considerar_todos_dias_ifo: bool = False

class FinesCumulativeRequest(BaseModel):
    start_month: int
    start_year: int
    end_month: int
    end_year: int
    evaluar_reincidencia: bool = True
    excluir_nivel_b: bool = False
    aplicar_non_bis_in_idem: bool = True
    excluir_arapoti: bool = True
    considerar_todos_dias_ifo: bool = False

def obtener_valor_jornal(fecha_eval: date) -> int:
    """
    Retorna el valor del jornal mínimo según la vigencia de la fecha.
    - Hasta el 30/06/2026: 111.502 Gs.
    - A partir del 01/07/2026: 117.077 Gs.
    """
    if fecha_eval >= date(2026, 7, 1):
        return 117077
    return 111502

def get_tipo_dia_id(fecha_obj, db_feriados):
    """5=LABORAL, 6=SABADO, 7=NO LABORAL"""
    dia_semana = fecha_obj.weekday()
    es_feriado = fecha_obj in db_feriados
    if es_feriado or dia_semana == 6:
        return 7
    elif dia_semana == 5:
        return 6
    else:
        return 5

def compute_fines_report_for_month(
    cursor,
    year: int,
    month: int,
    evaluar_reincidencia: bool = True,
    excluir_nivel_b: bool = False,
    aplicar_non_bis_in_idem: bool = True,
    considerar_todos_dias_ifo: bool = False
) -> dict:
    try:
        start_date, end_date = get_month_range(year, month)
        
        FECHA_INICIO_ETAPA2 = date(2026, 5, 19)
        
        # Si el mes solicitado es enteramente previo a la vigencia de la Etapa 2
        if end_date < FECHA_INICIO_ETAPA2:
            return {
                'month': month,
                'year': year,
                'reporte': []
            }

        # Ajustar start_date si es mayo de 2026
        if year == 2026 and month == 5:
            if start_date < FECHA_INICIO_ETAPA2:
                start_date = FECHA_INICIO_ETAPA2

        eval_start_date = start_date

        # 1. Obtener feriados
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (eval_start_date, end_date))
        db_feriados = set(row['fecha'] for row in cursor.fetchall())
        
        # 1.b Obtener días atípicos
        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (eval_start_date, end_date))
        atipicos_rows = cursor.fetchall()
        db_atipicos = set(row['fecha'] for row in atipicos_rows)
        cursor.execute("SELECT fecha, tipo_atipico FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (eval_start_date, end_date))
        atipicos_tipo_rows = cursor.fetchall()
        db_feriados.update(row['fecha'] for row in atipicos_tipo_rows if (row['tipo_atipico'] or '').upper().startswith('FERIADO'))
        db_lluvia_prepos = set(row['fecha'] for row in atipicos_tipo_rows if (row['tipo_atipico'] or '').upper() in ('LLUVIA', 'PRE_POS_FERIADO'))
        
        # 2. Obtener EOTs
        cursor.execute("SELECT cod_catalogo, eot_nombre, id_eot_vmt_hex FROM public.eots WHERE cod_catalogo NOT IN (72, 75) AND id_eot_vmt_hex != '004B' AND permisionario IS TRUE")
        eots = cursor.fetchall()
        eots_by_hex = {e['id_eot_vmt_hex']: e['eot_nombre'] for e in eots}
        
        # 3. Obtener franjas operativas y parámetros mínimos
        cursor.execute("""
            SELECT f.id_franja, f.id_tipo_dia, f.denominacion, 
                   p.cbd_minimo_franja
            FROM control_metricas.franjas_operativas f
            LEFT JOIN control_metricas.cbd_parametros_minimos p 
              ON f.id_franja = p.id_franja AND f.id_tipo_dia = p.id_tipo_dia
             AND (p.vigencia_desde IS NULL OR p.vigencia_desde <= %s)
             AND (p.vigencia_hasta IS NULL OR p.vigencia_hasta >= %s)
            WHERE (f.inicio_vigencia IS NULL OR f.inicio_vigencia <= %s)
              AND (f.fin_vigencia IS NULL OR f.fin_vigencia >= %s)
        """, (end_date, eval_start_date, end_date, eval_start_date))
        franjas_metadata = {}
        for row in cursor.fetchall():
            franjas_metadata[row['id_franja']] = {
                'id_tipo_dia': row['id_tipo_dia'],
                'denominacion': row['denominacion'],
                'cbd_minimo': row['cbd_minimo_franja']
            }
            
        def categorizar(nombre):
            nombre = (nombre or "").upper()
            if "PICO" in nombre and "POS" not in nombre: return "PICO"
            if "POS PICO" in nombre: return "POS_PICO"
            return "OTRO"
            
        # 4. Obtener todos los datos de IFO en la ventana de evaluación
        cursor.execute("""
            SELECT id_eot_vmt_hex, fecha, id_franja, ifo, cbd_indice
            FROM control_metricas.ifo_historico
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha, id_eot_vmt_hex, id_franja
        """, (eval_start_date, end_date))
        historico = cursor.fetchall()
        
        # Agrupar por EOT
        datos_por_eot = defaultdict(list)
        for row in historico:
            if row['id_eot_vmt_hex'] in eots_by_hex:
                datos_por_eot[row['id_eot_vmt_hex']].append(row)
        
        # 5. Calcular IFO Sistema (mes anterior) para Art 15.1
        prev_year, prev_month = get_previous_month(year, month)
        prev_start, prev_end = get_month_range(prev_year, prev_month)

        if aplicar_non_bis_in_idem:
            # Metodología Non bis in idem (Res. 104/2026 y 120/2025)
            # 5.a IFO Sistema General (mes anterior)
            where_sys_excl = ""
            if not considerar_todos_dias_ifo:
                where_sys_excl = """
                  AND EXTRACT(ISODOW FROM h.fecha) < 7
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                """
            cursor.execute(f"""
                SELECT AVG(eot_monthly_ifo_topeado) as system_ifo_topeado
                FROM (
                    SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as eot_monthly_ifo_topeado
                    FROM (
                        SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          {where_sys_excl}
                          AND (
                            (
                              EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5
                              AND (
                                UPPER(f.denominacion) LIKE '%%PICO%%'
                                OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%'
                                OR UPPER(f.denominacion) LIKE '%%POSPICO%%'
                              )
                              AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                            )
                            OR
                            (
                              EXTRACT(ISODOW FROM h.fecha) = 6
                              AND UPPER(f.denominacion) LIKE '%%PICO%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%POS%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                            )
                          )
                        GROUP BY h.id_eot_vmt_hex, h.fecha
                    ) daily_avgs
                    GROUP BY id_eot_vmt_hex
                ) eot_avgs
            """, (prev_start, prev_end))
            res_sys = cursor.fetchone()
            system_ifo_topeado_pct = float((res_sys['system_ifo_topeado'] or 0.0) * 100)
            if system_ifo_topeado_pct > 95: umbral_objetivo = 95.0
            elif system_ifo_topeado_pct < 90: umbral_objetivo = 90.0
            else: umbral_objetivo = system_ifo_topeado_pct

            # 5.b Histórico de los últimos 6 meses (para Reincidencias Art. 16.1, 16.2, 16.4 y Sumario Art. 18.2)
            eots_con_incumplimiento_15_1_previo = set()
            eots_con_incumplimiento_15_2_previo = set()
            eots_con_incumplimiento_15_4_previo = set()
            fallas_ifo_6meses = defaultdict(int)
            infracciones_previas_trimestre = defaultdict(int)

            check_y, check_m = prev_year, prev_month
            for month_idx in range(6):
                if check_y < 2026 or (check_y == 2026 and check_m < 5):
                    break
                m_start, m_end = get_month_range(check_y, check_m)
                if check_y == 2026 and check_m == 5:
                    m_start = max(m_start, FECHA_INICIO_ETAPA2)
                
                # Calcular umbral general del mes check
                prev_check_y, prev_check_m = get_previous_month(check_y, check_m)
                p_start, p_end = get_month_range(prev_check_y, prev_check_m)

                cursor.execute("""
                    SELECT AVG(eot_monthly_ifo_topeado) as sys_ifo
                    FROM (
                        SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as eot_monthly_ifo_topeado
                        FROM (
                            SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                            FROM control_metricas.ifo_historico h
                            JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                            WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                              AND EXTRACT(ISODOW FROM h.fecha) < 7
                              AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                              AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                              AND (
                                (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%') AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                                OR
                                (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%' AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                              )
                            GROUP BY h.id_eot_vmt_hex, h.fecha
                        ) daily_avgs
                        GROUP BY id_eot_vmt_hex
                    ) eot_avgs
                """, (p_start, p_end))
                p_sys = cursor.fetchone()
                p_sys_ifo = float((p_sys['sys_ifo'] or 0.0) * 100)
                m_umbral = 95.0 if p_sys_ifo > 95 else (90.0 if p_sys_ifo < 90 else p_sys_ifo)

                # Calcular IFO Mensual General por EOT (Regla 4 oficial: computa totalidad de jornadas evaluables)
                cursor.execute("""
                    SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as monthly_ifo_topeado
                    FROM (
                        SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND EXTRACT(ISODOW FROM h.fecha) < 7
                          AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                          AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                          AND (
                            (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%'))
                            OR
                            (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                          )
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                        GROUP BY h.id_eot_vmt_hex, h.fecha
                    ) daily_avgs
                    GROUP BY id_eot_vmt_hex
                """, (m_start, m_end))
                for row in cursor.fetchall():
                    m_ifo = float(row['monthly_ifo_topeado'] * 100)
                    if m_ifo < m_umbral:
                        if evaluar_reincidencia:
                            eots_con_incumplimiento_15_1_previo.add(row['id_eot_vmt_hex'])
                        fallas_ifo_6meses[row['id_eot_vmt_hex']] += 1
                        if month_idx < 2:
                            infracciones_previas_trimestre[row['id_eot_vmt_hex']] += 1

                # Reincidencias Nivel B: solo para EOTs que NO tuvieron Nivel C en ese mes
                cursor.execute("""
                    WITH dias_con_c AS (
                        SELECT DISTINCT h.id_eot_vmt_hex, h.fecha
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND (
                            (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%'))
                            OR
                            (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                          )
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                          AND h.ifo < 0.80
                    ),
                    eots_con_c AS (
                        SELECT DISTINCT id_eot_vmt_hex FROM dias_con_c
                    )
                    SELECT h.id_eot_vmt_hex,
                           SUM(CASE WHEN (
                               (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                               OR (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                           ) AND (h.ifo >= 0.80 AND h.ifo < 0.90) THEN 1 ELSE 0 END) as b_pico_count,
                           SUM(CASE WHEN (
                               EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%')
                           ) AND (h.ifo >= 0.80 AND h.ifo < 0.90) THEN 1 ELSE 0 END) as b_pospico_count
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                      AND EXTRACT(ISODOW FROM h.fecha) < 7
                      AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                      AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos WHERE tipo_atipico LIKE 'FERIADO%%')
                      AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                      AND h.id_eot_vmt_hex NOT IN (SELECT id_eot_vmt_hex FROM eots_con_c)
                    GROUP BY h.id_eot_vmt_hex
                """, (m_start, m_end, m_start, m_end))
                for row in cursor.fetchall():
                    pico_b = (row['b_pico_count'] or 0) >= 5
                    pos_b = (row['b_pospico_count'] or 0) >= 5
                    if pico_b and evaluar_reincidencia:
                        eots_con_incumplimiento_15_2_previo.add(row['id_eot_vmt_hex'])
                    if pos_b and evaluar_reincidencia:
                        eots_con_incumplimiento_15_4_previo.add(row['id_eot_vmt_hex'])
                    if (pico_b or pos_b) and month_idx < 2 and not excluir_nivel_b:
                        infracciones_previas_trimestre[row['id_eot_vmt_hex']] += 1

                if month_idx < 2:
                    # Conteo de días con Nivel C (máx 1 por día) o ICCBDM en los meses previos del trimestre
                    cursor.execute("""
                        SELECT h.id_eot_vmt_hex,
                               COUNT(DISTINCT CASE WHEN (
                                   (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%'))
                                   OR (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                               ) AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%' AND h.ifo < 0.80 THEN h.fecha END) as dias_c,
                               COUNT(DISTINCT CASE WHEN h.cbd_indice IS NOT NULL AND h.cbd_indice < 1.0 THEN h.fecha END) as dias_fail_cbd
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND EXTRACT(ISODOW FROM h.fecha) < 7
                          AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                          AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                        GROUP BY h.id_eot_vmt_hex
                    """, (m_start, m_end))
                    for row in cursor.fetchall():
                        infracciones_previas_trimestre[row['id_eot_vmt_hex']] += (
                            (row['dias_c'] or 0) + 
                            (row['dias_fail_cbd'] or 0)
                        )

                check_y, check_m = get_previous_month(check_y, check_m)
        else:
            # Metodología Estándar (Previa)
            where_std_sys_excl = ""
            if not considerar_todos_dias_ifo:
                where_std_sys_excl = """
                  AND EXTRACT(ISODOW FROM h.fecha) < 7
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                """
            cursor.execute(f"""
                SELECT AVG(eot_monthly_ifo_topeado) as system_ifo_topeado
                FROM (
                    SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as eot_monthly_ifo_topeado
                    FROM (
                        SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          {where_std_sys_excl}
                          AND (
                            (
                              EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5
                              AND (
                                UPPER(f.denominacion) LIKE '%%PICO%%'
                                OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%'
                                OR UPPER(f.denominacion) LIKE '%%POSPICO%%'
                              )
                              AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                            )
                            OR
                            (
                              EXTRACT(ISODOW FROM h.fecha) = 6
                              AND UPPER(f.denominacion) LIKE '%%PICO%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%POS%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                              AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                            )
                          )
                        GROUP BY h.id_eot_vmt_hex, h.fecha
                    ) daily_avgs
                    GROUP BY id_eot_vmt_hex
                ) eot_avgs
            """, (prev_start, prev_end))
            res_sys = cursor.fetchone()
            system_ifo_topeado_pct = float((res_sys['system_ifo_topeado'] or 0.0) * 100)
            
            if system_ifo_topeado_pct > 95: umbral_objetivo = 95.0
            elif system_ifo_topeado_pct < 90: umbral_objetivo = 90.0
            else: umbral_objetivo = system_ifo_topeado_pct
            
            # Calcular IFO mensual por EOT para el mes en curso (start_date a end_date)
            where_std_mes_excl = ""
            if not considerar_todos_dias_ifo:
                where_std_mes_excl = """
                  AND EXTRACT(ISODOW FROM h.fecha) < 7
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                """
            cursor.execute(f"""
                SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as monthly_ifo_topeado
                FROM (
                    SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                      {where_std_mes_excl}
                      AND (
                        (
                          EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5
                          AND (
                            UPPER(f.denominacion) LIKE '%%PICO%%'
                            OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%'
                            OR UPPER(f.denominacion) LIKE '%%POSPICO%%'
                          )
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                          AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                        )
                        OR
                        (
                          EXTRACT(ISODOW FROM h.fecha) = 6
                          AND UPPER(f.denominacion) LIKE '%%PICO%%'
                          AND UPPER(f.denominacion) NOT LIKE '%%POS%%'
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%'
                          AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                        )
                      )
                    GROUP BY h.id_eot_vmt_hex, h.fecha
                ) daily_avgs
                GROUP BY id_eot_vmt_hex
            """, (start_date, end_date))
            ifo_mensual_dict = {row['id_eot_vmt_hex']: float(row['monthly_ifo_topeado'] * 100) for row in cursor.fetchall()}

            eots_con_incumplimiento_15_1_previo = set()
            eots_con_incumplimiento_15_2_previo = set()
            eots_con_incumplimiento_15_4_previo = set()
            fallas_ifo_6meses = defaultdict(int)
            infracciones_previas_trimestre = defaultdict(int)

            check_y, check_m = prev_year, prev_month
            for month_idx in range(6):
                if check_y < 2026 or (check_y == 2026 and check_m < 5):
                    break
                m_start, m_end = get_month_range(check_y, check_m)
                if check_y == 2026 and check_m == 5:
                    m_start = max(m_start, FECHA_INICIO_ETAPA2)

                prev_check_y, prev_check_m = get_previous_month(check_y, check_m)
                p_start, p_end = get_month_range(prev_check_y, prev_check_m)

                cursor.execute("""
                    SELECT AVG(eot_monthly_ifo_topeado) as system_ifo_topeado
                    FROM (
                        SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as eot_monthly_ifo_topeado
                        FROM (
                            SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                            FROM control_metricas.ifo_historico h
                            JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                            WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                              AND EXTRACT(ISODOW FROM h.fecha) < 7
                              AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                              AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                              AND (
                                (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%') AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                                OR
                                (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%' AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                              )
                            GROUP BY h.id_eot_vmt_hex, h.fecha
                        ) daily_avgs
                        GROUP BY id_eot_vmt_hex
                    ) eot_avgs
                """, (p_start, p_end))
                p_sys = cursor.fetchone()
                p_sys_pct = float((p_sys['system_ifo_topeado'] or 0.0) * 100)
                m_umbral = 95.0 if p_sys_pct > 95 else (90.0 if p_sys_pct < 90 else p_sys_pct)

                cursor.execute("""
                    SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as monthly_ifo_topeado
                    FROM (
                        SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND EXTRACT(ISODOW FROM h.fecha) < 7
                          AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                          AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                          AND (
                            (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%') AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                            OR
                            (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%' AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%')
                          )
                        GROUP BY h.id_eot_vmt_hex, h.fecha
                    ) daily_avgs
                    GROUP BY id_eot_vmt_hex
                """, (m_start, m_end))
                for row in cursor.fetchall():
                    m_ifo = float(row['monthly_ifo_topeado'] * 100)
                    if m_ifo < m_umbral:
                        if evaluar_reincidencia:
                            eots_con_incumplimiento_15_1_previo.add(row['id_eot_vmt_hex'])
                        fallas_ifo_6meses[row['id_eot_vmt_hex']] += 1
                        if month_idx < 2:
                            infracciones_previas_trimestre[row['id_eot_vmt_hex']] += 1

                cursor.execute("""
                    WITH dias_c_pico AS (
                        SELECT DISTINCT h.id_eot_vmt_hex, h.fecha
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND (
                            (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                            OR (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                          )
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                          AND h.ifo < 0.80
                    ),
                    dias_c_pos AS (
                        SELECT DISTINCT h.id_eot_vmt_hex, h.fecha
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5
                          AND (UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%')
                          AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                          AND h.ifo < 0.80
                    )
                    SELECT h.id_eot_vmt_hex,
                           SUM(CASE WHEN (
                               (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                               OR (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                           ) AND (h.ifo >= 0.80 AND h.ifo < 0.90) 
                             AND (h.id_eot_vmt_hex, h.fecha) NOT IN (SELECT id_eot_vmt_hex, fecha FROM dias_c_pico) THEN 1 ELSE 0 END) as b_pico_count,
                           SUM(CASE WHEN (
                               EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%')
                           ) AND (h.ifo >= 0.80 AND h.ifo < 0.90) 
                             AND (h.id_eot_vmt_hex, h.fecha) NOT IN (SELECT id_eot_vmt_hex, fecha FROM dias_c_pos) THEN 1 ELSE 0 END) as b_pospico_count
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                      AND EXTRACT(ISODOW FROM h.fecha) < 7
                      AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                      AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos WHERE tipo_atipico LIKE 'FERIADO%%')
                      AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%'
                    GROUP BY h.id_eot_vmt_hex
                """, (m_start, m_end, m_start, m_end, m_start, m_end))
                for row in cursor.fetchall():
                    if (row['b_pico_count'] or 0) >= 5:
                        if evaluar_reincidencia:
                            eots_con_incumplimiento_15_2_previo.add(row['id_eot_vmt_hex'])
                        if month_idx < 2 and not excluir_nivel_b:
                            infracciones_previas_trimestre[row['id_eot_vmt_hex']] += 1
                    if (row['b_pospico_count'] or 0) >= 5:
                        if evaluar_reincidencia:
                            eots_con_incumplimiento_15_4_previo.add(row['id_eot_vmt_hex'])
                        if month_idx < 2 and not excluir_nivel_b:
                            infracciones_previas_trimestre[row['id_eot_vmt_hex']] += 1

                if month_idx < 2:
                    cursor.execute("""
                        SELECT h.id_eot_vmt_hex,
                               COUNT(DISTINCT CASE WHEN (
                                   (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%'))
                                   OR (EXTRACT(ISODOW FROM h.fecha) = 6 AND UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%')
                               ) AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%' AND h.ifo < 0.80 THEN (h.fecha, CASE WHEN UPPER(f.denominacion) LIKE '%%POS%%' THEN 'POS' ELSE 'PICO' END) END) as infracciones_c,
                               COUNT(DISTINCT CASE WHEN h.cbd_indice IS NOT NULL AND h.cbd_indice < 1.0 THEN h.fecha END) as dias_fail_cbd
                        FROM control_metricas.ifo_historico h
                        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                        WHERE h.fecha BETWEEN %s AND %s AND h.id_eot_vmt_hex != '004B'
                          AND EXTRACT(ISODOW FROM h.fecha) < 7
                          AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                          AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                        GROUP BY h.id_eot_vmt_hex
                    """, (m_start, m_end))
                    for row in cursor.fetchall():
                        infracciones_previas_trimestre[row['id_eot_vmt_hex']] += (
                            (row['infracciones_c'] or 0) + 
                            (row['dias_fail_cbd'] or 0)
                        )

                check_y, check_m = get_previous_month(check_y, check_m)

        reporte_final = []
        
        # 6. Evaluar infracciones para cada EOT
        for eot_hex, eot_nombre in eots_by_hex.items():
            historial_faltas = []
            
            # Agrupar datos diarios para Art 15.2 - 15.6 y sus reincidencias
            dias_data = defaultdict(dict)
            for r in datos_por_eot[eot_hex]:
                dias_data[r['fecha']][r['id_franja']] = r
                
            fechas_ordenadas = sorted(dias_data.keys())

            if not aplicar_non_bis_in_idem:
                # -------------------------------------------------------------
                # METODOLOGÍA ESTÁNDAR PREVIA
                # -------------------------------------------------------------
                ifo_mensual_eot = ifo_mensual_dict.get(eot_hex, 0.0)
                if ifo_mensual_eot > 0 and ifo_mensual_eot < umbral_objetivo:
                    if eot_hex in eots_con_incumplimiento_15_1_previo:
                        historial_faltas.append({
                            'fecha': end_date,
                            'base': 'Art. 16.1',
                            'desc': f'Reincidencia IFO Mensual ({ifo_mensual_eot:.2f}%) en últimos 6 meses - 30% recargo',
                            'jornales': round(173 * 1.3, 1)
                        })
                    else:
                        historial_faltas.append({
                            'fecha': end_date,
                            'base': 'Art. 15.1',
                            'desc': f'IFO Mensual ({ifo_mensual_eot:.2f}%) inferior al Umbral ({umbral_objetivo:.2f}%)',
                            'jornales': 173
                        })
                    fallas_ifo_6meses[eot_hex] += 1

                acum_b = {'PICO': 0, 'POS_PICO': 0}
                trigger_15_2 = False
                trigger_15_4 = False

                for fecha_eval in fechas_ordenadas:
                    if fecha_eval < FECHA_INICIO_ETAPA2: continue
                    id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                    if id_tipo_dia == 7: continue

                    franjas_dia = dias_data[fecha_eval]
                    fail_15_3, fail_15_5, fail_15_6 = False, False, False
                    b_pico_dia = 0
                    b_pospico_dia = 0

                    for fid, f_res in franjas_dia.items():
                        meta = franjas_metadata.get(fid, {})
                        cat = categorizar(meta.get('denominacion', ''))
                        if cat == "OTRO" or f_res['ifo'] is None: continue
                        if id_tipo_dia == 6 and cat == 'POS_PICO': continue

                        ifo_val = float(f_res['ifo']) * 100
                        cbd_idx = float(f_res['cbd_indice']) if f_res['cbd_indice'] is not None else 1.0

                        if cbd_idx < 1.0 and fecha_eval not in db_lluvia_prepos: fail_15_6 = True
                        if cat == 'PICO':
                            if ifo_val < 80: fail_15_3 = True
                            elif ifo_val < 90: b_pico_dia += 1
                        elif cat == 'POS_PICO':
                            if ifo_val < 80: fail_15_5 = True
                            elif ifo_val < 90: b_pospico_dia += 1

                    if fail_15_6 and fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM (Buses Mínimos)', 'jornales': 20})
                    if fail_15_3 and fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
                    if fail_15_5 and fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})

                    if not fail_15_3 and not trigger_15_2:
                        acum_b['PICO'] += b_pico_dia
                    if not fail_15_5 and not trigger_15_4:
                        acum_b['POS_PICO'] += b_pospico_dia

                    if not excluir_nivel_b:
                        if not trigger_15_2 and acum_b['PICO'] >= 5:
                            trigger_15_2 = True
                            if fecha_eval >= start_date:
                                if eot_hex in eots_con_incumplimiento_15_2_previo:
                                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.2', 'desc': 'Reincidencia Nivel B Pico en últimos 6 meses (5 franjas acumuladas)', 'jornales': 20})
                                else:
                                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.2', 'desc': 'Acumulación 5 Franjas Pico Nivel B', 'jornales': 10})

                        if not trigger_15_4 and acum_b['POS_PICO'] >= 5:
                            trigger_15_4 = True
                            if fecha_eval >= start_date:
                                if eot_hex in eots_con_incumplimiento_15_4_previo:
                                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.4', 'desc': 'Reincidencia Nivel B Pos Pico en últimos 6 meses (5 franjas acumuladas)', 'jornales': 20})
                                else:
                                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.4', 'desc': 'Acumulación 5 Franjas Pos Pico Nivel B', 'jornales': 10})
            else:
                # -------------------------------------------------------------
                # METODOLOGÍA NON BIS IN IDEM (NON BIS IN QUO - RES. 120/2025)
                # -------------------------------------------------------------
                dias_sancionados_c = set()
                dias_con_b_pico = defaultdict(int)
                dias_con_b_pos = defaultdict(int)

                for fecha_eval in fechas_ordenadas:
                    if fecha_eval < FECHA_INICIO_ETAPA2:
                        continue

                    id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                    if id_tipo_dia == 7: continue # Descartar Domingos y Feriados
                    # Res. GVMT N° 104/2026: Lluvia, Pre/Pos Feriado y Eventos Disruptivos SÍ se evalúan con su factor de exigencia reducido (ya aplicado en ifo_historico)
                    
                    franjas_dia = dias_data[fecha_eval]
                    
                    fail_15_3, fail_15_5, fail_15_6 = False, False, False
                    b_pico_dia = 0
                    b_pospico_dia = 0
                    
                    for fid, f_res in franjas_dia.items():
                        meta = franjas_metadata.get(fid, {})
                        cat = categorizar(meta.get('denominacion', ''))
                        if cat == "OTRO" or f_res['ifo'] is None: continue
                        
                        # Etapa 2: Excluir Pos Pico de Sábado del cálculo de multas
                        if id_tipo_dia == 6 and cat == 'POS_PICO':
                            continue
                        
                        ifo_val = float(f_res['ifo']) * 100
                        cbd_idx = float(f_res['cbd_indice']) if f_res['cbd_indice'] is not None else 1.0
                        
                        if cbd_idx < 1.0 and fecha_eval not in db_lluvia_prepos: fail_15_6 = True
                        
                        if cat == 'PICO':
                            if ifo_val < 80: fail_15_3 = True
                            elif ifo_val < 90:
                                b_pico_dia += 1
                        elif cat == 'POS_PICO':
                            if ifo_val < 80: fail_15_5 = True
                            elif ifo_val < 90:
                                b_pospico_dia += 1
                                    
                    # 1. ICCBDM (15.6) - Multa base ordinaria diaria (autónomo e independiente)
                    if fail_15_6 and fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM (Buses Mínimos)', 'jornales': 20})
                            
                    # 2. NIVEL C DIARIO (Regla #1: se aplica una sola sanción de 20 jornales por día)
                    if fail_15_3 and fail_15_5:
                        dias_sancionados_c.add(fecha_eval)
                        if fecha_eval >= start_date:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3 / 15.5', 'desc': 'Nivel C en Franjas Pico y Pos Pico', 'jornales': 20})
                    elif fail_15_3:
                        dias_sancionados_c.add(fecha_eval)
                        if fecha_eval >= start_date:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
                    elif fail_15_5:
                        dias_sancionados_c.add(fecha_eval)
                        if fecha_eval >= start_date:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})
                    else:
                        # Si no hubo Nivel C hoy, registramos las franjas Nivel B
                        if b_pico_dia > 0:
                            dias_con_b_pico[fecha_eval] = b_pico_dia
                        if b_pospico_dia > 0:
                            dias_con_b_pos[fecha_eval] = b_pospico_dia

                # REGLAS #2 y #3: Exclusión mensual de Nivel B ante presencia de al menos un Nivel C en el mes
                hubo_c_en_mes = len(dias_sancionados_c) > 0
                dias_sancionados_b = set()

                if not hubo_c_en_mes and not excluir_nivel_b:
                    total_b_pico = sum(dias_con_b_pico.values())
                    total_b_pos = sum(dias_con_b_pos.values())
                    fail_b_pico = total_b_pico >= 5
                    fail_b_pos = total_b_pos >= 5

                    # Si incumple 15.2 y 15.4, se aplica una sola multa mensual (no 2)
                    if fail_b_pico and fail_b_pos:
                        dias_sancionados_b.update(dias_con_b_pico.keys())
                        dias_sancionados_b.update(dias_con_b_pos.keys())
                        is_reinc = (eot_hex in eots_con_incumplimiento_15_2_previo or eot_hex in eots_con_incumplimiento_15_4_previo)
                        base_b = 'Art. 16.2 / 16.4' if is_reinc else 'Art. 15.2 / 15.4'
                        jornales_b = 20 if is_reinc else 10
                        desc_b = f'Reincidencia Nivel B en Franjas Pico ({total_b_pico}) y Pos Pico ({total_b_pos}) en últimos 6 meses' if is_reinc else f'Acumulación Nivel B en Franjas Pico ({total_b_pico}) y Pos Pico ({total_b_pos})'
                        historial_faltas.append({
                            'fecha': end_date,
                            'base': base_b,
                            'desc': desc_b,
                            'jornales': jornales_b
                        })
                    elif fail_b_pico:
                        dias_sancionados_b.update(dias_con_b_pico.keys())
                        base_b_pico = 'Art. 16.2' if eot_hex in eots_con_incumplimiento_15_2_previo else 'Art. 15.2'
                        jornales_b_pico = 20 if eot_hex in eots_con_incumplimiento_15_2_previo else 10
                        desc_b_pico = f'Reincidencia Nivel B Pico en últimos 6 meses ({total_b_pico} franjas acumuladas)' if eot_hex in eots_con_incumplimiento_15_2_previo else f'Acumulación {total_b_pico} Franjas Pico Nivel B'
                        historial_faltas.append({
                            'fecha': end_date,
                            'base': base_b_pico,
                            'desc': desc_b_pico,
                            'jornales': jornales_b_pico
                        })
                    elif fail_b_pos:
                        dias_sancionados_b.update(dias_con_b_pos.keys())
                        base_b_pos = 'Art. 16.4' if eot_hex in eots_con_incumplimiento_15_4_previo else 'Art. 15.4'
                        jornales_b_pos = 20 if eot_hex in eots_con_incumplimiento_15_4_previo else 10
                        desc_b_pos = f'Reincidencia Nivel B Pos Pico en últimos 6 meses ({total_b_pos} franjas acumuladas)' if eot_hex in eots_con_incumplimiento_15_4_previo else f'Acumulación {total_b_pos} Franjas Pos Pico Nivel B'
                        historial_faltas.append({
                            'fecha': end_date,
                            'base': base_b_pos,
                            'desc': desc_b_pos,
                            'jornales': jornales_b_pos
                        })

                # REGLA #4 (Res. GVMT N° 104/2026 oficial): IFO Mensual General (Art. 15.1).
                # Se computa la totalidad de las jornadas diarias evaluables del mes calendario,
                # con exclusión de feriados y días atípicos, con independencia de que dichas jornadas
                # hubieren sido objeto de sanciones previas (Nivel B o Nivel C).

                daily_ifo_mensual = []
                
                for fecha_eval in fechas_ordenadas:
                    if fecha_eval < start_date or fecha_eval > end_date: continue
                    if fecha_eval < FECHA_INICIO_ETAPA2: continue
                    id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                    if not considerar_todos_dias_ifo:
                        if id_tipo_dia == 7 or fecha_eval in db_atipicos: continue
                    
                    franjas_dia = dias_data[fecha_eval]
                    franja_vals = []
                    for fid, f_res in franjas_dia.items():
                        meta = franjas_metadata.get(fid, {})
                        cat = categorizar(meta.get('denominacion', ''))
                        if f_res['ifo'] is None or cat == 'OTRO': continue
                        if id_tipo_dia == 6 and cat == 'POS_PICO': continue # Excluir Pos Pico de Sábado
                        franja_vals.append(float(f_res['ifo']))
                    
                    if franja_vals:
                        daily_ifo_mensual.append(min(sum(franja_vals) / len(franja_vals), 1.1))

                if daily_ifo_mensual:
                    ifo_mensual_eot = (sum(daily_ifo_mensual) / len(daily_ifo_mensual)) * 100
                    if ifo_mensual_eot < umbral_objetivo:
                        if eot_hex in eots_con_incumplimiento_15_1_previo:
                            historial_faltas.append({
                                'fecha': end_date,
                                'base': 'Art. 16.1',
                                'desc': f'Reincidencia IFO Mensual ({ifo_mensual_eot:.2f}%) en últimos 6 meses - 30% recargo',
                                'jornales': round(173 * 1.3, 1)
                            })
                        else:
                            historial_faltas.append({
                                'fecha': end_date,
                                'base': 'Art. 15.1',
                                'desc': f'IFO Mensual ({ifo_mensual_eot:.2f}%) inferior al Umbral ({umbral_objetivo:.2f}%)',
                                'jornales': 173
                            })
                        fallas_ifo_6meses[eot_hex] += 1
                            
            if historial_faltas:
                # Calcular totales
                total_jornales = sum(f['jornales'] for f in historial_faltas)
                total_guaranies = sum(int(round(f['jornales'] * obtener_valor_jornal(f['fecha']))) for f in historial_faltas)
                
                # Evaluación de Causales de Sumario Administrativo (Art. 18.2)
                alertas_sumario = []
                if fallas_ifo_6meses[eot_hex] >= 3:
                    alertas_sumario.append(f"Causal de Sumario: Acumulación de {fallas_ifo_6meses[eot_hex]} fallas de IFO (<80% o bajo umbral) en 6 meses (Art. 18.2)")
                
                total_infracciones_trimestre = len(historial_faltas) + infracciones_previas_trimestre[eot_hex]
                if total_infracciones_trimestre >= 20:
                    alertas_sumario.append(f"Causal de Sumario: Acumulación de {total_infracciones_trimestre} infracciones en el trimestre (Art. 18.2)")

                reporte_final.append({
                    'eot_nombre': eot_nombre,
                    'eot_hex': eot_hex,
                    'total_jornales': total_jornales,
                    'total_guaranies': total_guaranies,
                    'total_infracciones': len(historial_faltas),
                    'total_infracciones_trimestre': total_infracciones_trimestre,
                    'alerta_sumario': len(alertas_sumario) > 0,
                    'motivos_sumario': alertas_sumario,
                    'infracciones': [
                        {
                            'fecha': f['fecha'].strftime('%Y-%m-%d'),
                            'base': f['base'],
                            'desc': f['desc'],
                            'jornales': f['jornales'],
                            'monto': int(round(f['jornales'] * obtener_valor_jornal(f['fecha'])))
                        } for f in historial_faltas
                    ]
                })
                
        # Sort by company name
        reporte_final.sort(key=lambda x: x['eot_nombre'])
        
        return {
            'month': month,
            'year': year,
            'aplicar_non_bis_in_idem': aplicar_non_bis_in_idem,
            'considerar_todos_dias_ifo': considerar_todos_dias_ifo,
            'reporte': reporte_final
        }
    except Exception as e:
        print(f"Error computing fines for {year}-{month}: {e}")
        raise

@router.post("")
async def generate_fines_report(
    request: FinesReportRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        return compute_fines_report_for_month(
            cursor=cursor,
            year=request.year,
            month=request.month,
            evaluar_reincidencia=request.evaluar_reincidencia,
            excluir_nivel_b=request.excluir_nivel_b,
            aplicar_non_bis_in_idem=request.aplicar_non_bis_in_idem,
            considerar_todos_dias_ifo=request.considerar_todos_dias_ifo
        )
    except Exception as e:
        print(f"Error generating fines report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@router.post("/cumulative")
async def generate_cumulative_fines_report(
    request: FinesCumulativeRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        # Generar lista de (year, month) desde (start_year, start_month) hasta (end_year, end_month)
        months_to_eval = []
        curr_y, curr_m = request.start_year, request.start_month
        end_y, end_m = request.end_year, request.end_month
        
        while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
            months_to_eval.append((curr_y, curr_m))
            if curr_m == 12:
                curr_y += 1
                curr_m = 1
            else:
                curr_m += 1

        MESES_NOMBRES = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Setiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        meses_resumen = []
        empresas_acum = {}

        for y, m in months_to_eval:
            month_data = compute_fines_report_for_month(
                cursor, y, m,
                request.evaluar_reincidencia,
                request.excluir_nivel_b,
                request.aplicar_non_bis_in_idem,
                request.considerar_todos_dias_ifo
            )
            rep = month_data.get('reporte', [])
            
            m_jornales = sum(e['total_jornales'] for e in rep)
            m_monto = sum(e['total_guaranies'] for e in rep)
            m_empresas = len(rep)
            
            m_label = f"{MESES_NOMBRES.get(m, str(m))} {y}"
            m_key = f"{y}-{m:02d}"

            meses_resumen.append({
                'year': y,
                'month': m,
                'key': m_key,
                'label': m_label,
                'total_jornales': m_jornales,
                'total_guaranies': m_monto,
                'empresas_sancionadas': m_empresas
            })

            for emp in rep:
                hex_id = emp['eot_hex']
                if hex_id not in empresas_acum:
                    empresas_acum[hex_id] = {
                        'eot_nombre': emp['eot_nombre'],
                        'eot_hex': hex_id,
                        'total_jornales': 0,
                        'total_guaranies': 0,
                        'total_infracciones': 0,
                        'meses': {},
                        'por_articulo': defaultdict(lambda: {'jornales': 0, 'monto': 0, 'conteo': 0}),
                        'alerta_sumario': False,
                        'motivos_sumario': [],
                        'infracciones': []
                    }
                
                e_entry = empresas_acum[hex_id]
                e_entry['total_jornales'] += emp['total_jornales']
                e_entry['total_guaranies'] += emp['total_guaranies']
                e_entry['total_infracciones'] += emp['total_infracciones']
                
                if emp.get('alerta_sumario'):
                    e_entry['alerta_sumario'] = True
                    for mot in emp.get('motivos_sumario', []):
                        if mot not in e_entry['motivos_sumario']:
                            e_entry['motivos_sumario'].append(mot)
                
                e_entry['meses'][m_key] = {
                    'jornales': emp['total_jornales'],
                    'monto': emp['total_guaranies'],
                    'infracciones': emp['total_infracciones']
                }

                for inf in emp.get('infracciones', []):
                    e_entry['infracciones'].append({
                        **inf,
                        'mes': m_key,
                        'mes_label': m_label
                    })
                    base = inf.get('base', 'Otros')
                    e_entry['por_articulo'][base]['jornales'] += inf.get('jornales', 0)
                    e_entry['por_articulo'][base]['monto'] += inf.get('monto', 0)
                    e_entry['por_articulo'][base]['conteo'] += 1

        lista_empresas = list(empresas_acum.values())
        for e in lista_empresas:
            e['por_articulo'] = dict(e['por_articulo'])
            for mr in meses_resumen:
                mk = mr['key']
                if mk not in e['meses']:
                    e['meses'][mk] = {'jornales': 0, 'monto': 0, 'infracciones': 0}

        lista_empresas.sort(key=lambda x: x['total_jornales'], reverse=True)

        gran_total_jornales = sum(e['total_jornales'] for e in lista_empresas)
        gran_total_guaranies = sum(e['total_guaranies'] for e in lista_empresas)
        gran_total_infracciones = sum(e['total_infracciones'] for e in lista_empresas)

        articulos_global = defaultdict(lambda: {'jornales': 0, 'monto': 0, 'conteo': 0})
        for e in lista_empresas:
            for art, vals in e['por_articulo'].items():
                articulos_global[art]['jornales'] += vals['jornales']
                articulos_global[art]['monto'] += vals['monto']
                articulos_global[art]['conteo'] += vals['conteo']

        return {
            'periodo': {
                'start_year': request.start_year,
                'start_month': request.start_month,
                'end_year': request.end_year,
                'end_month': request.end_month,
                'total_meses': len(meses_resumen)
            },
            'meses': meses_resumen,
            'totales_generales': {
                'total_jornales': gran_total_jornales,
                'total_guaranies': gran_total_guaranies,
                'total_infracciones': gran_total_infracciones,
                'empresas_sancionadas': len(lista_empresas),
                'empresas_sumario': sum(1 for e in lista_empresas if e['alerta_sumario']),
                'por_articulo': dict(articulos_global),
                'top_empresas': [
                    {
                        'eot_nombre': e['eot_nombre'],
                        'eot_hex': e['eot_hex'],
                        'total_jornales': e['total_jornales'],
                        'total_guaranies': e['total_guaranies']
                    }
                    for e in lista_empresas[:10]
                ]
            },
            'empresas': lista_empresas
        }
        
    except Exception as e:
        print(f"Error generating cumulative fines report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

