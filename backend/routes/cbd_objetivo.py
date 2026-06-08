from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import date, timedelta, time
from pydantic import BaseModel
from database.connection import DatabaseConnection, get_db_connection
from .performance import get_fechas_referencia, get_factores_ajuste_acumulados
import math

router = APIRouter(prefix="/api/cbd-objetivo", tags=["CBD Objetivo"])

class CBDObjetivoRequest(BaseModel):
    eot_id: int

class FranjaMetadata(BaseModel):
    id_franja: int
    denominacion: str
    hora_inicio: int
    hora_fin: int

class CBDObjetivoResponse(BaseModel):
    eot_id: int
    eot_nombre: str
    fechas: List[date]
    horas_label: List[int]
    franjas_metadata: Dict[str, List[FranjaMetadata]] # fecha -> list of franjas
    datos: Dict[str, Dict[str, Any]] # fecha -> { "horas": { "4": 5 }, "franjas": { "101": 12 } }

def get_tipo_dia_and_franjas(cursor, fecha: date) -> tuple:
    cursor.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (fecha,))
    es_feriado = cursor.fetchone() is not None
    dia_semana = fecha.weekday()
    if es_feriado or dia_semana == 6:
        id_tipo_dia, tipo_dia = 7, 'FERIADO' if es_feriado else 'NO LABORAL'
    elif dia_semana == 5:
        id_tipo_dia, tipo_dia = 6, 'SABADO'
    else:
        id_tipo_dia, tipo_dia = 5, 'LABORAL'
    
    cursor.execute("""
        SELECT id_franja, denominacion, hora_inicio, hora_fin
        FROM control_metricas.franjas_operativas
        WHERE id_tipo_dia = %s
          AND (inicio_vigencia IS NULL OR inicio_vigencia <= %s)
          AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
        ORDER BY hora_inicio
    """, (id_tipo_dia, fecha, fecha))
    franjas = cursor.fetchall()
    return id_tipo_dia, tipo_dia, franjas

