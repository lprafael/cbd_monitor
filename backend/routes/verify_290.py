from fastapi import APIRouter, HTTPException, Depends
from datetime import date, timedelta, datetime
import calendar
from typing import List, Dict, Tuple, Optional
from models.verify_290_schemas import Verify290Request, Verify290ResultV2, FranjaResult, TroncalResult
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/verify-290", tags=["Verify 290"])

def get_days_in_month(year: int, month: int) -> List[date]:
    num_days = calendar.monthrange(year, month)[1]
    days = [date(year, month, day) for day in range(1, num_days + 1)]
    return days

# ---------------------------------------------------------
# Static Definitions for Resolution 290 Franjas Logic
# ---------------------------------------------------------

# Day Types: 5 (L-V), 6 (Sat), 7 (Sun/Hol)
DAY_TYPE_LABORAL = 5
DAY_TYPE_SABADO = 6
DAY_TYPE_DOM_FER = 7

# Requirements per (DayType, FranjaName) -> Required Services (Buses/Hr)
REQUIREMENTS = {
    DAY_TYPE_LABORAL: { # L-V
        "Pico": 4,
        "Post Pico": 2,
        "Nocturno": 1
    },
    DAY_TYPE_SABADO: { # Sat
        "Pico": 2,
        "Post Pico": 1,
        "Nocturno": 1
    },
    DAY_TYPE_DOM_FER: { # Sun/Hol
        "Unica": 1 # "Única" (07-19) - Assuming 1 bus/hr per text? "Dom y Feriados... 1 bus por hora"
    }
}

# Thresholds per (DayType, FranjaName) -> Percentage (0-100)
THRESHOLDS = {
    DAY_TYPE_LABORAL: {
        "Pico": 80,
        "Post Pico": 70,
        "Nocturno": 60
    },
    DAY_TYPE_SABADO: {
        "Pico": 80,
        "Post Pico": 70,
        "Nocturno": 50
    },
    DAY_TYPE_DOM_FER: {
        "Unica": 70
    }
}

# Time Ranges for Resolution 290
# Format: List of (StartHour, EndHourInclusive)
# Note: "05:00 - 07:59" means hour 5, 6, 7. Start=5, End=7.
R290_RANGES = {
    DAY_TYPE_LABORAL: {
        "Pico": [(5, 7), (16, 18)],
        "Post Pico": [(8, 15), (19, 20)],
        "Nocturno": [(21, 22)]
    },
    DAY_TYPE_SABADO: {
        "Pico": [(6, 15)],
        "Post Pico": [(16, 20)],
        "Nocturno": [(21, 22)]
    },
    DAY_TYPE_DOM_FER: {
        "Unica": [(7, 19)]
    }
}

# SORT WEIGHTS FOR FRANJAS (Point 1 of User Request)
FRANJA_SORT_WEIGHT = {
    (DAY_TYPE_LABORAL, "Pico"): 10,
    (DAY_TYPE_LABORAL, "Post Pico"): 20,
    (DAY_TYPE_LABORAL, "Nocturno"): 30,
    (DAY_TYPE_SABADO, "Pico"): 40,
    (DAY_TYPE_SABADO, "Post Pico"): 50,
    (DAY_TYPE_SABADO, "Nocturno"): 60,
    (DAY_TYPE_DOM_FER, "Unica"): 70
}

def get_day_type(d: date, holidays: set) -> int:
    if d in holidays:
        return DAY_TYPE_DOM_FER
    weekday = d.weekday() # 0=Mon, 6=Sun
    if weekday == 6:
        return DAY_TYPE_DOM_FER
    if weekday == 5:
        return DAY_TYPE_SABADO
    return DAY_TYPE_LABORAL

def get_franja_name_for_hour(day_type: int, hour: int) -> str:
    """Returns the name of the Franja (Pico/Post Pico/Nocturno/Unica) for a given hour."""
    ranges = R290_RANGES.get(day_type, {})
    for name, hour_list in ranges.items():
        for (start, end) in hour_list:
            if start <= hour <= end:
                return name
    return None # Period not covered by R290 (e.g. Madrugada)

