"""Rutas para obtener desglose detallado de métricas CBD e IFO."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, timedelta
import math
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/performance-detail", tags=["Performance Detail"])


class CBDDetailRequest(BaseModel):
    """Solicitud para desglose de CBD."""
    fecha: date
    eot_id: int
    id_franja: int


class CBDHoraData(BaseModel):
    """Datos de CBD por hora."""
    hora: int
    cbd_observado: int
    cbd_minimo_hora: int
    ratio_hora: float  # min(cbd_observado/cbd_minimo_hora, 1)


class CBDDetailResponse(BaseModel):
    """Respuesta con desglose de CBD por franja."""
    fecha: date
    eot_id: int
    eot_nombre: str
    id_franja: int
    denominacion_franja: str
    cbd_minimo_hora: int
    cbd_minimo_franja: int
    horas_data: List[CBDHoraData]
    # Componentes del índice
    promedio_ratio_hora: float  # I_H
    cbd_franja_observado: int  # Suma o promedio de CBD en la franja
    ratio_franja: float  # I_F = min(cbd_franja/cbd_minimo_franja, 1)
    # Índice final
    componente_hora: float  # I_H * 0.7
    componente_franja: float  # I_F * 0.3
    indice_cbd: float  # componente_hora + componente_franja


class IFODetailRequest(BaseModel):
    """Solicitud para desglose de IFO."""
    fecha: date
    eot_id: int
    id_franja: int


class IFOHoraHistorico(BaseModel):
    """Datos históricos por hora para IFO."""
    fecha: date
    cbd_observado: int


class IFOHoraData(BaseModel):
    """Datos de IFO por hora."""
    hora: int
    cbd_dia_analizado: int
    promedio_historico: float
    b_dist_ajustado: float
    historico_detalle: List[IFOHoraHistorico]
    ifo_hora: float  # (cbd_dia / b_dist_ajustado * 100)


class IFOFechaHistorica(BaseModel):
    """Fecha histórica con estado de uso."""
    fecha: date
    usada: bool


class IFODetailResponse(BaseModel):
    """Respuesta con desglose de IFO por franja."""
    fecha: date
    eot_id: int
    eot_nombre: str
    id_franja: int
    denominacion_franja: str
    tipo_dia: str
    ajuste_aplicado: str
    factor_ajuste: float
    # Fechas usadas en el cálculo histórico
    fechas_historicas: List[date]
    fechas_historicas_todas: List[IFOFechaHistorica]
    horas_data: List[IFOHoraData]
    # IFO franja
    ifo_franja: float  # promedio de ifo_hora


def _es_fecha_atipica(cursor, fecha: date) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM control_metricas.dias_atipicos
        WHERE fecha = %s
        LIMIT 1
        """,
        (fecha,)
    )
    return cursor.fetchone() is not None


def _ajustar_fecha_no_atipica(cursor, fecha: date, fechas_usadas: set) -> date:
    fecha_ajustada = fecha
    while _es_fecha_atipica(cursor, fecha_ajustada) or fecha_ajustada in fechas_usadas:
        fecha_ajustada -= timedelta(weeks=1)
    return fecha_ajustada


def _get_fechas_base_referencia(fecha: date) -> list:
    """
    Determina las 4 fechas de referencia para el cálculo de IFO.
    - Enero/Marzo: Usa Noviembre del año anterior.
    - Diciembre: Usa Noviembre del año actual.
    - Resto: Usa las 4 semanas anteriores.
    """
    month = fecha.month
    year = fecha.year
    weekday = fecha.weekday()
    ref_month = None
    ref_year = year
    if month == 1: ref_month = 11; ref_year = year - 1
    elif month == 12: ref_month = 11; ref_year = year
    elif month == 3: ref_month = 11; ref_year = year - 1
    if ref_month:
        fechas = []
        d = date(ref_year, ref_month, 1)
        while d.weekday() != weekday: d += timedelta(days=1)
        while len(fechas) < 4 and d.month == ref_month:
            fechas.append(d)
            d += timedelta(weeks=1)
        if len(fechas) >= 4:
            return fechas[:4]
    return [fecha - timedelta(weeks=i) for i in range(1, 5)]