@router.post("", response_model=CBDObjetivoResponse)
async def get_cbd_objetivo_report(
    request: CBDObjetivoRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    cursor = db.get_cursor()
    
    try:
        # 1. Obtener info de la EOT
        cursor.execute("SELECT eot_nombre, id_eot_vmt_hex FROM public.eots WHERE cod_catalogo = %s", (request.eot_id,))
        eot = cursor.fetchone()
        if not eot:
            raise HTTPException(status_code=404, detail="EOT no encontrada")
        
        eot_nombre = eot['eot_nombre']
        eot_vmt_hex = eot['id_eot_vmt_hex']
        
        # 2. Determinar ventana de fechas
        cursor.execute("SELECT MAX(fecha) as max_date FROM public.servicios_diarios")
        res = cursor.fetchone()
        last_date = res['max_date'] if res and res['max_date'] else date.today()
            
        start_date = last_date + timedelta(days=1)
        fechas_objetivo = [start_date + timedelta(days=i) for i in range(7)]
        
        # 3. Preparar respuesta
        resultado_datos = {}
        franjas_metadata_por_fecha = {}
        horas_labels = list(range(4, 24))
        
        # Colectar fechas históricas para precarga
        todas_fechas_historicas = set()
        for f in fechas_objetivo:
            todas_fechas_historicas.update(get_fechas_referencia(cursor, f))
        list_fechas_todas = list(todas_fechas_historicas)
        
        # Cache de Billetaje
        cursor.execute("""
            SELECT fecha, hora, COUNT(DISTINCT idsam) as cbd
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = %s AND fecha = ANY(%s)
            GROUP BY fecha, hora
        """, (request.eot_id, list_fechas_todas))
        cache_val = {(r['fecha'], r['hora']): r['cbd'] for r in cursor.fetchall()}
        
        # Cache de GPS
        cache_gps = {}
        if eot_vmt_hex:
            cursor.execute("""
                SELECT fecha, hora, COUNT(DISTINCT mean_id) as cbd
                FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = %s AND fecha = ANY(%s)
                GROUP BY fecha, hora
            """, (eot_vmt_hex, list_fechas_todas))
            cache_gps = {(r['fecha'], r['hora']): r['cbd'] for r in cursor.fetchall()}

        for fecha in fechas_objetivo:
            fecha_str = fecha.strftime("%Y-%m-%d")
            resultado_datos[fecha_str] = {"horas": {}, "franjas": {}}
            
            id_tipo_dia, tipo_dia, franjas = get_tipo_dia_and_franjas(cursor, fecha)
            fechas_ref = get_fechas_referencia(cursor, fecha)
            factor_ajuste, _ = get_factores_ajuste_acumulados(cursor, fecha)
            
            # Metadata de franjas para el frontend
            franjas_metadata_por_fecha[fecha_str] = [
                FranjaMetadata(
                    id_franja=f['id_franja'],
                    denominacion=f['denominacion'],
                    hora_inicio=f['hora_inicio'].hour,
                    hora_fin=f['hora_fin'].hour
                ) for f in franjas
            ]

            # Obtener parámetros mínimos
            cursor.execute("""
                SELECT id_franja, cbd_minimo_hora, cbd_minimo_franja 
                FROM control_metricas.cbd_parametros_minimos 
                WHERE id_tipo_dia = %s
                AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
                AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
            """, (id_tipo_dia, fecha, fecha))
            params = {r['id_franja']: r for r in cursor.fetchall()}
            
            # --- CALCULO POR HORA ---
            for hora in horas_labels:
                min_h = 0
                for fr in franjas:
                    if fr['hora_inicio'].hour <= hora <= fr['hora_fin'].hour:
                        min_h = params.get(fr['id_franja'], {}).get('cbd_minimo_hora', 0) or 0
                        break
                
                sum_hora = 0
                for fh in fechas_ref:
                    c_val = cache_val.get((fh, hora), 0)
                    c_gps = cache_gps.get((fh, hora), 0)
                    cbd_h = c_val
                    if eot_vmt_hex and c_gps > cbd_h:
                        cbd_h = c_gps
                    sum_hora += cbd_h
                
                promedio = sum_hora / len(fechas_ref) if fechas_ref else 0
                resultado_datos[fecha_str]["horas"][str(hora)] = math.ceil(max(promedio * factor_ajuste, min_h))
            
            # --- CALCULO POR FRANJA ---
            for fr in franjas:
                fr_id = fr['id_franja']
                p = params.get(fr_id, {'cbd_minimo_franja': 0})
                min_f = p['cbd_minimo_franja'] or 0
                sum_distintos = 0
                h_ini, h_fin = fr['hora_inicio'].hour, fr['hora_fin'].hour

                for fh in fechas_ref:
                    # Billetaje
                    cursor.execute("""
                        SELECT COUNT(DISTINCT idsam) as cbd FROM public.servicios_diarios
                        WHERE id_eot_catalogo = %s AND fecha = %s AND hora >= %s AND hora <= %s
                    """, (request.eot_id, fh, h_ini, h_fin))
                    cbd_dist_val = cursor.fetchone()['cbd'] or 0
                    
                    cbd_final = cbd_dist_val
                    if eot_vmt_hex:
                        cursor.execute("""
                            SELECT COUNT(DISTINCT mean_id) as cbd FROM control_metricas.cbd_detalle_buses
                            WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora >= %s AND hora <= %s
                        """, (eot_vmt_hex, fh, h_ini, h_fin))
                        cbd_dist_gps = cursor.fetchone()['cbd'] or 0
                        if cbd_dist_gps > cbd_dist_val:
                            cbd_final = cbd_dist_gps
                    sum_distintos += cbd_final
                
                promedio = sum_distintos / len(fechas_ref) if fechas_ref else 0
                resultado_datos[fecha_str]["franjas"][str(fr_id)] = math.ceil(max(promedio * factor_ajuste, min_f))

        return CBDObjetivoResponse(
            eot_id=request.eot_id,
            eot_nombre=eot_nombre,
            fechas=fechas_objetivo,
            horas_label=horas_labels,
            franjas_metadata=franjas_metadata_por_fecha,
            datos=resultado_datos
        )

    except Exception as e:
        import traceback
        print(f"Error en CBD Objetivo: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