@router.post("", response_model=Verify290ResultV2)
async def verify_290(
    request: Verify290Request,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        # 1. Get EOT Name and Catalog ID
        cursor.execute("SELECT eot_nombre, cod_catalogo FROM public.eots WHERE cod_catalogo = %s", (request.eot_id,))
        eot = cursor.fetchone()
        if not eot:
            raise HTTPException(status_code=404, detail="EOT not found")
        eot_nombre = eot['eot_nombre']
        eot_catalogo = eot['cod_catalogo']
        
        # 2. Setup Dates
        start_date = date(request.year, request.month, 1)
        _, last_day = calendar.monthrange(request.year, request.month)
        end_date = date(request.year, request.month, last_day)
        
        today = date.today()
        limit_date = end_date
        is_current_month = (request.year == today.year and request.month == today.month)
        if is_current_month:
            limit_date = today - timedelta(days=1)

        # 3. Get Special Days (Holidays & Rain)
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (start_date, limit_date))
        holidays = set([row['fecha'] for row in cursor.fetchall()])
        
        cursor.execute("SELECT fecha_evento FROM control_metricas.t_casuisticas_lluvia WHERE fecha_evento BETWEEN %s AND %s", (start_date, limit_date))
        rainy_days = set([row['fecha_evento'] for row in cursor.fetchall()])
        
        all_month_days = get_days_in_month(request.year, request.month)
        if is_current_month:
            all_month_days = [d for d in all_month_days if d <= limit_date]
        
        # 4. Calculate Common Denominators (Requirements) and metrics
        req_map = {}
        day_count_map = {} # Track actual day counts with rain factor
        for dt_code, franja_dict in R290_RANGES.items():
            for fname in franja_dict.keys():
                req_map[(dt_code, fname)] = {
                    'sum_req': 0.0, 
                    'count_days': 0,
                    'count_rain': 0
                }
                day_count_map[(dt_code, fname)] = 0.0

        day_type_map = {} 
        for d in all_month_days:
            dt = get_day_type(d, holidays)
            day_type_map[d] = dt
            is_rain = d in rainy_days
            day_factor = 0.5 if is_rain else 1.0  # Tu criterio: días de lluvia valen 0.5
            
            ranges = R290_RANGES.get(dt, {})
            reqs_def = REQUIREMENTS.get(dt, {})
            
            for fname, hour_intervals in ranges.items():
                base_hourly = reqs_def.get(fname, 0)
                hours_count = 0
                for (start, end) in hour_intervals:
                    hours_count += (end - start + 1)
                daily_req_total = base_hourly * hours_count * day_factor
                if (dt, fname) in req_map:
                    req_map[(dt, fname)]['sum_req'] += float(daily_req_total)
                    req_map[(dt, fname)]['count_days'] += 1
                    req_map[(dt, fname)]['count_rain'] += 1 if is_rain else 0
                    # Tu criterio: contar días con factor de lluvia
                    day_count_map[(dt, fname)] += day_factor

        # Calculate Remaining Days for Projection
        remaining_days_req = {} 
        if is_current_month:
            cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (start_date, end_date))
            full_holidays = set([row['fecha'] for row in cursor.fetchall()])
            all_days = get_days_in_month(request.year, request.month)
            remaining_days = [d for d in all_days if d >= today]
            for d in remaining_days:
                dt = get_day_type(d, full_holidays)
                ranges = R290_RANGES.get(dt, {})
                reqs_def = REQUIREMENTS.get(dt, {})
                for fname, hour_intervals in ranges.items():
                    base_hourly = reqs_def.get(fname, 0)
                    hours_count = 0
                    for (start, end) in hour_intervals:
                        hours_count += (end - start + 1)
                    key = (dt, fname)
                    if key not in remaining_days_req:
                        remaining_days_req[key] = {'sum_req': 0.0, 'count_days': 0}
                    remaining_days_req[key]['sum_req'] += float(base_hourly * hours_count)
                    remaining_days_req[key]['count_days'] += 1

        # 5. Identify Troncales
        query_troncales = """
            SELECT DISTINCT identificador_troncal 
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = %s
              AND fecha BETWEEN %s AND %s
              AND identificador_troncal IS NOT NULL
        """
        cursor.execute(query_troncales, (eot_catalogo, start_date, limit_date))
        rows_troncales = cursor.fetchall()
        troncales_list = [r['identificador_troncal'] for r in rows_troncales]
        if not troncales_list:
            troncales_list = ["GENERAL"]
            cursor.execute("SELECT count(*) as c FROM public.servicios_diarios WHERE id_eot_catalogo=%s AND fecha BETWEEN %s AND %s", (eot_catalogo, start_date, limit_date))
            if cursor.fetchone()['c'] <= 0:
                 troncales_list = []

        # 6. Process Per Troncal
        detalles_troncal = []
        labels_dt = { DAY_TYPE_LABORAL: "Laboral", DAY_TYPE_SABADO: "Sábado", DAY_TYPE_DOM_FER: "Dom/Fer" }
        
        for troncal_id in troncales_list:
            res_results = {}
            for k in req_map.keys():
                res_results[k] = 0.0

            sum_hourly_map = {}  # (dt, fname, hour) -> sum servicios en el periodo
            
            query_services = """
                SELECT 
                    sd.fecha,
                    EXTRACT(HOUR FROM (sd.hora * INTERVAL '1 hour')::time)::int as hora,
                    COUNT(DISTINCT sd.idsam) as servicios
                FROM public.servicios_diarios sd
                WHERE sd.id_eot_catalogo = %s
                  AND sd.fecha BETWEEN %s AND %s
            """
            params = [eot_catalogo, start_date, limit_date]
            if troncal_id != "GENERAL":
                query_services += " AND sd.identificador_troncal = %s"
                params.append(troncal_id)
            query_services += " GROUP BY sd.fecha, EXTRACT(HOUR FROM (sd.hora * INTERVAL '1 hour')::time)"
            cursor.execute(query_services, tuple(params))
            rows_serv = cursor.fetchall()
            
            breakdown_map = {}
            for r in rows_serv:
                d = r['fecha']
                h = r['hora']
                cnt = r['servicios']
                dt = day_type_map.get(d)
                if dt is None:
                    continue
                fname = get_franja_name_for_hour(dt, h)
                if not fname:
                    continue

                key = (dt, fname)
                hour_key = (dt, fname, int(h))

                if key not in breakdown_map:
                    breakdown_map[key] = []
                breakdown_map[key].append({
                    'fecha': str(d),
                    'hora': int(h),
                    'servicios': int(cnt)
                })

                if (dt, fname) in res_results:
                    res_results[(dt, fname)] += float(cnt)

                if hour_key not in sum_hourly_map:
                    sum_hourly_map[hour_key] = 0.0
                sum_hourly_map[hour_key] += float(cnt)

            hourly_performance_map = {}
            for (dt, fname, h), sum_cnt in sum_hourly_map.items():
                required_services = REQUIREMENTS.get(dt, {}).get(fname, 0)
                if required_services <= 0:
                    continue
                dias_eq = float(day_count_map.get((dt, fname), 0.0))
                if dias_eq <= 0:
                    continue
                denom = dias_eq * float(required_services)
                pct_h = (sum_cnt / denom * 100.0) if denom > 0 else 0.0
                hourly_performance_map[(dt, fname, h)] = float(min(pct_h, 100.0))
            
            franjas_list_with_meta = [] # (sort_weight, FranjaResult)
            for (dt, fname), req_data in req_map.items():
                sum_req = float(req_data['sum_req'])
                count = int(req_data['count_days'])
                count_rain = int(req_data['count_rain'])
                if count == 0: continue
                sum_serv = float(res_results.get((dt, fname), 0.0))
                
                # Tu criterio: calcular rendimiento por franja como promedio de rendimientos horarios
                franja_ranges = R290_RANGES.get(dt, {}).get(fname, [])
                hourly_performances = []
                detalle_horario = []

                dias_eq = float(day_count_map.get((dt, fname), 0.0))
                req_por_hora = float(REQUIREMENTS.get(dt, {}).get(fname, 0))
                
                for (start, end) in franja_ranges:
                    for hour in range(start, end + 1):
                        hour_key = (dt, fname, hour)
                        pct_h = float(hourly_performance_map.get(hour_key, 0.0))
                        hourly_performances.append(pct_h)

                        servicios_h = float(sum_hourly_map.get(hour_key, 0.0))
                        denom_h = float(dias_eq * req_por_hora) if dias_eq > 0 and req_por_hora > 0 else 0.0
                        pct_h_raw = float((servicios_h / denom_h * 100.0) if denom_h > 0 else 0.0)

                        needed_bh = None
                        if is_current_month:
                            rem = remaining_days_req.get((dt, fname))
                            d_restantes_local = int(rem['count_days']) if rem else 0
                            if d_restantes_local > 0 and req_por_hora > 0:
                                target_total = (float(THRESHOLDS.get(dt, {}).get(fname, 0)) / 100.0) * ((dias_eq + d_restantes_local) * req_por_hora)
                                needed_total = float(target_total - servicios_h)
                                needed_bh = float(max(0.0, needed_total / d_restantes_local))

                        detalle_horario.append({
                            'hora': int(hour),
                            'servicios': round(servicios_h, 2),
                            'dias_equivalentes': round(dias_eq, 2),
                            'requerido_por_hora': round(req_por_hora, 2),
                            'denominador': round(denom_h, 2),
                            'rendimiento': round(pct_h_raw, 2),
                            'rendimiento_topeado': round(pct_h, 2),
                            'necesario_bh_restante': round(needed_bh, 2) if needed_bh is not None else None
                        })
                
                # Calcular rendimiento de la franja como promedio de rendimientos horarios
                if hourly_performances:
                    franja_rendimiento = sum(hourly_performances) / len(hourly_performances)
                else:
                    # Si no hay datos horarios, usar método tradicional como fallback
                    franja_rendimiento = float((sum_serv / sum_req * 100) if sum_req > 0 else (100 if sum_serv > 0 else 0))
                
                # Mantener cálculos tradicionales para display
                hours_duration = 0
                for (start, end) in franja_ranges:
                    hours_duration += (end - start + 1)
                if hours_duration == 0: hours_duration = 1

                total_horas_equiv = float(dias_eq * hours_duration) if dias_eq > 0 else float(count * hours_duration)
                if total_horas_equiv <= 0:
                    total_horas_equiv = 1.0

                avg_serv_per_hour = float(sum_serv / total_horas_equiv)
                avg_req_per_hour = float(sum_req / total_horas_equiv) if sum_req > 0 else float(req_por_hora)
                
                # Usar el nuevo cálculo de rendimiento
                pct = franja_rendimiento
                threshold = float(THRESHOLDS.get(dt, {}).get(fname, 0))
                cumple = bool(pct >= threshold)
                
                proj_val = None
                d_restantes = None
                if is_current_month:
                    rem = remaining_days_req.get((dt, fname))
                    if rem:
                        d_restantes = int(rem['count_days'])
                        if d_restantes > 0:
                            target_serv_total = (threshold / 100.0) * (sum_req + rem['sum_req'])
                            needed_serv_total = target_serv_total - sum_serv
                            if needed_serv_total <= 0:
                                proj_val = 0.0
                            else:
                                proj_val = float(needed_serv_total / (d_restantes * hours_duration))

                # Get breakdown for this franja
                desglose = breakdown_map.get((dt, fname), [])
                
                res = FranjaResult(
                    id_franja=0,
                    nombre_franja=f"{fname} ({labels_dt[dt]})",
                    servicios_realizados=round(avg_serv_per_hour, 2),
                    sum_servicios=float(sum_serv),
                    total_horas=float(round(total_horas_equiv, 2)),
                    exigencia=round(avg_req_per_hour, 2),
                    umbral=float(threshold),
                    rendimiento=round(pct, 2),
                    rendimiento_normalizado=round(min(pct, 100.0), 2),
                    dias_contabilizados=int(count),
                    dias_lluvia=int(count_rain),
                    dias_equivalentes=float(round(dias_eq, 2)),
                    proyeccion_requerida=round(proj_val, 2) if proj_val is not None else None,
                    dias_restantes=d_restantes,
                    desglose_diario=desglose,
                    detalle_horario=detalle_horario,
                    cumple=cumple,
                    estado="CUMPLE" if cumple else "NO CUMPLE"
                )
                weight = FRANJA_SORT_WEIGHT.get((dt, fname), 999)
                franjas_list_with_meta.append((weight, res))
            
            # Sort by predefined weight
            franjas_list_with_meta.sort(key=lambda x: x[0])
            sorted_franjas = [x[1] for x in franjas_list_with_meta]
            
            detalles_troncal.append(TroncalResult(
                nombre_troncal=troncal_id if troncal_id != "GENERAL" else "Troncal General",
                resultados_franjas=sorted_franjas
            ))
            
        projection_msg = ""
        if is_current_month:
            projection_msg = f" (Status al {limit_date})"

        return Verify290ResultV2(
            month=int(request.month),
            year=int(request.year),
            eot_nombre=str(eot_nombre),
            detalles_troncal=detalles_troncal,
            resumen_global=f"Análisis R290 Mensual{projection_msg}"
        )
    except Exception as e:
        print(f"Error 290: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