def get_fechas_referencia(cursor, fecha: date) -> list:
    fechas_base = _get_fechas_base_referencia(fecha)
    fechas_ajustadas = []
    fechas_usadas = set()
    for fecha_ref in fechas_base:
        fecha_ajustada = _ajustar_fecha_no_atipica(cursor, fecha_ref, fechas_usadas)
        fechas_ajustadas.append(fecha_ajustada)
        fechas_usadas.add(fecha_ajustada)
    return fechas_ajustadas


def get_fechas_referencia_detalle(cursor, fecha: date) -> tuple:
    fechas_base = _get_fechas_base_referencia(fecha)
    fechas_ajustadas = []
    fechas_usadas = set()
    detalle = []
    index_map = {}

    def _agregar_detalle(fecha_item: date, usada: bool) -> None:
        if fecha_item in index_map:
            idx = index_map[fecha_item]
            if usada and not detalle[idx].usada:
                detalle[idx].usada = True
            return
        index_map[fecha_item] = len(detalle)
        detalle.append(IFOFechaHistorica(fecha=fecha_item, usada=usada))

    for fecha_ref in fechas_base:
        fecha_ajustada = _ajustar_fecha_no_atipica(cursor, fecha_ref, fechas_usadas)
        fechas_ajustadas.append(fecha_ajustada)
        fechas_usadas.add(fecha_ajustada)

        if fecha_ajustada == fecha_ref:
            _agregar_detalle(fecha_ref, True)
        else:
            _agregar_detalle(fecha_ref, False)
            _agregar_detalle(fecha_ajustada, True)

    return fechas_ajustadas, detalle


def get_factores_ajuste_acumulados(cursor, fecha: date) -> tuple:
    """
    Calcula los factores de ajuste multiplicativos según Resolución 120/2025.
    Returns: (factor_total, lista_nombres_ajustes)
    """
    factor_total = 1.0; ajustes = []
    month = fecha.month; dia_semana = fecha.weekday()
    if month == 1: factor_total *= 0.80; ajustes.append("Mes Enero (0.80)")
    elif month == 12: factor_total *= 0.80; ajustes.append("Mes Diciembre (0.80)")
    cursor.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (fecha,))
    if cursor.fetchone():
        if dia_semana == 5: factor_total *= 0.50; ajustes.append("Feriado Sábado (0.50)")
        else: factor_total *= 0.30; ajustes.append("Feriado Laboral (0.30)")
    else:
        fecha_ant = fecha - timedelta(days=1); fecha_sig = fecha + timedelta(days=1)
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha IS NOT NULL AND (fecha = %s OR fecha = %s)", (fecha_ant, fecha_sig))
        feriados_cercanos = cursor.fetchall()
        pre = any(f[0] == fecha_sig if isinstance(f, (list, tuple)) else f['fecha'] == fecha_sig for f in feriados_cercanos)
        post = any(f[0] == fecha_ant if isinstance(f, (list, tuple)) else f['fecha'] == fecha_ant for f in feriados_cercanos)
        if post: factor_total *= 0.70; ajustes.append("Post-Feriado (0.70)")
        if pre: factor_total *= 0.70; ajustes.append("Pre-Feriado (0.70)")
    cursor.execute("SELECT mm_caidos FROM control_metricas.t_casuisticas_lluvia WHERE fecha_evento=%s AND mm_caidos > 5 ORDER BY mm_caidos DESC LIMIT 1", (fecha,))
    lluvia = cursor.fetchone()
    if lluvia:
        factor_total *= 0.50
        precipitacion = lluvia['mm_caidos'] if isinstance(lluvia, dict) else lluvia[0]
        ajustes.append(f"Lluvia {precipitacion}mm (0.50)")
    return round(factor_total, 2), ajustes


