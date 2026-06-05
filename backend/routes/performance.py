"""Rutas para obtener resultados de desempeño diario (CBD e IFO).

Este endpoint calcula los índices en tiempo real a partir de:
1. public.servicios_diarios (datos de validación - prioridad)
2. control_metricas.cbd_detalle_buses (datos GPS - fallback si validaciones < mínimo)
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import date, timedelta
import math
from models.performance_schemas import (
    PerformanceRequest, PerformanceResponse, EOTPerformance, PerformanceResult,
    SaveIFORequest, SaveIFOResponse, IFOHistoricoItem
)
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/performance", tags=["Performance"])


def get_cbd_for_hour(cursor, eot_id: int, eot_vmt_hex: str, fecha, hora: int, cbd_min_hora: int, cache_val: dict = None, cache_gps: dict = None) -> int:
    """
    Obtiene CBD para una hora específica.
    Usa el caché si está disponible, de lo contrario consulta la BD.
    """
    # 1. Consultar validaciones
    if cache_val is not None:
        cbd_val = cache_val.get((eot_id, fecha, hora), 0)
    else:
        cursor.execute("""
            SELECT COUNT(DISTINCT idsam) as cbd
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = %s AND fecha = %s AND hora = %s
        """, (eot_id, fecha, hora))
        res = cursor.fetchone()
        cbd_val = res['cbd'] if res else 0
    
    # 2. Consultar GPS siempre (independientemente de si cumple o no)
    if eot_vmt_hex:
        if cache_gps is not None:
            cbd_gps = cache_gps.get((eot_vmt_hex, fecha, hora), 0)
        else:
            cursor.execute("""
                SELECT COUNT(DISTINCT mean_id) as cbd
                FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora = %s
            """, (eot_vmt_hex, fecha, hora))
            res = cursor.fetchone()
            cbd_gps = res['cbd'] if res else 0
        
        # Tomar siempre el mayor entre validaciones y GPS
        if cbd_gps > cbd_val:
            return cbd_gps
        return cbd_val
    
    return cbd_val


def calculate_cbd_index(cursor, eot_id: int, eot_vmt_hex: str, fecha, franja_info: dict, cbd_min_hora: int, cbd_min_franja: int, cache_val: dict = None, cache_gps: dict = None, cache_franja_val: dict = None, cache_franja_gps: dict = None) -> dict:
    """
    Calcula el índice de cumplimiento CBD para una franja.
    """
    hora_inicio = franja_info['hora_inicio'].hour
    hora_fin = franja_info['hora_fin'].hour
    id_franja = franja_info['id_franja']
    
    sum_ratios = 0
    count_horas = 0
    
    for hora in range(hora_inicio, hora_fin + 1):
        cbd_observado = get_cbd_for_hour(cursor, eot_id, eot_vmt_hex, fecha, hora, cbd_min_hora, cache_val, cache_gps)
        ratio = min(cbd_observado / cbd_min_hora, 1.0) if cbd_min_hora > 0 else 0
        
        sum_ratios += ratio
        count_horas += 1
    
    if count_horas == 0:
        return {'cbd_obs_franja': 0, 'cbd_indice': 0, 'origen': 'Sin datos'}
    
    # Componente I_H: promedio de ratios por hora
    promedio_ratio_hora = sum_ratios / count_horas
    
    # CBD Franja: buses DISTINTOS en la franja
    if cache_franja_val is not None:
        cbd_franja_val = cache_franja_val.get((eot_id, fecha, id_franja), 0)
    else:
        cursor.execute("""
            SELECT COUNT(DISTINCT idsam) as cbd FROM public.servicios_diarios
            WHERE id_eot_catalogo = %s AND fecha = %s AND hora >= %s AND hora <= %s
        """, (eot_id, fecha, hora_inicio, hora_fin))
        res = cursor.fetchone()
        cbd_franja_val = res['cbd'] if res else 0
    
    cbd_franja_observado = cbd_franja_val
    origen_final = 'Validaciones'
    if eot_vmt_hex:
        if cache_franja_gps is not None:
            cbd_franja_gps = cache_franja_gps.get((eot_vmt_hex, fecha, id_franja), 0)
        else:
            cursor.execute("""
                SELECT COUNT(DISTINCT mean_id) as cbd FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora >= %s AND hora <= %s
            """, (eot_vmt_hex, fecha, hora_inicio, hora_fin))
            res = cursor.fetchone()
            cbd_franja_gps = res['cbd'] if res else 0
        
        # Tomar siempre el mayor entre validaciones y GPS
        if cbd_franja_gps > cbd_franja_val:
            cbd_franja_observado = cbd_franja_gps
            origen_final = 'GPS'
    
    ratio_franja = min(cbd_franja_observado / cbd_min_franja, 1.0) if cbd_min_franja > 0 else 0
    indice_cbd = (promedio_ratio_hora * 0.7) + (ratio_franja * 0.3)
    
    return {
        'cbd_obs_franja': cbd_franja_observado,
        'cbd_indice': indice_cbd,
        'origen': origen_final
    }


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
    original = fecha
    while _es_fecha_atipica(cursor, fecha_ajustada) or fecha_ajustada in fechas_usadas:
        fecha_ajustada -= timedelta(weeks=1)
    
    if fecha_ajustada != original:
        print(f"  [INFO] Fecha referencia ajustada: {original} -> {fecha_ajustada} (Atípica o Repetida)")
        
    return fecha_ajustada


def get_fechas_referencia(cursor, fecha: date) -> list:
    """
    Determina las 4 fechas de referencia para el cálculo de IFO.
    - Enero/Marzo: Usa Noviembre del año anterior.
    - Diciembre: Usa Noviembre del año actual.
    - Resto: Usa las 4 semanas anteriores.
    """
    month = fecha.month
    year = fecha.year
    weekday = fecha.weekday()
    
    # Determinar mes de referencia para meses atípicos
    ref_month = None
    ref_year = year
    
    if month == 1: # Enero
        ref_month = 11
        ref_year = year - 1
    elif month == 12: # Diciembre
        ref_month = 11
        ref_year = year
    elif month == 3: # Marzo
        ref_month = 11
        ref_year = year - 1
        
    if ref_month:
        fechas = []
        d = date(ref_year, ref_month, 1)
        # Buscar el primer día de ese weekday en el mes
        while d.weekday() != weekday:
            d += timedelta(days=1)
        
        # Tomar los 4 días de ese weekday en el mes
        while len(fechas) < 4 and d.month == ref_month:
            fechas.append(d)
            d += timedelta(weeks=1)
            
        if len(fechas) >= 4:
            fechas_ajustadas = []
            fechas_usadas = set()
            for fecha_ref in fechas[:4]:
                fecha_ajustada = _ajustar_fecha_no_atipica(cursor, fecha_ref, fechas_usadas)
                fechas_ajustadas.append(fecha_ajustada)
                fechas_usadas.add(fecha_ajustada)
            return fechas_ajustadas

    # Por defecto: 4 semanas anteriores
    fechas_base = [fecha - timedelta(weeks=i) for i in range(1, 5)]
    fechas_ajustadas = []
    fechas_usadas = set()
    for fecha_ref in fechas_base:
        fecha_ajustada = _ajustar_fecha_no_atipica(cursor, fecha_ref, fechas_usadas)
        fechas_ajustadas.append(fecha_ajustada)
        fechas_usadas.add(fecha_ajustada)
    return fechas_ajustadas


def get_factores_ajuste_acumulados(cursor, fecha: date) -> tuple:
    """
    Calcula los factores de ajuste multiplicativos según Resolución 120/2025.
    Returns: (factor_total, lista_nombres_ajustes)
    """
    factor_total = 1.0
    ajustes = []
    
    month = fecha.month
    dia_semana = fecha.weekday()
    
    # 1. Factores Mensuales (Capa 1)
    if month == 1:
        factor_total *= 0.80
        ajustes.append("Mes Enero (0.80)")
    elif month == 12:
        factor_total *= 0.80
        ajustes.append("Mes Diciembre (0.80)")
        
    # 2. Factores Diarios (Capa 2)
    cursor.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (fecha,))
    if cursor.fetchone():
        if dia_semana == 5: # Sábado
            factor_total *= 0.50
            ajustes.append("Feriado Sábado (0.50)")
        else: # Laboral
            factor_total *= 0.30
            ajustes.append("Feriado Laboral (0.30)")
    else:
        # Pre/Post Feriado
        fecha_ant = fecha - timedelta(days=1)
        fecha_sig = fecha + timedelta(days=1)
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha IS NOT NULL AND (fecha = %s OR fecha = %s)", (fecha_ant, fecha_sig))
        feriados_cercanos = cursor.fetchall()
        
        pre_feriado = False
        post_feriado = False
        for f in feriados_cercanos:
            # feriados_cercanos devuelve objetos con atributo fecha o diccionarios según el cursor
            # Usamos acceso genérico por índice si el cursor es normal
            f_fecha = f[0] if isinstance(f, (list, tuple)) else f['fecha']
            if f_fecha == fecha_ant:
                post_feriado = True
            if f_fecha == fecha_sig:
                pre_feriado = True
        
        if post_feriado:
            factor_total *= 0.70
            ajustes.append("Post-Feriado (0.70)")
        if pre_feriado:
            factor_total *= 0.70
            ajustes.append("Pre-Feriado (0.70)")
                
    # 3. Factor Climático (Capa 3 - Lluvia > 5mm)
    cursor.execute("""
        SELECT mm_caidos FROM control_metricas.t_casuisticas_lluvia
        WHERE fecha_evento = %s
        AND mm_caidos > 5
        ORDER BY mm_caidos DESC LIMIT 1
    """, (fecha,))
    lluvia = cursor.fetchone()
    if lluvia:
        factor_total *= 0.50
        # Usar acceso por nombre de columna para evitar KeyError
        precipitacion = lluvia['mm_caidos'] if isinstance(lluvia, dict) else lluvia[0]
        ajustes.append(f"Lluvia {precipitacion}mm (0.50)")
        
    return round(factor_total, 2), ajustes


def calculate_ifo_index(cursor, eot_id: int, eot_vmt_hex: str, fecha, franja_info: dict, cbd_min_hora: int, fechas_historicas: list, factor_ajuste: float, ajuste_aplicado: str, cache_val: dict = None, cache_gps: dict = None) -> dict:
    """
    Calcula el índice IFO para una franja.
    """
    hora_inicio = franja_info['hora_inicio'].hour
    hora_fin = franja_info['hora_fin'].hour
    
    sum_ifo = 0
    count_horas = 0
    
    for hora in range(hora_inicio, hora_fin + 1):
        # CBD del día analizado
        cbd_dia = get_cbd_for_hour(cursor, eot_id, eot_vmt_hex, fecha, hora, cbd_min_hora, cache_val, cache_gps)
        
        # Promedio histórico
        sum_historico = 0
        count_historico = 0
        
        for fecha_hist in fechas_historicas:
            cbd_hist = get_cbd_for_hour(cursor, eot_id, eot_vmt_hex, fecha_hist, hora, cbd_min_hora, cache_val, cache_gps)
            sum_historico += cbd_hist
            count_historico += 1
        
        promedio_historico = sum_historico / count_historico if count_historico > 0 else 0
        promedio_ajustado = round(max(promedio_historico * factor_ajuste, cbd_min_hora), 2)
        
        ifo_hora = (cbd_dia / promedio_ajustado * 100) if promedio_ajustado > 0 else 0
        sum_ifo += ifo_hora
        count_horas += 1
    
    ifo_franja = sum_ifo / count_horas if count_horas > 0 else 0
    
    return {
        'ifo_franja': ifo_franja,
        'ajuste_aplicado': ajuste_aplicado,
        'b_dist_ajustado': factor_ajuste,
        'cant_horas': count_horas
    }


def get_estado_cumplimiento_cbd(indice: float) -> str:
    """Determina el estado de cumplimiento para CBD."""
    if indice >= 1.0:
        return 'Cumple'
    elif indice >= 0.95:
        return 'Leve'
    elif indice >= 0.85:
        return 'Intermedia'
    else:
        return 'Grave'


def get_estado_cumplimiento_ifo(ifo: float) -> str:
    """Determina el nivel de servicio para IFO."""
    if ifo >= 90:
        return 'Nivel A'
    elif ifo >= 80:
        return 'Nivel B'
    else:
        return 'Nivel C'


@router.post("", response_model=PerformanceResponse)
async def get_performance_data(
    request: PerformanceRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtener resultados de desempeño diario (CBD e IFO) con optimización de batch masiva.
    """
    cursor = db.get_cursor()
    
    try:
        # 1. Obtener info de los EOTs seleccionados
        cursor.execute("""
            SELECT eot_id, cod_catalogo, eot_nombre, id_eot_vmt_hex, gre_id
            FROM public.eots
            WHERE cod_catalogo = ANY(%s)
            AND cod_catalogo NOT IN (72)
            ORDER BY cod_catalogo
        """, (request.eot_ids,))
        eots = cursor.fetchall()
        
        if not eots:
            return PerformanceResponse(fecha_analisis=request.fecha, tipo_dia="Desconocido", resultados_eots=[])
        
        # 2. Determinar tipo de día
        cursor.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (request.fecha,))
        es_feriado = cursor.fetchone() is not None
        dia_semana = request.fecha.weekday()
        if es_feriado or dia_semana == 6:
            id_tipo_dia, tipo_dia = 7, ('FERIADO' if es_feriado else 'NO LABORAL')
        elif dia_semana == 5:
            id_tipo_dia, tipo_dia = 6, 'SABADO'
        else:
            id_tipo_dia, tipo_dia = 5, 'LABORAL'
        
        # 3. Obtener franjas operativas
        cursor.execute("""
            SELECT id_franja, denominacion, hora_inicio, hora_fin
            FROM control_metricas.franjas_operativas
            WHERE id_tipo_dia = %s AND (inicio_vigencia IS NULL OR inicio_vigencia <= %s)
              AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
            ORDER BY hora_inicio
        """, (id_tipo_dia, request.fecha, request.fecha))
        franjas = cursor.fetchall()
        
        # 4. Pre-calcular datos comunes y determinar TODAS las fechas necesarias
        fechas_historicas = get_fechas_referencia(cursor, request.fecha)
        todas_las_fechas = [request.fecha] + fechas_historicas
        factor_ajuste, lista_ajustes = get_factores_ajuste_acumulados(cursor, request.fecha)
        ajuste_global = ", ".join(lista_ajustes) if lista_ajustes else 'Ninguno'
        
        # 5. PRE-CARGA MASIVA (BATCH) - Esto es el corazón de la optimización
        cod_catalogos = [e['cod_catalogo'] for e in eots]
        vmt_hexs = [e['id_eot_vmt_hex'] for e in eots if e['id_eot_vmt_hex']]
        
        # A. Caché Horaria Validaciones (servicios_diarios)
        cursor.execute("""
            SELECT id_eot_catalogo, fecha, hora, COUNT(DISTINCT idsam) as cbd
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = ANY(%s) AND fecha = ANY(%s)
            GROUP BY id_eot_catalogo, fecha, hora
        """, (cod_catalogos, todas_las_fechas))
        cache_val = {(r['id_eot_catalogo'], r['fecha'], r['hora']): r['cbd'] for r in cursor.fetchall()}
        
        # B. Caché Horaria GPS (cbd_detalle_buses)
        cache_gps = {}
        if vmt_hexs:
            cursor.execute("""
                SELECT id_eot_vmt_hex, fecha, hora, COUNT(DISTINCT mean_id) as cbd
                FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = ANY(%s) AND fecha = ANY(%s)
                GROUP BY id_eot_vmt_hex, fecha, hora
            """, (vmt_hexs, todas_las_fechas))
            cache_gps = {(r['id_eot_vmt_hex'], r['fecha'], r['hora']): r['cbd'] for r in cursor.fetchall()}

        # C. Caché Franja (sólo fecha actual) para CBD (DISTINCT buses en el rango)
        cache_franja_val = {}
        cache_franja_gps = {}
        for f in franjas:
            h_ini, h_fin = f['hora_inicio'].hour, f['hora_fin'].hour
            cursor.execute("""
                SELECT id_eot_catalogo, COUNT(DISTINCT idsam) as cbd FROM public.servicios_diarios
                WHERE id_eot_catalogo = ANY(%s) AND fecha = %s AND hora >= %s AND hora <= %s
                GROUP BY id_eot_catalogo
            """, (cod_catalogos, request.fecha, h_ini, h_fin))
            for r in cursor.fetchall():
                cache_franja_val[(r['id_eot_catalogo'], request.fecha, f['id_franja'])] = r['cbd']
            
            if vmt_hexs:
                cursor.execute("""
                    SELECT id_eot_vmt_hex, COUNT(DISTINCT mean_id) as cbd FROM control_metricas.cbd_detalle_buses
                    WHERE id_eot_vmt_hex = ANY(%s) AND fecha = %s AND hora >= %s AND hora <= %s
                    GROUP BY id_eot_vmt_hex
                """, (vmt_hexs, request.fecha, h_ini, h_fin))
                for r in cursor.fetchall():
                    cache_franja_gps[(r['id_eot_vmt_hex'], request.fecha, f['id_franja'])] = r['cbd']

        # D. Pre-cargar parámetros de franjas
        params_franjas = {}
        for f in franjas:
            # Parámetros CBD
            cursor.execute("SELECT cbd_minimo_hora, cbd_minimo_franja FROM control_metricas.cbd_parametros_minimos WHERE id_franja = %s LIMIT 1", (f['id_franja'],))
            p_cbd = cursor.fetchone()
            # Parámetros IFO
            cursor.execute("SELECT porc_cumplimiento_minimo FROM control_metricas.parametros_ifo WHERE id_franja_operativa = %s ORDER BY inicio_vigencia DESC LIMIT 1", (f['id_franja'],))
            p_ifo = cursor.fetchone()
            
            params_franjas[f['id_franja']] = {
                'min_h': p_cbd['cbd_minimo_hora'] if p_cbd else 0,
                'min_f': p_cbd['cbd_minimo_franja'] if p_cbd else 0,
                'ifo_min': p_ifo['porc_cumplimiento_minimo'] if p_ifo else 80.0
            }

        # 6. Para cada EOT, realizar los cálculos (ahora ultra-rápidos con caché)
        resultados_eots = []
        for eot in eots:
            gre_nombre = None
            if eot['gre_id']:
                cursor.execute("SELECT gre_nombre FROM public.gremios WHERE gre_id = %s", (eot['gre_id'],))
                g = cursor.fetchone()
                gre_nombre = g['gre_nombre'] if g else None
            
            res_franjas = []
            for f in franjas:
                p = params_franjas[f['id_franja']]
                
                # Calcular CBD con caché
                cbd_res = calculate_cbd_index(
                    cursor, eot['cod_catalogo'], eot['id_eot_vmt_hex'], request.fecha, 
                    f, p['min_h'], p['min_f'], 
                    cache_val, cache_gps, cache_franja_val, cache_franja_gps
                )
                
                # Calcular IFO con caché
                ifo_res = calculate_ifo_index(
                    cursor, eot['cod_catalogo'], eot['id_eot_vmt_hex'], request.fecha, 
                    f, p['min_h'], fechas_historicas, factor_ajuste, ajuste_global, 
                    cache_val, cache_gps
                )
                
                res_franjas.append(PerformanceResult(
                    id_franja=f['id_franja'],
                    denominacion_franja=f['denominacion'],
                    cbd_obs_promedio=round(cbd_res['cbd_obs_franja'], 2),
                    cbd_minimo_franja_exigido=float(p['min_f']),
                    cbd_cumplimiento_franja_indice=round(cbd_res['cbd_indice'], 4),
                    cbd_estado_cumplimiento=get_estado_cumplimiento_cbd(cbd_res['cbd_indice']),
                    origen_cbd_final=cbd_res['origen'],
                    b_dist_ajustado=ifo_res['b_dist_ajustado'],
                    ifo_franja_calculado=round(ifo_res['ifo_franja'], 2),
                    ifo_minimo_exigido=float(p['ifo_min']),
                    ifo_estado_cumplimiento=get_estado_cumplimiento_ifo(ifo_res['ifo_franja']),
                    ajuste_aplicado=ifo_res['ajuste_aplicado'],
                    cant_horas=ifo_res['cant_horas']
                ))
            
            resultados_eots.append(EOTPerformance(
                eot_id=eot['cod_catalogo'],
                eot_nombre=eot['eot_nombre'],
                gre_nombre=gre_nombre,
                resultados_franjas=res_franjas
            ))
        
        return PerformanceResponse(fecha_analisis=request.fecha, tipo_dia=tipo_dia, resultados_eots=resultados_eots)
        
    except Exception as e:
        print(f"Error crítico en performance batch: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()



def determinar_nivel_ifo(ifo: float) -> str:
    """
    Determina el nivel según el IFO:
    - Nivel A: >= 90
    - Nivel B: 80 a 89
    - Nivel C: < 80
    """
    if ifo >= 90:
        return 'A'
    elif ifo >= 80:
        return 'B'
    else:
        return 'C'


@router.post("/save-ifo", response_model=SaveIFOResponse)
async def save_ifo_historico(
    request: SaveIFORequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Guarda resultados de IFO en control_metricas.ifo_historico.
    Actualiza registros existentes o crea nuevos.
    """
    cursor = db.get_cursor()
    
    try:
        guardados = 0
        actualizados = 0
        
        if not request.resultados:
            return SaveIFOResponse(
                guardados=0,
                actualizados=0,
                total=0
            )
        
        for item in request.resultados:
            try:
                # Validar datos requeridos
                if not item.id_eot_vmt_hex or item.fecha is None or item.id_franja is None:
                    print(f"⚠ Item inválido: id_eot_vmt_hex={item.id_eot_vmt_hex}, fecha={item.fecha}, id_franja={item.id_franja}")
                    continue
                
                # El IFO viene como porcentaje (0-100) desde la API
                # La BD espera decimal (0-1), así que convertimos
                ifo_val_pct = float(item.ifo)  # Porcentaje (0-100)
                ifo_min_pct = float(item.ifo_minimo)  # Porcentaje (0-100)
                
                ifo_val_decimal = ifo_val_pct / 100.0
                
                # determinar_nivel_ifo espera porcentaje
                nivel = determinar_nivel_ifo(ifo_val_pct)
                # Para comparar, ambos en porcentaje
                cumple_parametros = ifo_val_pct >= ifo_min_pct
                
                # Verificar si ya existe el registro
                cursor.execute("""
                    SELECT id FROM control_metricas.ifo_historico
                    WHERE id_eot_vmt_hex = %s AND fecha = %s AND id_franja = %s
                """, (item.id_eot_vmt_hex, item.fecha, item.id_franja))
                existe = cursor.fetchone()
                
                if existe:
                    # Actualizar registro existente
                    cursor.execute("""
                        UPDATE control_metricas.ifo_historico
                        SET ifo = %s,
                            cumple_parametros = %s,
                            nivel = %s,
                            cbd_indice = %s,
                            cbd_cantidad = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id_eot_vmt_hex = %s AND fecha = %s AND id_franja = %s
                    """, (ifo_val_decimal, cumple_parametros, nivel, item.cbd_indice, item.cbd_cantidad, item.id_eot_vmt_hex, item.fecha, item.id_franja))
                    actualizados += 1
                else:
                    # Insertar nuevo registro
                    cursor.execute("""
                        INSERT INTO control_metricas.ifo_historico
                        (id_eot_vmt_hex, fecha, id_franja, ifo, cumple_parametros, nivel, cbd_indice, cbd_cantidad, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (item.id_eot_vmt_hex, item.fecha, item.id_franja, ifo_val_decimal, cumple_parametros, nivel, item.cbd_indice, item.cbd_cantidad))
                    guardados += 1
            except Exception as item_error:
                print(f"Error procesando item IFO (EOT: {item.id_eot_vmt_hex}, fecha: {item.fecha}, franja: {item.id_franja}): {item_error}")
                import traceback
                traceback.print_exc()
                continue  # Continuar con el siguiente item
        
        db.connection.commit()
        
        return SaveIFOResponse(
            guardados=guardados,
            actualizados=actualizados,
            total=len(request.resultados)
        )
        
    except Exception as e:
        db.connection.rollback()
        print(f"Error guardando IFO histórico: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error guardando IFO histórico: {str(e)}")
    finally:
        cursor.close()
