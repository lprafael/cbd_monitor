from fastapi import APIRouter, HTTPException, Depends
from datetime import date, timedelta
from typing import List, Optional
import math
from models.monthly_schemas import MonthlyPerformanceRequest, MonthlyPerformanceResult
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/monthly-performance", tags=["Monthly Performance"])

def get_month_range(year: int, month: int):
    """Returns start and end date for a given month."""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return start_date, end_date

def get_previous_month(year: int, month: int):
    """Returns year, month for the previous month."""
    if month == 1:
        return year - 1, 12
    return year, month - 1

@router.post("", response_model=MonthlyPerformanceResult)
async def get_monthly_performance(
    request: MonthlyPerformanceRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Calculates the Monthly IFO Performance for a specific EOT.
    
    Rules:
    1. IFO Mensual: Average of Daily IFOs (which are average of Franja IFOs).
       - Excludes Sundays and Holidays.
       - Excludes 'Madrugada' and 'Nocturna' franjas.
    2. Comparison: IFO Sistema (Month n-1).
       - Average of Monthly IFOs of all EOTs in previous month.
    3. Thresholds:
       - Umbral Teorico: System(n-1) * 0.95
       - Umbral Aplicable: Umbral Teorico - 0.49 (percentage points)
    4. Infraction: IFO Mensual < Umbral Aplicable.
    """
    cursor = db.get_cursor()
    try:
        # 1. Get EOT Info (need vmt_hex)
        cursor.execute("SELECT eot_nombre, id_eot_vmt_hex FROM public.eots WHERE cod_catalogo = %s", (request.eot_id,))
        eot = cursor.fetchone()
        if not eot:
            raise HTTPException(status_code=404, detail="EOT not found")
        
        eot_nombre = eot['eot_nombre']
        eot_hex = eot['id_eot_vmt_hex']
        
        # Date ranges
        start_date, end_date = get_month_range(request.year, request.month)
        
        prev_year, prev_month = get_previous_month(request.year, request.month)
        prev_start, prev_end = get_month_range(prev_year, prev_month)
        
        # 2. Calculate IFO Mensual for Target EOT
        # Note: ifo in DB is 0-1 decimal. We convert to 0-100 for final result.
        query_ifo_mensual = """
            SELECT 
                AVG(daily_ifo) as monthly_ifo
            FROM (
                SELECT 
                    fecha, 
                    AVG(ifo) as daily_ifo
                FROM control_metricas.ifo_historico h
                JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                WHERE h.id_eot_vmt_hex = %s
                  AND h.fecha BETWEEN %s AND %s
                  AND extract(isodow from h.fecha) < 7 -- Exclude Sundays (7)
                  AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                  AND f.denominacion NOT ILIKE '%%Nocturn%%'
                  AND f.denominacion NOT ILIKE '%%Madrugada%%'
                GROUP BY fecha
            ) daily_avgs
        """
        cursor.execute(query_ifo_mensual, (eot_hex, start_date, end_date))
        res_eot = cursor.fetchone()
        ifo_mensual_val = res_eot['monthly_ifo'] if res_eot and res_eot['monthly_ifo'] is not None else 0.0
        # Convert to percentage
        ifo_mensual_pct = float(ifo_mensual_val * 100)
        
        # Get details for chart (daily IFOs)
        query_daily = """
            SELECT 
                fecha, 
                AVG(ifo) as daily_ifo
            FROM control_metricas.ifo_historico h
            JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
            WHERE h.id_eot_vmt_hex = %s
              AND h.fecha BETWEEN %s AND %s
              AND extract(isodow from h.fecha) < 7
              AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
              AND f.denominacion NOT ILIKE '%%Nocturn%%'
              AND f.denominacion NOT ILIKE '%%Madrugada%%'
            GROUP BY fecha
            ORDER BY fecha
        """
        cursor.execute(query_daily, (eot_hex, start_date, end_date))
        daily_rows = cursor.fetchall()
        ifo_diarios = [{'fecha': str(r['fecha']), 'ifo': float(r['daily_ifo'] * 100)} for r in daily_rows]
        
        # 3. Calculate IFO Sistema (Month n-1)
        query_system_prev = """
            SELECT 
                AVG(eot_monthly_ifo) as system_ifo
            FROM (
                SELECT 
                    id_eot_vmt_hex,
                    AVG(daily_ifo) as eot_monthly_ifo
                FROM (
                    SELECT 
                        id_eot_vmt_hex,
                        fecha, 
                        AVG(ifo) as daily_ifo
                    FROM control_metricas.ifo_historico h
                    JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
                    WHERE h.fecha BETWEEN %s AND %s
                      AND extract(isodow from h.fecha) < 7
                      AND h.fecha NOT IN (SELECT fecha FROM public.feriados)
                      AND f.denominacion NOT ILIKE '%%Nocturn%%'
                      AND f.denominacion NOT ILIKE '%%Madrugada%%'
                    GROUP BY id_eot_vmt_hex, fecha
                ) daily_avgs
                GROUP BY id_eot_vmt_hex
            ) eot_avgs
        """
        cursor.execute(query_system_prev, (prev_start, prev_end))
        res_sys = cursor.fetchone()
        system_ifo_val = res_sys['system_ifo'] if res_sys and res_sys['system_ifo'] is not None else 0.0
        system_ifo_pct = float(system_ifo_val * 100)
        
        # 4. Thresholds
        # Umbral Teórico: 95% of System(n-1)
        umbral_teorico = system_ifo_pct * 0.95
        
        # Factor de Ajuste: -0.49
        factor_ajuste = 0.49
        
        # Umbral Aplicable
        umbral_aplicable = umbral_teorico - factor_ajuste
        
        # Rounding rules: "Redondear resultados finales... al entero superior inmediato"
        # The prompt says: "Redondeo de Resultados: Todos los valores finales derivados de estas fórmulas... redondearse al entero superior inmediato (ej. 94,51 -> 95)."
        # It applies to "Umbral Aplicable" specifically? Or all final displayed values?
        # "Si el IFO Mensual (...) es inferior al Umbral Aplicable (94,50%)..."
        # Implicitly, the comparison should be done on rounded values?
        # Example: 94.51 -> 95. If IFO is 94.8 -> Infraction? No, 94.8 < 95 is True.
        # But wait, "Umbral Aplicable (aprox 94.50%)". If they round 94.50 -> 95.
        # Let's apply rounding to the Thresholds as requested.
        
        umbral_teorico_rounded = math.ceil(umbral_teorico) 
        # Wait, usually intermediate calculations are precise.
        # "Todos los valores finales derivados de estas fórmulas... redondearse al número entero superior inmediato"
        # It probably refers to the final Threshold against which we compare.
        # Let's round the Umbral Aplicable.
        
        umbral_aplicable_final = math.ceil(umbral_aplicable * 100) / 100.0 # Maybe just integer ceil?
        # The example says "94.51 -> 95". That is integer ceil.
        
        umbral_aplicable_int = math.ceil(umbral_aplicable)
        
        # But the prompt also says "Si el IFO Mensual (...) es inferior al Umbral Aplicable (94,50%)..."
        # The example explicitly mentions 94.50% as a threshold in the text, so maybe it's NOT always rounded to integer?
        # "Redondeo de Resultados: Todos los valores finales derivados de estas fórmulas... redondearse al número entero superior inmediato (ej. 94,51 -> 95)."
        # This instruction seems to contradict the "94.50%" text unless 94.50 was just an example of the result BEFORE rounding?
        # "Factor de Ajuste... para obtener el Umbral Aplicable (aprox. 94,50%)." -> This is the result of calculation.
        # Then Rule 4 says: "Redondeo... valores finales... redondearse al número entero superior inmediato".
        # So likely the final threshold IS an integer.
        
        umbral_aplicable_official = math.ceil(umbral_aplicable)

        # IFO Mensual precision: "mantenerse con al menos 4 decimales" during intermediate.
        # But for final comparison?
        # I'll stick to comparing the high precision IFO Mensual against the Rounded Threshold.
        # But display might round IFO Mensual too?
        # For safety, I will return the precise values and maybe a rounded version or just let frontend display it.
        # I'll return the rounded threshold as `umbral_aplicable`.
        
        # 5. Infraction
        # "Si el IFO Mensual (EOT) ... es inferior al Umbral Aplicable"
        infraccion = ifo_mensual_pct < umbral_aplicable_official
        sancion = "Infracción Gravísima (173 jornales)" if infraccion else "Sin Infracción"
        
        return MonthlyPerformanceResult(
            month=request.month,
            year=request.year,
            eot_nombre=eot_nombre,
            ifo_mensual_eot=round(ifo_mensual_pct, 4),
            ifo_sistema_anterior=round(system_ifo_pct, 4),
            umbral_teorico=round(umbral_teorico, 4),
            factor_ajuste=factor_ajuste,
            umbral_aplicable=umbral_aplicable_official,
            infraccion=infraccion,
            sancion=sancion,
            ifo_diarios=ifo_diarios
        )

    except Exception as e:
        print(f"Error calculating monthly performance: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
