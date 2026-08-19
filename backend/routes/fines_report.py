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
        
        # Excepción de Mayo
        # La Etapa 2 corre solo a partir del 19 de mayo de 2026.
        cutoff_date = date(2026, 5, 19)
        
        # eval_start es la fecha desde la cual REPORTO multas
        eval_start = max(start_date, cutoff_date)
        
        # hist_start es la fecha desde la cual CARGO datos para calcular reincidencias (hasta 7 días antes)
        # pero no antes del cutoff_date porque no había multas antes de esa fecha.
        hist_start = max(eval_start - timedelta(days=7), cutoff_date)
                
        # 1. Obtener feriados
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (hist_start, end_date))
        db_feriados = set(row['fecha'] for row in cursor.fetchall())
        
        # 1.b Obtener días atípicos
        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (hist_start, end_date))
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
        """, (end_date, hist_start, end_date, hist_start))
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
            
        # 4. Obtener todos los datos de IFO del mes (incluyendo ventana histórica)
        cursor.execute("""
            SELECT id_eot_vmt_hex, fecha, id_franja, ifo, cbd_indice
            FROM control_metricas.ifo_historico
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha, id_eot_vmt_hex, id_franja
        """, (hist_start, end_date))
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
        
        # Calcular IFO mensual por EOT (rango normal o recortado, según start_date)
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
        
        reporte_final = []
        
        # 6. Evaluar infracciones para cada EOT
        for eot_hex, eot_nombre in eots_by_hex.items():
            historial_faltas = []
            alertas = []
            
            # Art 15.1
            ifo_mensual_eot = ifo_mensual_dict.get(eot_hex, 0.0)
            if ifo_mensual_eot > 0 and ifo_mensual_eot < umbral_objetivo:
                # Nota: Para calcular la reincidencia (16.1) y el sumario, idealmente se consultan meses pasados.
                # Como simplificación, registramos la ordinaria si estamos en el periodo de evaluación
                if end_date >= eval_start:
                    historial_faltas.append({
                        'fecha': end_date,
                        'base': 'Art. 15.1',
                        'desc': f'IFO Mensual ({ifo_mensual_eot:.2f}%) inferior al Umbral ({umbral_objetivo:.2f}%)',
                        'jornales': 173
                    })
                
            # Agrupar datos diarios para Art 15.2 - 15.6
            dias_data = defaultdict(dict)
            for r in datos_por_eot[eot_hex]:
                dias_data[r['fecha']][r['id_franja']] = r
                
            acum_b = {'PICO': 0, 'POS_PICO': 0}
            acum_b_reinc = {'PICO': 0, 'POS_PICO': 0}
            
            # Trackers
            ultimo_15_3_fecha = None
            ultimo_15_5_fecha = None
            ultimo_15_6_fecha = None
            
            trigger_15_2_fecha = None
            trigger_15_4_fecha = None
            
            fechas_ordenadas = sorted(dias_data.keys())
            for fecha_eval in fechas_ordenadas:
                id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                if id_tipo_dia == 7: continue # Descartar Domingos y Feriados
                if fecha_eval in db_atipicos: continue # Descartar Días Atípicos (Lluvia, etc.)
                
                franjas_dia = dias_data[fecha_eval]
                
                # Banderas por día
                fail_15_3 = False
                fail_15_5 = False
                fail_15_6 = False
                
                for fid, f_res in franjas_dia.items():
                    meta = franjas_metadata.get(fid, {})
                    cat = categorizar(meta.get('denominacion', ''))
                    if cat == "OTRO" or f_res['ifo'] is None: continue
                    
                    # Etapa 2: Excluir Pos Pico de Sábado del cálculo de multas
                    if id_tipo_dia == 6 and cat == 'POS_PICO':
                        continue
                    
                    ifo_val = float(f_res['ifo']) * 100
                    cbd_idx = float(f_res['cbd_indice']) if f_res['cbd_indice'] is not None else 0.0
                    
                    # Art 15.6 (ICCBDM)
                    if cbd_idx < 1.0:
                        fail_15_6 = True

                    # Art 15.3 y 15.5 (Nivel C Pico y Pos Pico)
                    if cat == 'PICO':
                        if ifo_val < 80:
                            fail_15_3 = True
                        elif ifo_val < 90:
                            if not trigger_15_2_fecha:
                                if fecha_eval >= eval_start: acum_b['PICO'] += 1
                            else:
                                if 1 <= (fecha_eval - trigger_15_2_fecha).days <= 7:
                                    if fecha_eval >= eval_start: acum_b_reinc['PICO'] += 1

                    elif cat == 'POS_PICO':
                        if ifo_val < 80:
                            fail_15_5 = True
                        elif ifo_val < 90:
                            if not trigger_15_4_fecha:
                                if fecha_eval >= eval_start: acum_b['POS_PICO'] += 1
                            else:
                                if 1 <= (fecha_eval - trigger_15_4_fecha).days <= 7:
                                    if fecha_eval >= eval_start: acum_b_reinc['POS_PICO'] += 1

                # Evaluaciones Diarias (Fuera del loop de franjas)
                if fail_15_6:
                    if ultimo_15_6_fecha and 1 <= (fecha_eval - ultimo_15_6_fecha).days <= 2:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.6', 'desc': 'Reincidencia ICCBDM (Día)', 'jornales': 45})
                    else:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM Día', 'jornales': 20})
                        if not ultimo_15_6_fecha or (fecha_eval - ultimo_15_6_fecha).days > 2:
                            ultimo_15_6_fecha = fecha_eval

                if fail_15_3:
                    if ultimo_15_3_fecha and 1 <= (fecha_eval - ultimo_15_3_fecha).days <= 7:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.3', 'desc': 'Reincidencia Nivel C Pico', 'jornales': 45})
                    else:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3', 'desc': 'Nivel C Franja Pico', 'jornales': 20})
                        if not ultimo_15_3_fecha or (fecha_eval - ultimo_15_3_fecha).days > 7:
                            ultimo_15_3_fecha = fecha_eval

                if fail_15_5:
                    if ultimo_15_5_fecha and 1 <= (fecha_eval - ultimo_15_5_fecha).days <= 7:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.5', 'desc': 'Reincidencia Nivel C Pos Pico', 'jornales': 45})
                    else:
                        if fecha_eval >= eval_start:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.5', 'desc': 'Nivel C Franja Pos Pico', 'jornales': 20})
                        if not ultimo_15_5_fecha or (fecha_eval - ultimo_15_5_fecha).days > 7:
                            ultimo_15_5_fecha = fecha_eval

                # Evaluaciones de Acumulación Diaria (Art 15.2 y 15.4)
                if fecha_eval >= eval_start:
                    if not trigger_15_2_fecha and acum_b['PICO'] >= 5:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.2', 'desc': 'Acumulación 5 Franjas Pico Nivel B', 'jornales': 10})
                        trigger_15_2_fecha = fecha_eval
                    elif trigger_15_2_fecha and acum_b_reinc['PICO'] >= 5:
                        if 1 <= (fecha_eval - trigger_15_2_fecha).days <= 7:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.2', 'desc': 'Reincidencia Nivel B Pico (5 más en 7 días)', 'jornales': 20})
                            # Reiniciar
                            trigger_15_2_fecha = fecha_eval
                            acum_b_reinc['PICO'] = 0

                    if not trigger_15_4_fecha and acum_b['POS_PICO'] >= 5:
                        historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.4', 'desc': 'Acumulación 5 Franjas Pos Pico Nivel B', 'jornales': 10})
                        trigger_15_4_fecha = fecha_eval
                    elif trigger_15_4_fecha and acum_b_reinc['POS_PICO'] >= 5:
                        if 1 <= (fecha_eval - trigger_15_4_fecha).days <= 7:
                            historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 16.4', 'desc': 'Reincidencia Nivel B Pos Pico (5 más en 7 días)', 'jornales': 20})
                            trigger_15_4_fecha = fecha_eval
                            acum_b_reinc['POS_PICO'] = 0

            # Evaluar Sumario (20 multas) - Solo una alerta basada en el mes actual como aproximación
            if len(historial_faltas) >= 20:
                alertas.append("ALERTA ART. 18: La EOT acumula 20 o más infracciones, pasible de Sumario Administrativo.")
                        
            if historial_faltas:
                # Calcular totales
                total_jornales = sum(f['jornales'] for f in historial_faltas)
                total_guaranies = total_jornales * VALOR_JORNAL
                
                reporte_final.append({
                    'eot_nombre': eot_nombre,
                    'eot_hex': eot_hex,
                    'total_jornales': total_jornales,
                    'total_guaranies': total_guaranies,
                    'alertas': alertas,
                    'infracciones': [
                        {
                            'fecha': f['fecha'].strftime('%Y-%m-%d'),
                            'base': f['base'],
                            'desc': f['desc'],
                            'jornales': f['jornales'],
                            'monto': f['jornales'] * VALOR_JORNAL
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
