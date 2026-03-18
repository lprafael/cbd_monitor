from fastapi import APIRouter, HTTPException, Depends
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
import calendar
from database.connection import DatabaseConnection, get_db_connection
from models.report_schemas import (
    MonthlyReportRequest, MonthlyReportResponse, 
    SystemIFOResponse, ParametersIFOResponse,
    TipoDiaReport, FranjaInfo, DiaData,
    SystemIFOBreakdownResponse, EOTMonthlyIFO
)
from .performance import get_factores_ajuste_acumulados

router = APIRouter(prefix="/api/reports/res120", tags=["Reports Resolution 120/2025"])

def get_tipo_dia_id(fecha_obj: date, feriados_set: Optional[set] = None) -> int:
    """
    Determinar el id_tipo_dia basado en la fecha (5=LABORAL, 6=SABADO, 7=NO LABORAL).
    Si feriados_set está definido, las fechas en ese conjunto se consideran NO LABORAL (7).
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
    """
    Obtiene los datos mensuales de IFO para un EOT.
    Migrado desde el script enviar_informe.py para centralizar la l\u00f3gica.
    """
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
        
        # 1. Obtener franjas para cada tipo de d\u00eda
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

        # Feriados del mes (para clasificar como Domingo/Feriado)
        cursor.execute(
            "SELECT fecha FROM public.feriados WHERE fecha >= %s AND fecha <= %s",
            (primer_dia_mes, fecha_referencia)
        )
        feriados_set = {str(row['fecha']) for row in cursor.fetchall()}

        # 2. Inicializar todas las fechas del mes
        fecha_actual = primer_dia_mes
        while fecha_actual <= fecha_referencia:
            td_id = get_tipo_dia_id(fecha_actual, feriados_set)
            if td_id in tipos_dia_info:
                tipos_dia_info[td_id]['dias'][str(fecha_actual)] = {'franjas': {}, 'ifo_diario': None}
            fecha_actual += timedelta(days=1)

        # 3. Obtener datos de IFO del mes
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

        # 4. Calcular IFO diario
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

@router.get("/system-ifo-baseline/{fecha}", response_model=SystemIFOResponse)
async def get_system_ifo_baseline(fecha: date, db: DatabaseConnection = Depends(get_db_connection)):
    """
    Calcula el IFO del sistema del mes anterior siguiendo la jerarquía correcta:
    1. IFO Franja (ya está en la tabla)
    2. IFO Día = Promedio de IFO Franja por día
    3. IFO Mensual EOT = Promedio de IFO Día
    4. IFO Sistema = Promedio de IFO Mensual de todas las EOTs
    """
    cursor = db.get_cursor()
    try:
        # Mes anterior
        if fecha.month == 1:
            mes_ant, anio_ant = 12, fecha.year - 1
        else:
            mes_ant, anio_ant = fecha.month - 1, fecha.year
            
        _, last_day = calendar.monthrange(anio_ant, mes_ant)
        inicio_mes_ant = date(anio_ant, mes_ant, 1)
        fin_mes_ant = date(anio_ant, mes_ant, last_day)
        
        # Query corregido siguiendo la jerarquía correcta
        query = """
        WITH ifo_diario AS (
            -- Paso 1: Calcular IFO Diario = Promedio de IFO Franja por día y EOT
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
            -- Paso 2: Calcular IFO Mensual por EOT = Promedio de IFO Diario
            SELECT 
                i.id_eot_vmt_hex,
                AVG(i.ifo_dia_real) * 100 as ifo_mensual_real,
                AVG(i.ifo_dia_topeado) * 100 as ifo_mensual_topeado
            FROM ifo_diario i
            JOIN public.eots e ON i.id_eot_vmt_hex = e.id_eot_vmt_hex
            WHERE e.cod_catalogo NOT IN (72)
            GROUP BY i.id_eot_vmt_hex
        )
        -- Paso 3: Calcular IFO Sistema = Promedio de IFO Mensual de todas las EOTs
        SELECT 
            AVG(ifo_mensual_real) as ifo_sistema_real,
            AVG(ifo_mensual_topeado) as ifo_sistema_topeado
        FROM ifo_mensual_eot;
        """
        cursor.execute(query, (inicio_mes_ant, fin_mes_ant))
        res = cursor.fetchone()
        
        ifo_topeado = float(res['ifo_sistema_topeado']) if res and res['ifo_sistema_topeado'] is not None else 0.0
        ifo_real = float(res['ifo_sistema_real']) if res and res['ifo_sistema_real'] is not None else 0.0

        # Lógica Res 120/2025 para el IFO Objetivo (Mes n basado en n-1)
        if ifo_topeado > 95:
            ifo_objetivo = 95.0
        elif ifo_topeado < 90:
            ifo_objetivo = 90.0
        else:
            ifo_objetivo = ifo_topeado

        return SystemIFOResponse(
            ifo_sistema_mes_anterior=round(ifo_topeado, 2),
            ifo_sistema_real_mes_anterior=round(ifo_real, 2),
            ifo_objetivo=round(ifo_objetivo, 2),
            anio=anio_ant,
            mes=mes_ant
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculando IFO sistema: {str(e)}")
    finally:
        cursor.close()

@router.get("/parameters-summary/{fecha}", response_model=ParametersIFOResponse)
async def get_parameters_summary(fecha: date, db: DatabaseConnection = Depends(get_db_connection)):
    """Resumen de par\u00e1metros IFO vigentes."""
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
        
        # Agrupar y construir texto (l\u00f3gica similar a la original)
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
    """
    Obtiene el desglose completo del IFO Sistema para un mes específico.
    Muestra el IFO Mensual de cada EOT y el promedio del sistema.
    """
    cursor = db.get_cursor()
    try:
        # Validar mes
        if not (1 <= month <= 12):
            raise HTTPException(status_code=400, detail="Mes inválido (debe estar entre 1 y 12)")
        
        # Calcular rango del mes
        _, last_day = calendar.monthrange(year, month)
        inicio_mes = date(year, month, 1)
        fin_mes = date(year, month, last_day)
        
        # 1. Obtener días excluidos
        dias_excluidos = {
            'domingos': [],
            'feriados': [],
            'atipicos': []
        }
        
        # Domingos
        current = inicio_mes
        while current <= fin_mes:
            if current.weekday() == 6:  # Domingo
                dias_excluidos['domingos'].append(str(current))
            current += timedelta(days=1)
        
        # Feriados
        cursor.execute("""
            SELECT fecha FROM public.feriados 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha
        """, (inicio_mes, fin_mes))
        dias_excluidos['feriados'] = [str(row['fecha']) for row in cursor.fetchall()]
        
        # Días atípicos
        cursor.execute("""
            SELECT fecha FROM control_metricas.dias_atipicos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha
        """, (inicio_mes, fin_mes))
        dias_excluidos['atipicos'] = [str(row['fecha']) for row in cursor.fetchall()]
        
        # 2. Calcular IFO Mensual por EOT
        query_eots = """
        WITH ifo_diario AS (
            -- Paso 1: Calcular IFO Diario = Promedio de IFO Franja por día y EOT
            SELECT 
                h.id_eot_vmt_hex,
                h.fecha,
                AVG(h.ifo) as ifo_dia,
                LEAST(AVG(h.ifo), 1.1) as ifo_dia_topeado
            FROM control_metricas.ifo_historico h
            WHERE h.fecha >= %s AND h.fecha <= %s
            GROUP BY h.id_eot_vmt_hex, h.fecha
        ),
        ifo_mensual_eot AS (
            -- Paso 2: Calcular IFO Mensual por EOT = Promedio de IFO Diario
            SELECT 
                id_eot_vmt_hex,
                AVG(ifo_dia) * 100 as ifo_mensual,
                AVG(ifo_dia_topeado) * 100 as ifo_mensual_topeado,
                COUNT(DISTINCT fecha) as dias_validos
            FROM ifo_diario
            GROUP BY id_eot_vmt_hex
        )
        SELECT 
            e.id_eot_vmt_hex,
            e.eot_nombre,
            COALESCE(i.ifo_mensual, 0) as ifo_mensual,
            COALESCE(i.ifo_mensual_topeado, 0) as ifo_mensual_topeado,
            COALESCE(i.dias_validos, 0) as dias_validos
        FROM public.eots e
        LEFT JOIN ifo_mensual_eot i ON e.id_eot_vmt_hex = i.id_eot_vmt_hex
        WHERE e.cod_catalogo NOT IN (72)
        ORDER BY e.eot_nombre;
        """
        
        cursor.execute(query_eots, (inicio_mes, fin_mes))
        eots_data = cursor.fetchall()
        
        # 3. Construir lista de EOTs y calcular promedios
        eots_list = []
        ifo_values = []
        ifo_topeado_values = []
        
        for row in eots_data:
            if row['dias_validos'] > 0:  # Solo incluir EOTs con datos
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
        
        # 4. Calcular IFO Sistema
        ifo_sistema = sum(ifo_values) / len(ifo_values) if ifo_values else 0.0
        ifo_sistema_topeado = sum(ifo_topeado_values) / len(ifo_topeado_values) if ifo_topeado_values else 0.0
        
        # 5. Calcular Umbral Obligatorio del IFO (Mes n+1)
        # Basado en IFO Sistema Topeado del mes actual (Mes n)
        if ifo_sistema_topeado > 95:
            umbral_obligatorio = 95.0
        elif ifo_sistema_topeado < 90:
            umbral_obligatorio = 90.0
        else:
            umbral_obligatorio = ifo_sistema_topeado
            
        return SystemIFOBreakdownResponse(
            year=year,
            month=month,
            ifo_sistema=round(ifo_sistema, 2),
            ifo_sistema_topeado=round(ifo_sistema_topeado, 2),
            total_eots=len(eots_list),
            eots=eots_list,
            umbral_obligatorio_mes_siguiente=round(umbral_obligatorio, 2),
            dias_excluidos=dias_excluidos
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculando desglose IFO sistema: {str(e)}")
    finally:
        cursor.close()

@router.get("/eot-monthly-breakdown/{eot_id}/{year}/{month}")
async def get_eot_monthly_breakdown(
    eot_id: str,
    year: int,
    month: int,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtiene el desglose diario y por franja de una EOT específica para un mes.
    Identifica días excluidos (domingos, feriados, atípicos).
    """
    cursor = db.get_cursor()
    try:
        _, last_day = calendar.monthrange(year, month)
        inicio_mes = date(year, month, 1)
        fin_mes = date(year, month, last_day)

        # 1. Obtener datos de exclusión
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha BETWEEN %s AND %s", (inicio_mes, fin_mes))
        feriados = {str(row['fecha']) for row in cursor.fetchall()}

        cursor.execute("SELECT fecha FROM control_metricas.dias_atipicos WHERE fecha BETWEEN %s AND %s", (inicio_mes, fin_mes))
        atipicos = {str(row['fecha']) for row in cursor.fetchall()}

        # 2. Obtener IFO por franja y día
        query = """
        SELECT 
            h.fecha,
            f.id_franja,
            f.denominacion,
            AVG(h.ifo) * 100 as ifo_franja
        FROM control_metricas.ifo_historico h
        JOIN control_metricas.franjas_operativas f ON h.id_franja = f.id_franja
        WHERE h.id_eot_vmt_hex = %s AND h.fecha BETWEEN %s AND %s
        GROUP BY h.fecha, f.id_franja, f.denominacion
        ORDER BY h.fecha, f.id_franja;
        """
        cursor.execute(query, (eot_id, inicio_mes, fin_mes))
        rows = cursor.fetchall()

        # Agrupar por día
        breakdown = {}
        for row in rows:
            fecha_str = str(row['fecha'])
            if fecha_str not in breakdown:
                # Determinar si es excluido
                es_domingo = row['fecha'].weekday() == 6
                es_feriado = fecha_str in feriados
                es_atipico = fecha_str in atipicos
                
                # Calcular factores de ajuste
                _, lista_ajustes = get_factores_ajuste_acumulados(cursor, row['fecha'])
                
                breakdown[fecha_str] = {
                    "fecha": fecha_str,
                    "es_excluido": False, # Etapa 1: Todos los días se consideran para el promedio
                    "motivo_exclusion": "Domingo" if es_domingo else "Feriado" if es_feriado else "Atípico" if es_atipico else None,
                    "ajustes": lista_ajustes,
                    "ifo_dia": 0,
                    "franjas": []
                }
            
            breakdown[fecha_str]["franjas"].append({
                "id_franja": row['id_franja'],
                "denominacion": row['denominacion'],
                "ifo": round(float(row['ifo_franja']), 2)
            })

        # Calcular promedio diario por cada día
        for fecha, info in breakdown.items():
            if info["franjas"]:
                info["ifo_dia"] = round(min(sum(f["ifo"] for f in info["franjas"]) / len(info["franjas"]), 110.0), 2)

        return sorted(breakdown.values(), key=lambda x: x["fecha"])

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
