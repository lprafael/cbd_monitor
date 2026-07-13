from fastapi import APIRouter, HTTPException, Depends
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
import calendar
from database.connection import DatabaseConnection, get_db_connection
from models.report_schemas import (
    MonthlyReportRequest, MonthlyReportResponse, 
    SystemIFOResponse, ParametersIFOResponse,
    TipoDiaReport, FranjaInfo, DiaData,
    SystemIFOBreakdownResponse, EOTMonthlyIFO,
    AdvancedDailyReportResponse
)
from .performance import get_factores_ajuste_acumulados

router = APIRouter(prefix="/api/reports/res120", tags=["Reports Resolution 120/2025"])

def get_tipo_dia_id(fecha_obj: date, feriados_set: Optional[set] = None) -> int:
    """
    Determinar el id_tipo_dia basado en la fecha (5=LABORAL, 6=SABADO, 7=NO LABORAL).
    """
    if feriados_set is not None and str(fecha_obj) in feriados_set:
        return 7
    dia_semana = fecha_obj.weekday()
    if dia_semana == 5:
        return 6
    elif dia_semana == 6:
        return 7
    else:
        return 5

@router.post("/monthly-summary", response_model=MonthlyReportResponse)
async def get_monthly_summary(
    request: MonthlyReportRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        id_eot_vmt_hex = request.id_eot_vmt_hex
        fecha_referencia = request.fecha_referencia
        primer_dia_mes = fecha_referencia.replace(day=1)
        
        tipos_dia_info = {
            5: {'nombre': 'D\u00eda Laboral', 'franjas': {}, 'dias': {}},
            6: {'nombre': 'S\u00e1bado', 'franjas': {}, 'dias': {}},
            7: {'nombre': 'Domingo/Feriado', 'franjas': {}, 'dias': {}}
        }
        
        for id_tipo_dia in [5, 6, 7]:
            cursor.execute("""
                SELECT DISTINCT f.id_franja, f.denominacion, f.hora_inicio, f.hora_fin
                FROM control_metricas.franjas_operativas f
                WHERE f.id_tipo_dia = %s
                  AND (f.inicio_vigencia IS NULL OR f.inicio_vigencia <= %s)
                  AND (f.fin_vigencia IS NULL OR f.fin_vigencia >= %s)
                ORDER BY f.hora_inicio
            """, (id_tipo_dia, fecha_referencia, primer_dia_mes))
            franjas_tipo = cursor.fetchall()
            
            franjas_info = {}
            for f in franjas_tipo:
                id_franja = f['id_franja']
                cursor.execute("""
                    SELECT cbd_minimo_franja
                    FROM control_metricas.cbd_parametros_minimos
                    WHERE id_franja = %s
                      AND id_tipo_dia = %s
                      AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
                      AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
                    ORDER BY vigencia_desde DESC NULLS LAST
                    LIMIT 1
                """, (id_franja, id_tipo_dia, fecha_referencia, primer_dia_mes))
                param_result = cursor.fetchone()
                cbd_minimo = param_result['cbd_minimo_franja'] if param_result else None
                
                franjas_info[str(id_franja)] = FranjaInfo(
                    denominacion=f['denominacion'],
                    hora_inicio=f['hora_inicio'].strftime('%H:%M:%S') if f['hora_inicio'] else None,
                    hora_fin=f['hora_fin'].strftime('%H:%M:%S') if f['hora_fin'] else None,
                    cbd_minimo=cbd_minimo
                )
            tipos_dia_info[id_tipo_dia]['franjas'] = franjas_info

        cursor.execute(
            "SELECT fecha FROM public.feriados WHERE fecha >= %s AND fecha <= %s",
            (primer_dia_mes, fecha_referencia)
        )
        feriados_set = {str(row['fecha']) for row in cursor.fetchall()}

        fecha_actual = primer_dia_mes
        while fecha_actual <= fecha_referencia:
            td_id = get_tipo_dia_id(fecha_actual, feriados_set)
            if td_id in tipos_dia_info:
                tipos_dia_info[td_id]['dias'][str(fecha_actual)] = {'franjas': {}, 'ifo_diario': None}
            fecha_actual += timedelta(days=1)

        cursor.execute("""
            SELECT fecha, id_franja, ifo, cbd_indice, cbd_cantidad
            FROM control_metricas.ifo_historico
            WHERE id_eot_vmt_hex = %s 
              AND fecha >= %s 
              AND fecha <= %s
            ORDER BY fecha, id_franja
        """, (id_eot_vmt_hex, primer_dia_mes, fecha_referencia))
        datos_ifo = cursor.fetchall()
        
        for row in datos_ifo:
            fecha_str = str(row['fecha'])
            id_franja = str(row['id_franja'])
            td_id = get_tipo_dia_id(row['fecha'], feriados_set)
            
            if td_id in tipos_dia_info and fecha_str in tipos_dia_info[td_id]['dias']:
                tipos_dia_info[td_id]['dias'][fecha_str]['franjas'][id_franja] = {
                    'ifo': (float(row['ifo']) * 100) if row['ifo'] is not None else 0,
                    'cbd': float(row['cbd_indice']) if row['cbd_indice'] is not None else 0,
                    'cbd_cantidad': int(row['cbd_cantidad']) if row['cbd_cantidad'] is not None else 0
                }

        ifos_diarios_mes = []
        for td_id, td_data in tipos_dia_info.items():
            for f_str, dia_data in td_data['dias'].items():
                franjas_dia = dia_data['franjas']
                ifos = [f['ifo'] for f in franjas_dia.values() if f.get('ifo') is not None]
                if ifos:
                    avg_diario = min(sum(ifos) / len(ifos), 110.0)
                    dia_data['ifo_diario'] = avg_diario
                    ifos_diarios_mes.append(avg_diario)

        ifo_mes = sum(ifos_diarios_mes) / len(ifos_diarios_mes) if ifos_diarios_mes else 0
        
        return MonthlyReportResponse(
            tipos_dia=tipos_dia_info,
            ifo_mes=float(round(ifo_mes, 4)),
            total_franjas=sum(len(t['franjas']) for t in tipos_dia_info.values()),
            total_dias=sum(len(t['dias']) for t in tipos_dia_info.values())
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

# Cache global para baselines mensuales para mejorar performance
baseline_cache = {}

@router.get("/system-ifo-baseline/{fecha}", response_model=SystemIFOResponse)
async def get_system_ifo_baseline(fecha: date, db: DatabaseConnection = Depends(get_db_connection)):
    # Usar cache si ya se calculó para este mes anterior
    if fecha.month == 1:
        mes_ant, anio_ant = 12, fecha.year - 1
    else:
        mes_ant, anio_ant = fecha.month - 1, fecha.year
    
    cache_key = f"{anio_ant}-{mes_ant}"
    if cache_key in baseline_cache:
        return SystemIFOResponse(**baseline_cache[cache_key])

    cursor = db.get_cursor()
    try:
        if fecha.month == 1:
            mes_ant, anio_ant = 12, fecha.year - 1
        else:
            mes_ant, anio_ant = fecha.month - 1, fecha.year
            
        _, last_day = calendar.monthrange(anio_ant, mes_ant)
        inicio_mes_ant = date(anio_ant, mes_ant, 1)
        fin_mes_ant = date(anio_ant, mes_ant, last_day)
        
        query = """
        WITH ifo_diario AS (
            SELECT 
                h.id_eot_vmt_hex,
                h.fecha,
                AVG(h.ifo) as ifo_dia_real,
                LEAST(AVG(h.ifo), 1.1) as ifo_dia_topeado
            FROM control_metricas.ifo_historico h
            WHERE h.fecha >= %s AND h.fecha <= %s
            GROUP BY h.id_eot_vmt_hex, h.fecha
        ),
        ifo_mensual_eot AS (
            SELECT 
                i.id_eot_vmt_hex,
                AVG(i.ifo_dia_real) * 100 as ifo_mensual_real,
                AVG(i.ifo_dia_topeado) * 100 as ifo_mensual_topeado
            FROM ifo_diario i
            JOIN public.eots e ON i.id_eot_vmt_hex = e.id_eot_vmt_hex
            WHERE e.cod_catalogo NOT IN (72)
            GROUP BY i.id_eot_vmt_hex
        )
        SELECT 
            AVG(ifo_mensual_real) as ifo_sistema_real,
            AVG(ifo_mensual_topeado) as ifo_sistema_topeado
        FROM ifo_mensual_eot;
        """
        cursor.execute(query, (inicio_mes_ant, fin_mes_ant))
        res = cursor.fetchone()
        
        ifo_topeado = float(res['ifo_sistema_topeado']) if res and res['ifo_sistema_topeado'] is not None else 0.0
        ifo_real = float(res['ifo_sistema_real']) if res and res['ifo_sistema_real'] is not None else 0.0

        if ifo_topeado > 95:
            ifo_objetivo = 95.0
        elif ifo_topeado < 90:
            ifo_objetivo = 90.0
        else:
            ifo_objetivo = ifo_topeado

        response_data = {
            "ifo_sistema_mes_anterior": round(ifo_topeado, 2),
            "ifo_sistema_real_mes_anterior": round(ifo_real, 2),
            "ifo_objetivo": round(ifo_objetivo, 2),
            "anio": anio_ant,
            "mes": mes_ant
        }
        baseline_cache[cache_key] = response_data
        return SystemIFOResponse(**response_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculando IFO sistema: {str(e)}")
    finally:
        cursor.close()

@router.get("/parameters-summary/{fecha}", response_model=ParametersIFOResponse)
async def get_parameters_summary(fecha: date, db: DatabaseConnection = Depends(get_db_connection)):
    cursor = db.get_cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT
                f.denominacion,
                p.porc_cumplimiento_minimo,
                p.normativa
            FROM control_metricas.parametros_ifo p
            JOIN control_metricas.franjas_operativas f ON p.id_franja_operativa = f.id_franja
            WHERE p.inicio_vigencia <= %s 
                AND (p.fin_vigencia IS NULL OR p.fin_vigencia >= %s)
            ORDER BY f.denominacion
        """, (fecha, fecha))
        
        parametros = cursor.fetchall()
        if not parametros:
            return ParametersIFOResponse(resumen="No se encontraron par\u00e1metros vigentes.", parametros=[])
        
        franjas_por_porcentaje = {}
        normativa = None
        for p in parametros:
            if normativa is None: normativa = p['normativa']
            porc = p['porc_cumplimiento_minimo']
            if porc not in franjas_por_porcentaje: franjas_por_porcentaje[porc] = []
            franjas_por_porcentaje[porc].append(p['denominacion'])
        
        descripciones = [f"{int(porc)}% en franjas {', '.join(frs)}" for porc, frs in sorted(franjas_por_porcentaje.items())]
        resumen = f"Los incumplimientos para el IFO son sancionables cuando est\u00e1n por debajo del {' y '.join(descripciones)}."
        if normativa: resumen += f" Base legal: {normativa}"
        
        return ParametersIFOResponse(resumen=resumen, parametros=[dict(p) for p in parametros])
    finally:
        cursor.close()

@router.get("/system-ifo-breakdown/{year}/{month}", response_model=SystemIFOBreakdownResponse)
async def get_system_ifo_breakdown(
    year: int, 
    month: int, 
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    try:
        if not (1 <= month <= 12):
            raise HTTPException(status_code=400, detail="Mes inválido")
            
        _, last_day = calendar.monthrange(year, month)
        inicio_mes = date(year, month, 1)
        fin_mes = date(year, month, last_day)
        
        dias_excluidos = {'domingos': [], 'feriados': [], 'atipicos': []}
        current = inicio_mes
        while current <= fin_mes:
            if current.weekday() == 6: dias_excluidos['domingos'].append(str(current))
            current += timedelta(days=1)
        
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (inicio_mes, fin_mes))
        dias_excluidos['feriados'] = [str(row['fecha']) for row in cursor.fetchall()]
        
        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (inicio_mes, fin_mes))
        dias_excluidos['atipicos'] = [str(row['fecha']) for row in cursor.fetchall()]
        
        query_eots = """
        WITH ifo_diario AS (
            SELECT h.id_eot_vmt_hex, h.fecha, AVG(h.ifo) as ifo_dia, LEAST(AVG(h.ifo), 1.1) as ifo_dia_topeado
            FROM control_metricas.ifo_historico h
            WHERE h.fecha >= %s AND h.fecha <= %s
            GROUP BY h.id_eot_vmt_hex, h.fecha
        ),
        ifo_mensual_eot AS (
            SELECT id_eot_vmt_hex, AVG(ifo_dia) * 100 as ifo_mensual, AVG(ifo_dia_topeado) * 100 as ifo_mensual_topeado, COUNT(DISTINCT fecha) as dias_validos
            FROM ifo_diario
            GROUP BY id_eot_vmt_hex
        )
        SELECT e.id_eot_vmt_hex, e.eot_nombre, COALESCE(i.ifo_mensual, 0) as ifo_mensual, COALESCE(i.ifo_mensual_topeado, 0) as ifo_mensual_topeado, COALESCE(i.dias_validos, 0) as dias_validos
        FROM public.eots e
        LEFT JOIN ifo_mensual_eot i ON e.id_eot_vmt_hex = i.id_eot_vmt_hex
        WHERE e.cod_catalogo NOT IN (72)
        AND e.permisionario IS TRUE
        ORDER BY e.eot_nombre;
        """
        cursor.execute(query_eots, (inicio_mes, fin_mes))
        eots_data = cursor.fetchall()
        
        eots_list, ifo_values, ifo_topeado_values = [], [], []
        for row in eots_data:
            if row['dias_validos'] > 0:
                eot_ifo = EOTMonthlyIFO(
                    id_eot_vmt_hex=row['id_eot_vmt_hex'],
                    eot_nombre=row['eot_nombre'],
                    ifo_mensual=round(float(row['ifo_mensual']), 2),
                    ifo_mensual_topeado=round(float(row['ifo_mensual_topeado']), 2),
                    dias_validos=int(row['dias_validos'])
                )
                eots_list.append(eot_ifo)
                ifo_values.append(eot_ifo.ifo_mensual)
                ifo_topeado_values.append(eot_ifo.ifo_mensual_topeado)
        
        ifo_sistema = sum(ifo_values) / len(ifo_values) if ifo_values else 0.0
        ifo_sistema_topeado = sum(ifo_topeado_values) / len(ifo_topeado_values) if ifo_topeado_values else 0.0
        umbral_obligatorio = max(90.0, min(95.0, ifo_sistema_topeado))
            
        cursor.execute("""
            WITH ifo_diario_eot AS (
                SELECT h.id_eot_vmt_hex, h.fecha, AVG(h.ifo) as ifo_dia_real
                FROM control_metricas.ifo_historico h
                WHERE h.fecha >= %s AND h.fecha <= %s
                GROUP BY h.id_eot_vmt_hex, h.fecha
            )
            SELECT fecha, AVG(ifo_dia_real) * 100 as promedio, MIN(ifo_dia_real) * 100 as minimo, MAX(ifo_dia_real) * 100 as maximo
            FROM ifo_diario_eot GROUP BY fecha ORDER BY fecha;
        """, (inicio_mes, fin_mes))
        daily_res = cursor.fetchall()
        daily_averages = [
            {"fecha": str(row['fecha']), "promedio": round(float(row['promedio']), 2), "minimo": round(float(row['minimo']), 2), "maximo": round(float(row['maximo']), 2)} 
            for row in daily_res
        ]

        return SystemIFOBreakdownResponse(
            year=year, month=month, ifo_sistema=round(ifo_sistema, 2), 
            ifo_sistema_topeado=round(ifo_sistema_topeado, 2), total_eots=len(eots_list), 
            eots=eots_list, umbral_obligatorio_mes_siguiente=round(umbral_obligatorio, 2),
            dias_excluidos=dias_excluidos, daily_averages=daily_averages
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@router.get("/advanced-daily-report/{fecha}", response_model=AdvancedDailyReportResponse)
async def get_advanced_daily_report(fecha: date, db: DatabaseConnection = Depends(get_db_connection)):
    cursor = db.get_cursor()
    try:
        baseline = await get_system_ifo_baseline(fecha, db)
        query_ranking = """
        SELECT e.id_eot_vmt_hex, e.eot_nombre, LEAST(AVG(h.ifo), 1.1) * 100 as ifo_dia
        FROM public.eots e JOIN control_metricas.ifo_historico h ON e.id_eot_vmt_hex = h.id_eot_vmt_hex
        WHERE h.fecha = %s AND e.cod_catalogo NOT IN (72)
        GROUP BY e.id_eot_vmt_hex, e.eot_nombre ORDER BY ifo_dia DESC;
        """
        cursor.execute(query_ranking, (fecha,))
        ranking_res = cursor.fetchall()
        ranking_eots = [{"name": r["eot_nombre"], "ifo": round(float(r["ifo_dia"]), 2), "id_eot_vmt_hex": r["id_eot_vmt_hex"]} for r in ranking_res]
        ifo_sistema = sum(r["ifo"] for r in ranking_eots) / len(ranking_eots) if ranking_eots else 0.0

        td_id = get_tipo_dia_id(fecha)
        query_hourly = """
        SELECT EXTRACT(HOUR FROM f.hora_inicio) as hora, SUM(h.cbd_cantidad) as obs, SUM(p.cbd_minimo_franja) as base
        FROM control_metricas.ifo_historico h
        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
        LEFT JOIN control_metricas.cbd_parametros_minimos p ON h.id_franja = p.id_franja 
            AND p.id_tipo_dia = %s 
            AND (p.vigencia_desde IS NULL OR p.vigencia_desde <= %s)
            AND (p.vigencia_hasta IS NULL OR p.vigencia_hasta >= %s)
        WHERE h.fecha = %s GROUP BY 1 ORDER BY 1;
        """
        cursor.execute(query_hourly, (td_id, fecha, fecha, fecha))
        hourly_res = cursor.fetchall()
        buses_by_hour = []
        for r in hourly_res:
            obs, base = int(r["obs"]), int(r["base"])
            buses_by_hour.append({
                "hour": int(r["hora"]), "real": obs, "base": base, 
                "ifo": round((obs / base * 100) if base > 0 else 0.0, 2), "diff": obs - base
            })

        # 3. Detalles por Franja para TODAS las EOTs (Una sola query rápida)
        cursor.execute("""
            SELECT e.id_eot_vmt_hex, e.eot_nombre, f.denominacion, h.ifo * 100 as ifo_franja
            FROM control_metricas.ifo_historico h
            JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
            JOIN public.eots e ON h.id_eot_vmt_hex = e.id_eot_vmt_hex
            WHERE h.fecha = %s ORDER BY e.eot_nombre, f.hora_inicio;
        """, (fecha,))
        f_res = cursor.fetchall()
        
        franjas_map = {}
        for row in f_res:
            eot_name = row["eot_nombre"]
            if eot_name not in franjas_map:
                franjas_map[eot_name] = []
            franjas_map[eot_name].append({
                "denominacion": row["denominacion"], 
                "ifo": round(float(row["ifo_franja"]), 2)
            })
        
        franjas_by_eot = [{"eot": name, "franjas": frs} for name, frs in franjas_map.items()]

        return AdvancedDailyReportResponse(
            fecha=fecha, ifo_sistema=round(ifo_sistema, 2), ifo_objetivo=round(baseline.ifo_objetivo, 2),
            total_buses=sum(b["real"] for b in buses_by_hour), ranking_eots=ranking_eots,
            buses_by_hour=buses_by_hour, franjas_by_eot=franjas_by_eot
        )
    finally:
        cursor.close()

@router.get("/eot-monthly-breakdown/{eot_id}/{year}/{month}")
async def get_eot_monthly_breakdown(eot_id: str, year: int, month: int, db: DatabaseConnection = Depends(get_db_connection)):
    cursor = db.get_cursor()
    try:
        _, last_day = calendar.monthrange(year, month)
        inicio, fin = date(year, month, 1), date(year, month, last_day)
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (inicio, fin))
        feriados = {str(row['fecha']) for row in cursor.fetchall()}
        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (inicio, fin))
        atipicos = {str(row['fecha']) for row in cursor.fetchall()}
        cursor.execute("""
            SELECT h.fecha, f.id_franja, f.denominacion, AVG(h.ifo) * 100 as ifo_franja
            FROM control_metricas.ifo_historico h
            JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
            WHERE h.id_eot_vmt_hex = %s AND h.fecha BETWEEN %s AND %s
            GROUP BY 1, 2, 3 ORDER BY 1, 2;
        """, (eot_id, inicio, fin))
        rows, breakdown = cursor.fetchall(), {}
        for row in rows:
            fs = str(row['fecha'])
            if fs not in breakdown:
                _, adjustments = get_factores_ajuste_acumulados(cursor, row['fecha'])
                breakdown[fs] = {"fecha": fs, "es_excluido": False, "ajustes": adjustments, "ifo_dia": 0, "franjas": [], "motivo_exclusion": "Domingo" if row['fecha'].weekday() == 6 else "Feriado" if fs in feriados else "Atípico" if fs in atipicos else None}
            breakdown[fs]["franjas"].append({"id_franja": row['id_franja'], "denominacion": row['denominacion'], "ifo": round(float(row['ifo_franja']), 2)})
        for info in breakdown.values():
            if info["franjas"]:
                # Topear cada día al 110% según Res. 120
                info["ifo_dia"] = round(min(sum(f["ifo"] for f in info["franjas"]) / len(info["franjas"]), 110.0), 2)
        return sorted(breakdown.values(), key=lambda x: x["fecha"])
    finally:
        cursor.close()
