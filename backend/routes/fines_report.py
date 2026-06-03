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
        # "Con respecto al mes de mayo, considerar que se contabiliza recién a partir el día 19/06" (asumiendo 19/05 o aplicando la restricción)
        # Aplicaremos un inicio modificado si es mayo de 2026
        if year == 2026 and month == 5:
            # Usaremos 19/05 como start date según interpretación lógica (o 19/06 no aplica a mayo)
            # Para estar seguros, si pidieron 19/06 literal, tal vez se refieren a Junio, pero dijeron "mes de mayo".
            # Vamos a ignorar todo antes del 19 de mayo.
            cutoff_date = date(2026, 5, 19)
            if start_date < cutoff_date:
                start_date = cutoff_date
                
        # 1. Obtener feriados
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (start_date, end_date))
        db_feriados = set(row['fecha'] for row in cursor.fetchall())
        
        # 2. Obtener EOTs
        cursor.execute("SELECT cod_catalogo, eot_nombre, id_eot_vmt_hex FROM public.eots WHERE cod_catalogo NOT IN (72)")
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
        """, (end_date, start_date, end_date, start_date))
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
            
        # 4. Obtener todos los datos de IFO del mes (solo el rango modificado)
        cursor.execute("""
            SELECT id_eot_vmt_hex, fecha, id_franja, ifo, cbd_indice
            FROM control_metricas.ifo_historico
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha, id_eot_vmt_hex, id_franja
        """, (start_date, end_date))
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
                    SELECT id_eot_vmt_hex, fecha, LEAST(AVG(ifo), 1.1) as daily_ifo_topeado
                    FROM control_metricas.ifo_historico
                    WHERE fecha BETWEEN %s AND %s
                    GROUP BY id_eot_vmt_hex, fecha
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
                SELECT id_eot_vmt_hex, fecha, LEAST(AVG(ifo), 1.1) as daily_ifo_topeado
                FROM control_metricas.ifo_historico
                WHERE fecha BETWEEN %s AND %s
                GROUP BY id_eot_vmt_hex, fecha
            ) daily_avgs
            GROUP BY id_eot_vmt_hex
        """, (start_date, end_date))
        ifo_mensual_dict = {row['id_eot_vmt_hex']: float(row['monthly_ifo_topeado'] * 100) for row in cursor.fetchall()}
        
        reporte_final = []
        
        # 6. Evaluar infracciones para cada EOT
        for eot_hex, eot_nombre in eots_by_hex.items():
            historial_faltas = []
            
            # Art 15.1
            ifo_mensual_eot = ifo_mensual_dict.get(eot_hex, 0.0)
            if ifo_mensual_eot > 0 and ifo_mensual_eot < umbral_objetivo:
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
            
            fechas_ordenadas = sorted(dias_data.keys())
            for fecha_eval in fechas_ordenadas:
                id_tipo_dia = get_tipo_dia_id(fecha_eval, db_feriados)
                if id_tipo_dia == 7: continue # Descartar Domingos y Feriados
                
                franjas_dia = dias_data[fecha_eval]
                
                fail_15_3, fail_15_5, fail_15_6 = False, False, False
                
                for fid, f_res in franjas_dia.items():
                    meta = franjas_metadata.get(fid, {})
                    cat = categorizar(meta.get('denominacion', ''))
                    if cat == "OTRO" or f_res['ifo'] is None: continue
                    
                    ifo_val = float(f_res['ifo']) * 100
                    cbd_idx = float(f_res['cbd_indice']) if f_res['cbd_indice'] is not None else 0.0
                    
                    if cbd_idx < 1.0: fail_15_6 = True
                    
                    if cat == 'PICO':
                        if ifo_val < 80: fail_15_3 = True
                        elif ifo_val < 90: acum_b['PICO'] += 1
                    elif cat == 'POS_PICO':
                        if ifo_val < 80: fail_15_5 = True
                        elif ifo_val < 90: acum_b['POS_PICO'] += 1
                            
                # ICCBDM (15.6) - Sin reincidencia
                if fail_15_6:
                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM (Buses Mínimos)', 'jornales': 20})
                        
                # NIVEL C PICO (15.3) - Sin reincidencia
                if fail_15_3:
                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
                        
                # NIVEL C POS PICO (15.5) - Sin reincidencia
                if fail_15_5:
                    historial_faltas.append({'fecha': fecha_eval, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})
                        
            # ACUMULACIÓN NIVEL B PICO (15.2 / 16.2) - Reincidencia Única Mensual y Sustitutiva
            if acum_b['PICO'] >= 10:
                historial_faltas.append({'fecha': end_date, 'base': 'Art. 16.2', 'desc': 'Reincidencia Nivel B Pico (Única Mensual)', 'jornales': 20})
            elif acum_b['PICO'] >= 5:
                historial_faltas.append({'fecha': end_date, 'base': 'Art. 15.2', 'desc': 'Acumulación 5 Franjas Pico Nivel B', 'jornales': 10})
                
            # ACUMULACIÓN NIVEL B POS PICO (15.4 / 16.3) - Reincidencia Única Mensual y Sustitutiva
            if acum_b['POS_PICO'] >= 10:
                historial_faltas.append({'fecha': end_date, 'base': 'Art. 16.3', 'desc': 'Reincidencia Nivel B Pos Pico (Única Mensual)', 'jornales': 20})
            elif acum_b['POS_PICO'] >= 5:
                historial_faltas.append({'fecha': end_date, 'base': 'Art. 15.4', 'desc': 'Acumulación 5 Franjas Pos Pico Nivel B', 'jornales': 10})
                        
            if historial_faltas:
                # Calcular totales
                total_jornales = sum(f['jornales'] for f in historial_faltas)
                total_guaranies = total_jornales * VALOR_JORNAL
                
                reporte_final.append({
                    'eot_nombre': eot_nombre,
                    'eot_hex': eot_hex,
                    'total_jornales': total_jornales,
                    'total_guaranies': total_guaranies,
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