@router.post("/cbd", response_model=CBDDetailResponse)
async def get_cbd_detail(
    request: CBDDetailRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtener desglose detallado del cálculo del Índice de CBD para una franja.
    Muestra cómo se calcula: 0.7 * promedio(CBD_hora/CBD_min_hora) + 0.3 * (CBD_franja/CBD_min_franja)
    """
    cursor = db.get_cursor()
    
    try:
        # 1. Obtener info del EOT
        cursor.execute("""
            SELECT eot_id, cod_catalogo, eot_nombre, id_eot_vmt_hex 
            FROM public.eots 
            WHERE cod_catalogo = %s
            AND cod_catalogo NOT IN (72)
        """, (request.eot_id,))
        eot_info = cursor.fetchone()
        if not eot_info:
            raise HTTPException(status_code=404, detail="EOT no encontrado")
        
        internal_eot_id = eot_info['eot_id']
        
        # 2. Obtener info de la franja
        cursor.execute("""
            SELECT id_franja, denominacion, hora_inicio, hora_fin
            FROM control_metricas.franjas_operativas
            WHERE id_franja = %s
        """, (request.id_franja,))
        franja_info = cursor.fetchone()
        if not franja_info:
            raise HTTPException(status_code=404, detail="Franja no encontrada")
        
        hora_inicio = franja_info['hora_inicio'].hour
        hora_fin = franja_info['hora_fin'].hour
        
        # 3. Obtener parámetros mínimos
        cursor.execute("""
            SELECT cbd_minimo_hora, cbd_minimo_franja
            FROM control_metricas.cbd_parametros_minimos
            WHERE id_franja = %s
              AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
              AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
            LIMIT 1
        """, (request.id_franja, request.fecha, request.fecha))
        params = cursor.fetchone()
        if not params:
            raise HTTPException(status_code=404, detail="Parámetros mínimos no encontrados")
        
        cbd_min_hora = params['cbd_minimo_hora']
        cbd_min_franja = params['cbd_minimo_franja']
        
        # 4. Obtener CBD observado por hora (combinando validaciones y GPS)
        horas_data = []
        total_cbd_franja = 0
        sum_ratios = 0
        count_horas = 0
        
        for hora in range(hora_inicio, hora_fin + 1):  # +1 para incluir hora_fin (ej: 03:00-04:59 = horas 3 y 4)
            # 1. Primero consultar CBD de validaciones (servicios_diarios)
            cursor.execute("""
                SELECT COUNT(DISTINCT idsam) as cbd
                FROM public.servicios_diarios
                WHERE id_eot_catalogo = %s AND fecha = %s AND hora = %s
            """, (request.eot_id, request.fecha, hora))
            cbd_val = cursor.fetchone()['cbd'] or 0
            
            # 2. Solo si no cumple con el mínimo, consultar GPS
            cbd_observado = cbd_val
            if cbd_val < cbd_min_hora and eot_info['id_eot_vmt_hex']:
                cursor.execute("""
                    SELECT COUNT(DISTINCT mean_id) as cbd
                    FROM control_metricas.cbd_detalle_buses
                    WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora = %s
                """, (eot_info['id_eot_vmt_hex'], request.fecha, hora))
                cbd_gps = cursor.fetchone()['cbd'] or 0
                
                # Solo usar GPS si tiene MÁS datos que billetaje
                if cbd_gps > cbd_val:
                    cbd_observado = cbd_gps
                # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
            
            # Calcular ratio (capped at 1)
            ratio = min(cbd_observado / cbd_min_hora, 1.0) if cbd_min_hora > 0 else 0
            
            horas_data.append(CBDHoraData(
                hora=hora,
                cbd_observado=cbd_observado,
                cbd_minimo_hora=cbd_min_hora,
                ratio_hora=round(ratio, 4)
            ))
            
            total_cbd_franja += cbd_observado
            sum_ratios += ratio
            count_horas += 1
        
        # 5. Calcular componentes del índice
        promedio_ratio_hora = sum_ratios / count_horas if count_horas > 0 else 0
        I_H = min(promedio_ratio_hora, 1.0)
        
        # CBD Franja: contar buses DISTINTOS en TODA la franja (no promedio)
        # Primero intentamos con validaciones
        cursor.execute("""
            SELECT COUNT(DISTINCT idsam) as cbd
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = %s 
              AND fecha = %s 
              AND hora >= %s AND hora <= %s
        """, (request.eot_id, request.fecha, hora_inicio, hora_fin))
        cbd_franja_val = cursor.fetchone()['cbd'] or 0
        
        # Si no cumple el mínimo, consultar GPS
        cbd_franja_observado = cbd_franja_val
        if cbd_franja_val < cbd_min_franja and eot_info['id_eot_vmt_hex']:
            cursor.execute("""
                SELECT COUNT(DISTINCT mean_id) as cbd
                FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = %s 
                  AND fecha = %s 
                  AND hora >= %s AND hora <= %s
            """, (eot_info['id_eot_vmt_hex'], request.fecha, hora_inicio, hora_fin))
            cbd_franja_gps = cursor.fetchone()['cbd'] or 0
            # Solo usar GPS si tiene MÁS datos que billetaje
            if cbd_franja_gps > cbd_franja_val:
                cbd_franja_observado = cbd_franja_gps
            # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
        
        ratio_franja = min(cbd_franja_observado / cbd_min_franja, 1.0) if cbd_min_franja > 0 else 0
        I_F = ratio_franja
        
        componente_hora = I_H * 0.7
        componente_franja = I_F * 0.3
        indice_cbd = componente_hora + componente_franja
        
        return CBDDetailResponse(
            fecha=request.fecha,
            eot_id=request.eot_id,
            eot_nombre=eot_info['eot_nombre'],
            id_franja=request.id_franja,
            denominacion_franja=franja_info['denominacion'],
            cbd_minimo_hora=cbd_min_hora,
            cbd_minimo_franja=cbd_min_franja,
            horas_data=horas_data,
            promedio_ratio_hora=round(I_H, 4),
            cbd_franja_observado=cbd_franja_observado,
            ratio_franja=round(I_F, 4),
            componente_hora=round(componente_hora, 4),
            componente_franja=round(componente_franja, 4),
            indice_cbd=round(indice_cbd, 4)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en CBD detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()


@router.post("/ifo", response_model=IFODetailResponse)
async def get_ifo_detail(
    request: IFODetailRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtener desglose detallado del cálculo del IFO para una franja.
    Muestra: IFO_hora = CBD_hora / promedio(CBD_hora de 4 semanas anteriores del mismo día)
    IFO_franja = promedio(IFO_hora)
    """
    cursor = db.get_cursor()
    
    try:
        # 1. Obtener info del EOT
        cursor.execute("""
            SELECT eot_id, cod_catalogo, eot_nombre, id_eot_vmt_hex 
            FROM public.eots 
            WHERE cod_catalogo = %s
        """, (request.eot_id,))
        eot_info = cursor.fetchone()
        if not eot_info:
            raise HTTPException(status_code=404, detail="EOT no encontrado")
        
        # 2. Obtener info de la franja
        cursor.execute("""
            SELECT id_franja, denominacion, hora_inicio, hora_fin
            FROM control_metricas.franjas_operativas
            WHERE id_franja = %s
        """, (request.id_franja,))
        franja_info = cursor.fetchone()
        if not franja_info:
            raise HTTPException(status_code=404, detail="Franja no encontrada")
        
        hora_inicio = franja_info['hora_inicio'].hour
        hora_fin = franja_info['hora_fin'].hour
        
        # 3. Determinar tipo de día y factores de ajuste (Resolución 120/2025)
        fechas_historicas, fechas_historicas_todas = get_fechas_referencia_detalle(cursor, request.fecha)
        factor_ajuste, lista_ajustes = get_factores_ajuste_acumulados(cursor, request.fecha)
        ajuste_aplicado = ", ".join(lista_ajustes) if lista_ajustes else 'Ninguno'
        factor_ajuste = round(factor_ajuste, 2)
        
        # Determinar tipo de día (solo para visualización)
        dia_semana = request.fecha.weekday()
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (request.fecha,))
        if cursor.fetchone(): tipo_dia = 'FERIADO'
        elif dia_semana == 5: tipo_dia = 'SABADO'
        elif dia_semana == 6: tipo_dia = 'DOMINGO'
        else: tipo_dia = 'LABORAL'
        
        # 5. Obtener parámetros mínimos para determinar si se necesita consultar GPS
        cursor.execute("""
            SELECT cbd_minimo_hora
            FROM control_metricas.cbd_parametros_minimos
            WHERE id_franja = %s
              AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
              AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
            LIMIT 1
        """, (request.id_franja, request.fecha, request.fecha))
        params = cursor.fetchone()
        cbd_min_hora = params['cbd_minimo_hora'] if params else 0
        
        # 6. Calcular IFO por hora
        horas_data = []
        sum_ifo = 0
        count_horas = 0
        
        for hora in range(hora_inicio, hora_fin + 1):  # +1 para incluir hora_fin
            # 1. Primero consultar CBD de validaciones (servicios_diarios)
            cursor.execute("""
                SELECT COUNT(DISTINCT idsam) as cbd
                FROM public.servicios_diarios
                WHERE id_eot_catalogo = %s AND fecha = %s AND hora = %s
            """, (request.eot_id, request.fecha, hora))
            cbd_val = cursor.fetchone()['cbd'] or 0
            
            # 2. Solo si no cumple con el mínimo, consultar GPS
            cbd_dia = cbd_val
            if cbd_val < cbd_min_hora and eot_info['id_eot_vmt_hex']:
                cursor.execute("""
                    SELECT COUNT(DISTINCT mean_id) as cbd
                    FROM control_metricas.cbd_detalle_buses
                    WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora = %s
                """, (eot_info['id_eot_vmt_hex'], request.fecha, hora))
                cbd_gps = cursor.fetchone()['cbd'] or 0
                
                # Solo usar GPS si tiene MÁS datos que billetaje
                if cbd_gps > cbd_val:
                    cbd_dia = cbd_gps
                # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
            
            # Histórico: CBD de las 4 semanas anteriores (usando misma lógica)
            historico_detalle = []
            sum_historico = 0
            count_historico = 0
            
            for fecha_hist in fechas_historicas:
                # Primero validaciones
                cursor.execute("""
                    SELECT COUNT(DISTINCT idsam) as cbd
                    FROM public.servicios_diarios
                    WHERE id_eot_catalogo = %s AND fecha = %s AND hora = %s
                """, (request.eot_id, fecha_hist, hora))
                cbd_hist_val = cursor.fetchone()['cbd'] or 0
                
                # Solo si no cumple, consultar GPS
                cbd_hist = cbd_hist_val
                if cbd_hist_val < cbd_min_hora and eot_info['id_eot_vmt_hex']:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT mean_id) as cbd
                        FROM control_metricas.cbd_detalle_buses
                        WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora = %s
                    """, (eot_info['id_eot_vmt_hex'], fecha_hist, hora))
                    cbd_hist_gps = cursor.fetchone()['cbd'] or 0
                    # Solo usar GPS si tiene MÁS datos que billetaje
                    if cbd_hist_gps > cbd_hist_val:
                        cbd_hist = cbd_hist_gps
                    # Si GPS tiene menos o igual, usar billetaje (aunque no cumpla mínimo)
                
                historico_detalle.append(IFOHoraHistorico(
                    fecha=fecha_hist,
                    cbd_observado=cbd_hist
                ))
                
                sum_historico += cbd_hist
                count_historico += 1
            
            promedio_historico_raw = sum_historico / count_historico if count_historico > 0 else 0
            
            # Aplicar factor de ajuste y mantener 2 decimales (Sin redondeo al entero superior)
            promedio_ajustado = round(max(promedio_historico_raw * factor_ajuste, cbd_min_hora), 2)
            
            # IFO hora (sin tope del 100%)
            ifo_hora = (cbd_dia / promedio_ajustado * 100) if promedio_ajustado > 0 else 0
            
            horas_data.append(IFOHoraData(
                hora=hora,
                cbd_dia_analizado=cbd_dia,
                promedio_historico=round(promedio_historico_raw, 2),
                b_dist_ajustado=promedio_ajustado,
                historico_detalle=historico_detalle,
                ifo_hora=round(ifo_hora, 2)
            ))
            
            sum_ifo += ifo_hora
            count_horas += 1
        
        # 6. IFO franja = promedio de IFO hora
        ifo_franja = sum_ifo / count_horas if count_horas > 0 else 0
        
        return IFODetailResponse(
            fecha=request.fecha,
            eot_id=request.eot_id,
            eot_nombre=eot_info['eot_nombre'],
            id_franja=request.id_franja,
            denominacion_franja=franja_info['denominacion'],
            tipo_dia=tipo_dia,
            ajuste_aplicado=ajuste_aplicado,
            factor_ajuste=factor_ajuste,
            fechas_historicas=fechas_historicas,
            fechas_historicas_todas=fechas_historicas_todas,
            horas_data=horas_data,
            ifo_franja=round(ifo_franja, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en IFO detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
