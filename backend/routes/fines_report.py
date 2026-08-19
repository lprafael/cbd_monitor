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

VALOR_JORNAL = 111502

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

@router.post("")
async def generate_fines_report(
    request: FinesReportRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        month = request.month
        year = request.year
        
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

        # Ventana de evaluación extendida hacia atrás hasta 7 días para capturar reincidencias que crucen meses
        eval_start_date = max(FECHA_INICIO_ETAPA2, start_date - timedelta(days=7))

        # 1. Obtener feriados
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (eval_start_date, end_date))
        db_feriados = set(row['fecha'] for row in cursor.fetchall())
        
        # 1.b Obtener días atípicos
        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (eval_start_date, end_date))
        db_atipicos = set(row['fecha'] for row in cursor.fetchall())
        
        # 2. Obtener EOTs
        cursor.execute("SELECT cod_catalogo, eot_nombre, id_eot_vmt_hex FROM public.eots WHERE cod_catalogo NOT IN (72) AND permisionario IS TRUE")
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
        cursor.execute("""
            SELECT AVG(eot_monthly_ifo_topeado) as system_ifo_topeado
            FROM (
                SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as eot_monthly_ifo_topeado
                FROM (
                    SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s
                      AND EXTRACT(ISODOW FROM h.fecha) < 7
                      AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                      AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
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
        cursor.execute("""
            SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as monthly_ifo_topeado
            FROM (
                SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                FROM control_metricas.ifo_historico h
                JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                WHERE h.fecha BETWEEN %s AND %s
                  AND EXTRACT(ISODOW FROM h.fecha) < 7
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
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
        
        # 5.b Histórico de los últimos 6 meses (para Reincidencias Art. 16.1, 16.2, 16.4 y Sumario Art. 18.2)
        eots_con_incumplimiento_15_1_previo = set()
        eots_con_incumplimiento_15_2_previo = set()
        eots_con_incumplimiento_15_4_previo = set()
        fallas_ifo_6meses = defaultdict(int)

        check_y, check_m = prev_year, prev_month
        for _ in range(6):
            if check_y < 2026 or (check_y == 2026 and check_m < 5):
                break
            m_start, m_end = get_month_range(check_y, check_m)
            if check_y == 2026 and check_m == 5:
                m_start = max(m_start, FECHA_INICIO_ETAPA2)
            
            # Calcular umbral del mes check
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
                        WHERE h.fecha BETWEEN %s AND %s
                          AND EXTRACT(ISODOW FROM h.fecha) < 7
                          AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                          AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
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
            """, (p_start, p_end))
            p_sys = cursor.fetchone()
            p_sys_ifo = float((p_sys['system_ifo_topeado'] or 0.0) * 100)
            if p_sys_ifo > 95: m_umbral = 95.0
            elif p_sys_ifo < 90: m_umbral = 90.0
            else: m_umbral = p_sys_ifo

            # IFO mensual de las EOTs en el mes check
            cursor.execute("""
                SELECT id_eot_vmt_hex, AVG(daily_ifo_topeado) as monthly_ifo_topeado
                FROM (
                    SELECT h.id_eot_vmt_hex, h.fecha, LEAST(AVG(h.ifo), 1.1) as daily_ifo_topeado
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s
                      AND EXTRACT(ISODOW FROM h.fecha) < 7
                      AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                      AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
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
            """, (m_start, m_end))
            for row in cursor.fetchall():
                eot_ifo = float(row['monthly_ifo_topeado'] * 100)
                if 0 < eot_ifo < m_umbral:
                    eots_con_incumplimiento_15_1_previo.add(row['id_eot_vmt_hex'])
                    fallas_ifo_6meses[row['id_eot_vmt_hex']] += 1

            # Conteo de franjas Nivel B (Pico y Pos Pico) en el mes check
            cursor.execute("""
                SELECT h.id_eot_vmt_hex,
                       SUM(CASE WHEN (UPPER(f.denominacion) LIKE '%%PICO%%' AND UPPER(f.denominacion) NOT LIKE '%%POS%%' AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%') AND (h.ifo >= 0.80 AND h.ifo < 0.90) THEN 1 ELSE 0 END) as b_pico_count,
                       SUM(CASE WHEN (EXTRACT(ISODOW FROM h.fecha) BETWEEN 1 AND 5 AND (UPPER(f.denominacion) LIKE '%%POS%%PICO%%' OR UPPER(f.denominacion) LIKE '%%POSPICO%%') AND UPPER(f.denominacion) NOT LIKE '%%MADRUGADA%%' AND UPPER(f.denominacion) NOT LIKE '%%NOCTURN%%') AND (h.ifo >= 0.80 AND h.ifo < 0.90) THEN 1 ELSE 0 END) as b_pospico_count
                FROM control_metricas.ifo_historico h
                JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                WHERE h.fecha BETWEEN %s AND %s
                  AND EXTRACT(ISODOW FROM h.fecha) < 7
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND h.fecha NOT IN (SELECT fecha FROM control_metricas.dias_atipicos)
                GROUP BY h.id_eot_vmt_hex
            """, (m_start, m_end))
            for row in cursor.fetchall():
                if (row['b_pico_count'] or 0) >= 5:
                    eots_con_incumplimiento_15_2_previo.add(row['id_eot_vmt_hex'])
                if (row['b_pospico_count'] or 0) >= 5:
                    eots_con_incumplimiento_15_4_previo.add(row['id_eot_vmt_hex'])

            check_y, check_m = get_previous_month(check_y, check_m)

        reporte_final = []
        
        # 6. Evaluar infracciones para cada EOT
        for eot_hex, eot_nombre in eots_by_hex.items():
            historial_faltas = []
            
            # Art 15.1 / 16.1 - IFO Mensual
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
                
            # Agrupar datos diarios para Art 15.2 - 15.6 y sus reincidencias
            dias_data = defaultdict(dict)
            for r in datos_por_eot[eot_hex]:
                dias_data[r['fecha']][r['id_franja']] = r
                
            acum_b = {'PICO': 0, 'POS_PICO': 0}
            trigger_15_2 = False
            trigger_15_4 = False

            fechas_ordenadas = sorted(dias_data.keys())
            for fecha_eval in fechas_ordenadas:
                if fecha_eval < FECHA_INICIO_ETAPA2:
                    continue

                id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                if id_tipo_dia == 7: continue # Descartar Domingos y Feriados
                if fecha_eval in db_atipicos: continue # Descartar Días Atípicos (Lluvia, etc.)
                
                franjas_dia = dias_data[fecha_eval]
                
                fail_15_3, fail_15_5, fail_15_6 = False, False, False
                
                for fid, f_res in franjas_dia.items():
                    meta = franjas_metadata.get(fid, {})
                    cat = categorizar(meta.get('denominacion', ''))
                    if cat == "OTRO" or f_res['ifo'] is None: continue
                    
                    # Etapa 2: Excluir Pos Pico de Sábado del cálculo de multas
                    if id_tipo_dia == 6 and cat == 'POS_PICO':
                        continue
                    
                    ifo_val = float(f_res['ifo']) * 100
                    cbd_idx = float(f_res['cbd_indice']) if f_res['cbd_indice'] is not None else 0.0
                    
                    if cbd_idx < 1.0: fail_15_6 = True
                    
                    if cat == 'PICO':
                        if ifo_val < 80: fail_15_3 = True
                        elif ifo_val < 90:
                            if not trigger_15_2:
                                acum_b['PICO'] += 1
                    elif cat == 'POS_PICO':
                        if ifo_val < 80: fail_15_5 = True
                        elif ifo_val < 90:
                            if not trigger_15_4:
                                acum_b['POS_PICO'] += 1
                                
                # EVALUACIÓN DE REGLAS (Bajo Res. 21/2026 Nivel C e ICCBDM no tienen agravante pecuniario de reincidencia)
                # 1. ICCBDM (15.6) - Multa base ordinaria diaria
                if fail_15_6:
                    if fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM (Buses Mínimos)', 'jornales': 20})
                            
                # 2. NIVEL C PICO (15.3) - Multa base ordinaria diaria
                if fail_15_3:
                    if fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
                            
                # 3. NIVEL C POS PICO (15.5) - Multa base ordinaria diaria
                if fail_15_5:
                    if fecha_eval >= start_date:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})

                # 4. ACUMULACIÓN NIVEL B (15.2 / 16.2 y 15.4 / 16.4 - Reincidencia lookback 6 meses)
                if not trigger_15_2 and acum_b['PICO'] >= 5:
                    trigger_15_2 = True
                    if fecha_eval >= start_date:
                        if eot_hex in eots_con_incumplimiento_15_2_previo:
                            historial_faltas.append({
                                'fecha': fecha_eval, 
                                'base': 'Art. 16.2', 
                                'desc': 'Reincidencia Nivel B Pico en últimos 6 meses (5 franjas acumuladas)', 
                                'jornales': 20
                            })
                        else:
                            historial_faltas.append({
                                'fecha': fecha_eval, 
                                'base': 'Art. 15.2', 
                                'desc': 'Acumulación 5 Franjas Pico Nivel B', 
                                'jornales': 10
                            })

                if not trigger_15_4 and acum_b['POS_PICO'] >= 5:
                    trigger_15_4 = True
                    if fecha_eval >= start_date:
                        if eot_hex in eots_con_incumplimiento_15_4_previo:
                            historial_faltas.append({
                                'fecha': fecha_eval, 
                                'base': 'Art. 16.4', 
                                'desc': 'Reincidencia Nivel B Pos Pico en últimos 6 meses (5 franjas acumuladas)', 
                                'jornales': 20
                            })
                        else:
                            historial_faltas.append({
                                'fecha': fecha_eval, 
                                'base': 'Art. 15.4', 
                                'desc': 'Acumulación 5 Franjas Pos Pico Nivel B', 
                                'jornales': 10
                            })
                            
            if historial_faltas:
                # Calcular totales
                total_jornales = sum(f['jornales'] for f in historial_faltas)
                total_guaranies = int(round(total_jornales * VALOR_JORNAL))
                
                # Evaluación de Causales de Sumario Administrativo (Art. 18.2)
                alertas_sumario = []
                if fallas_ifo_6meses[eot_hex] >= 3:
                    alertas_sumario.append("Causal de Sumario: Acumulación de 3 fallas de IFO (<80% o bajo umbral) en 6 meses (Art. 18.2)")
                if len(historial_faltas) >= 20:
                    alertas_sumario.append("Causal de Sumario: Acumulación de 20 o más infracciones en el periodo (Art. 18.2)")

                reporte_final.append({
                    'eot_nombre': eot_nombre,
                    'eot_hex': eot_hex,
                    'total_jornales': total_jornales,
                    'total_guaranies': total_guaranies,
                    'total_infracciones': len(historial_faltas),
                    'alerta_sumario': len(alertas_sumario) > 0,
                    'motivos_sumario': alertas_sumario,
                    'infracciones': [
                        {
                            'fecha': f['fecha'].strftime('%Y-%m-%d'),
                            'base': f['base'],
                            'desc': f['desc'],
                            'jornales': f['jornales'],
                            'monto': int(round(f['jornales'] * VALOR_JORNAL))
                        } for f in historial_faltas
                    ]
                })
                
        # Sort by company name
        reporte_final.sort(key=lambda x: x['eot_nombre'])
        
        return {
            'month': month,
            'year': year,
            'reporte': reporte_final
        }
        
    except Exception as e:
        print(f"Error generating fines report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
