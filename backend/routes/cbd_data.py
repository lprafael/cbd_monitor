"""Rutas para manejar operaciones relacionadas con datos de CBD."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from datetime import datetime
from models.schemas import (
    CBDDataRequest, CBDDataResponse, DatosEOT, FilaEOT, DatoCelda, FranjaOperativa
)
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/cbd-data", tags=["CBD Data"])

def get_tipo_dia_id(fecha_obj):
    """
    Determinar el id_tipo_dia basado en la fecha.
    
    Args:
        fecha_obj: Objeto date
    
    Returns:
        int: ID del tipo de día
    """
    dia_semana = fecha_obj.weekday()
    
    if dia_semana >= 0 and dia_semana <= 4:  # Lunes a Viernes
        return 5  # LABORAL
    elif dia_semana == 5:  # Sábado
        return 6  # SABADO
    else:  # Domingo
        return 7  # NO LABORAL

def get_franjas_operativas_db(db: DatabaseConnection, id_tipo_dia: int, fecha) -> List[Dict]:
    """Obtener franjas operativas desde la base de datos para una fecha específica."""
    cursor = db.get_cursor()
    
    query = """
        SELECT 
            id_franja,
            denominacion,
            hora_inicio,
            hora_fin,
            id_tipo_dia,
            activo
        FROM control_metricas.franjas_operativas
        WHERE id_tipo_dia = %s
            AND (inicio_vigencia IS NULL OR inicio_vigencia <= %s)
            AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
        ORDER BY hora_inicio
    """
    
    cursor.execute(query, (id_tipo_dia, fecha, fecha))
    results = cursor.fetchall()
    cursor.close()
    
    return [dict(row) for row in results]

def get_parametros_minimos(db: DatabaseConnection, id_tipo_dia: int, fecha) -> Dict:
    """
    Obtener parámetros mínimos de CBD para un tipo de día.
    
    Returns:
        Dict: Diccionario con parámetros mínimos indexados por id_franja
    """
    cursor = db.get_cursor()
    
    query = """
        SELECT 
            id,
            id_tipo_dia,
            id_franja,
            cbd_minimo_franja,
            cbd_minimo_hora,
            vigencia_desde,
            vigencia_hasta,
            id_infraccion_hora,
            id_infraccion_franja
        FROM control_metricas.cbd_parametros_minimos
        WHERE id_tipo_dia = %s
            AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
            AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
    """
    
    cursor.execute(query, (id_tipo_dia, fecha, fecha))
    results = cursor.fetchall()
    cursor.close()
    
    # Indexar por id_franja
    parametros = {}
    for row in results:
        parametros[row['id_franja']] = dict(row)
    
    return parametros

def get_servicios_diarios_data(db: DatabaseConnection, eot_ids: List[int], fecha, 
                                franjas: List[Dict], modo: str) -> Dict:
    """
    Obtener datos de servicios diarios por EOT.
    
    Returns:
        Dict: Diccionario con datos indexados por eot_id, incluyendo totales
    """
    cursor = db.get_cursor()
    
    if modo == "franja":
        # Contar buses por franja
        query = """
            SELECT 
                sd.id_eot_catalogo,
                fo.id_franja,
                COUNT(DISTINCT sd.idsam) as cantidad_buses
            FROM public.servicios_diarios sd
            INNER JOIN control_metricas.franjas_operativas fo 
                ON (sd.hora * INTERVAL '1 hour')::time >= fo.hora_inicio 
                AND (sd.hora * INTERVAL '1 hour')::time < fo.hora_fin
                AND (fo.inicio_vigencia IS NULL OR fo.inicio_vigencia <= sd.fecha)
                AND (fo.fin_vigencia IS NULL OR fo.fin_vigencia >= sd.fecha)
            WHERE sd.id_eot_catalogo = ANY(%s)
                AND sd.fecha = %s
            GROUP BY sd.id_eot_catalogo, fo.id_franja
        """
        cursor.execute(query, (eot_ids, fecha))
    else:  # modo == "hora"
        # Contar buses por hora
        query = """
            SELECT 
                id_eot_catalogo,
                EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time) as hora,
                COUNT(DISTINCT idsam) as cantidad_buses
            FROM public.servicios_diarios
            WHERE id_eot_catalogo = ANY(%s)
                AND fecha = %s
            GROUP BY id_eot_catalogo, EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time)
        """
        cursor.execute(query, (eot_ids, fecha))
    
    results = cursor.fetchall()
    
    # Obtener totales (idsam distintos en el día completo)
    # Inicializar totales en 0 para todos los EOTs
    totales = {eot_id: 0 for eot_id in eot_ids}
    
    query_total = """
        SELECT 
            id_eot_catalogo,
            COUNT(DISTINCT idsam) as total_dia
        FROM public.servicios_diarios
        WHERE id_eot_catalogo = ANY(%s)
            AND fecha = %s
        GROUP BY id_eot_catalogo
    """
    cursor.execute(query_total, (eot_ids, fecha))
    resultados_totales = cursor.fetchall()
    for row in resultados_totales:
        totales[row['id_eot_catalogo']] = row['total_dia']
    
    cursor.close()
    
    # Organizar datos por EOT
    datos = {}
    for row in results:
        eot_id = row['id_eot_catalogo']
        if eot_id not in datos:
            datos[eot_id] = {'totales': totales.get(eot_id, 0)}
        
        if modo == "franja":
            key = str(row['id_franja'])
        else:
            key = str(int(row['hora']))
        
        datos[eot_id][key] = row['cantidad_buses']
    
    return datos

# def get_cbd_detalle_buses_data(db: DatabaseConnection, eot_ids: List[int], fecha,
#                                 franjas: List[Dict], modo: str) -> Dict:
#     """
#     Obtener datos de CBD detalle de buses por EOT.
    
#     Returns:
#         Dict: Diccionario con datos indexados por eot_id
#     """
#     cursor = db.get_cursor()
    
#     if modo == "franja":
#         # Contar buses por franja
#         query = """
#             SELECT 
#                 cdb.id_eot_vmt_hex,
#                 fo.id_franja,
#                 COUNT(DISTINCT cdb.mean_id) as cantidad_buses
#             FROM control_metricas.cbd_detalle_buses cdb
#             INNER JOIN control_metricas.franjas_operativas fo 
#                 ON (cdb.hora * INTERVAL '1 hour')::time >= fo.hora_inicio 
#                 AND (cdb.hora * INTERVAL '1 hour')::time < fo.hora_fin
#                 AND fo.activo = TRUE
#             WHERE cdb.id_eot_vmt_hex = ANY(ARRAY[%s]::text[])
#                 AND cdb.fecha = %s
#             GROUP BY cdb.id_eot_vmt_hex, fo.id_franja
#         """
#         cursor.execute(query, (eot_ids, fecha))
#     else:  # modo == "hora"
#         # Contar buses por hora
#         query = """
#             SELECT 
#                 id_eot_vmt_hex,
#                 EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time) as hora,
#                 COUNT(DISTINCT mean_id) as cantidad_buses
#             FROM control_metricas.cbd_detalle_buses
#             WHERE id_eot_vmt_hex = ANY(ARRAY[%s]::text[])
#                 AND fecha = %s
#             GROUP BY id_eot_vmt_hex, EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time)
#         """
#         cursor.execute(query, (eot_ids, fecha))
    
#     results = cursor.fetchall()
#     cursor.close()
    
#     # Organizar datos por EOT
#     datos = {}
#     for row in results:
#         eot_id = row['id_eot_vmt_hex']
#         if eot_id not in datos:
#             datos[eot_id] = {}
        
#         if modo == "franja":
#             key = str(row['id_franja'])
#         else:
#             key = str(int(row['hora']))
        
#         datos[eot_id][key] = row['cantidad_buses']
    
#     # Si el modo es por hora, filtrar según las franjas operativas
#     if modo == "hora" and franjas:
#         # Obtener la hora mínima y máxima de las franjas operativas
#         hora_min = min(franja['hora_inicio'].hour for franja in franjas)
#         hora_max = max(franja['hora_fin'].hour for franja in franjas)
        
#         # Filtrar las claves de cada EOT para incluir solo horas dentro del rango
#         for eot_id in datos:
#             datos[eot_id] = {
#                 k: v for k, v in datos[eot_id].items() 
#                 if hora_min <= int(k) <= hora_max
#             }
    
#     return datos

# En cbd_data.py, modifica la función get_cbd_detalle_buses_data:

def get_cbd_detalle_buses_data(db: DatabaseConnection, eot_ids: List[int], fecha,
                             franjas: List[Dict], modo: str) -> Dict:
    """
    Obtener datos de CBD detalle de buses por EOT.
    
    Returns:
        Dict: Diccionario con datos indexados por eot_id (entero)
    """
    cursor = db.get_cursor()
    
    # Mapeo de códigos de catálogo a id_eot_vmt_hex
    query_map = """
        SELECT cod_catalogo, id_eot_vmt_hex 
        FROM public.eots 
        WHERE cod_catalogo = ANY(%s)
            AND id_eot_vmt_hex IS NOT NULL
    """
    cursor.execute(query_map, (eot_ids,))
    eot_mapping = {row['cod_catalogo']: row['id_eot_vmt_hex'] for row in cursor.fetchall()}
    
    if not eot_mapping:
        cursor.close()
        print(f"⚠️ No se encontró mapeo de EOTs para: {eot_ids}")
        return {}

    print(f"🔍 Mapeo EOTs encontrado: {eot_mapping}")

    # Consulta para obtener datos de GPS
    if modo == "franja":
        # Contar buses por franja
        query = """
            SELECT 
                %s::integer as id_eot_catalogo,
                fo.id_franja,
                COUNT(DISTINCT cdb.mean_id) as cantidad_buses
            FROM control_metricas.cbd_detalle_buses cdb
            INNER JOIN control_metricas.franjas_operativas fo 
                ON (cdb.hora * INTERVAL '1 hour')::time >= fo.hora_inicio 
                AND (cdb.hora * INTERVAL '1 hour')::time < fo.hora_fin
                AND (fo.inicio_vigencia IS NULL OR fo.inicio_vigencia <= cdb.fecha)
                AND (fo.fin_vigencia IS NULL OR fo.fin_vigencia >= cdb.fecha)
            WHERE cdb.id_eot_vmt_hex = %s
                AND cdb.fecha = %s
            GROUP BY fo.id_franja
        """
    else:  # modo == "hora"
        # Contar buses por hora
        query = """
            SELECT 
                %s::integer as id_eot_catalogo,
                EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time)::integer as hora,
                COUNT(DISTINCT mean_id) as cantidad_buses
            FROM control_metricas.cbd_detalle_buses
            WHERE id_eot_vmt_hex = %s
                AND fecha = %s
            GROUP BY EXTRACT(HOUR FROM (hora * INTERVAL '1 hour')::time)
        """
    
    # Ejecutar consulta para cada EOT
    all_results = []
    for cod_catalogo, vmt_hex in eot_mapping.items():
        # Asegurar que vmt_hex sea string y no None
        if not vmt_hex:
            print(f"⚠️ EOT {cod_catalogo} tiene id_eot_vmt_hex NULL o vacío")
            continue
            
        vmt_hex_str = str(vmt_hex).strip()
        print(f"🔍 Consultando GPS para EOT {cod_catalogo} (vmt_hex: '{vmt_hex_str}'), fecha: {fecha}")
        
        # Verificación: consultar si hay datos en la tabla para este EOT y fecha
        check_query = """
            SELECT COUNT(*) as total_registros
            FROM control_metricas.cbd_detalle_buses
            WHERE id_eot_vmt_hex = %s
                AND fecha = %s
        """
        cursor.execute(check_query, (vmt_hex_str, fecha))
        check_result = cursor.fetchone()
        print(f"🔍 Verificación: Total de registros en cbd_detalle_buses para vmt_hex '{vmt_hex_str}' y fecha {fecha}: {check_result['total_registros']}")
        
        # Si hay datos, ejecutar la consulta principal
        if check_result['total_registros'] > 0:
            cursor.execute(query, (cod_catalogo, vmt_hex_str, fecha))
            results = cursor.fetchall()
            print(f"📊 Resultados encontrados para EOT {cod_catalogo}: {len(results)} registros")
            if results:
                print(f"   Ejemplo: {dict(results[0])}")
            all_results.extend(results)
        else:
            print(f"⚠️ No hay datos en cbd_detalle_buses para vmt_hex '{vmt_hex_str}' y fecha {fecha}")
    
    # Obtener totales (mean_id distintos en el día completo)
    # Inicializar totales en 0 para todos los EOTs
    totales = {cod: 0 for cod in eot_mapping.keys()}
    
    if eot_mapping:
        query_total = """
            SELECT 
                e.cod_catalogo,
                COUNT(DISTINCT cdb.mean_id) as total_dia
            FROM control_metricas.cbd_detalle_buses cdb
            INNER JOIN public.eots e ON cdb.id_eot_vmt_hex = e.id_eot_vmt_hex
            WHERE e.cod_catalogo = ANY(%s)
                AND cdb.fecha = %s
            GROUP BY e.cod_catalogo
        """
        cursor.execute(query_total, (list(eot_mapping.keys()), fecha))
        resultados_totales = cursor.fetchall()
        for row in resultados_totales:
            totales[row['cod_catalogo']] = row['total_dia']
    
    cursor.close()
    
    # Organizar datos por EOT (usando la misma estructura que get_servicios_diarios_data)
    datos = {}
    for row in all_results:
        eot_id = row['id_eot_catalogo']  # Mantener como entero, no convertir a string
        if eot_id not in datos:
            datos[eot_id] = {'totales': totales.get(eot_id, 0)}
        
        if modo == "franja":
            key = str(row['id_franja'])
        else:
            key = str(int(row['hora']))
        
        datos[eot_id][key] = row['cantidad_buses']
    
    print(f"✅ Datos GPS organizados: {datos}")
    return datos

def get_eot_info(db: DatabaseConnection, eot_ids: List[int]) -> Dict:
    """Obtener información de EOTs."""
    cursor = db.get_cursor()
    
    query = """
        SELECT 
            e.cod_catalogo,
            e.eot_nombre,
            g.gre_nombre as gre_nombre
        FROM public.eots e
        LEFT JOIN public.gremios g ON e.gre_id = g.gre_id
        WHERE e.cod_catalogo = ANY(%s)
    """
    
    cursor.execute(query, (eot_ids,))
    results = cursor.fetchall()
    cursor.close()
    
    # Indexar por cod_catalogo
    eots = {}
    for row in results:
        eots[row['cod_catalogo']] = dict(row)
    
    return eots

@router.post("", response_model=CBDDataResponse)
async def get_cbd_data(
    request: CBDDataRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtener datos completos de CBD para EOTs seleccionados.
    
    Args:
        request: Solicitud con eot_ids, fecha y modo_visualizacion
    
    Returns:
        CBDDataResponse: Datos completos de CBD con validaciones
    """
    try:
        # Validar modo de visualización
        if request.modo_visualizacion not in ["hora", "franja"]:
            raise HTTPException(
                status_code=400,
                detail="Modo de visualización debe ser 'hora' o 'franja'"
            )
        
        # Determinar tipo de día
        id_tipo_dia = get_tipo_dia_id(request.fecha)
        
        # Mapeo de nombres de tipo de día
        nombres_tipo_dia = {5: "LABORAL", 6: "SABADO", 7: "NO LABORAL"}
        nombre_tipo_dia = nombres_tipo_dia.get(id_tipo_dia, "DESCONOCIDO")
        
        # Obtener franjas operativas
        franjas = get_franjas_operativas_db(db, id_tipo_dia, request.fecha)
        
        if not franjas:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron franjas operativas para el tipo de día {id_tipo_dia}"
            )
        
        # Obtener parámetros mínimos
        parametros = get_parametros_minimos(db, id_tipo_dia, request.fecha)
        
        # Obtener información de EOTs
        eot_info = get_eot_info(db, request.eot_ids)
        
        # Obtener datos de servicios diarios
        servicios_data = get_servicios_diarios_data(
            db, request.eot_ids, request.fecha, franjas, request.modo_visualizacion
        )
        
        # Obtener datos de CBD detalle buses
        cbd_data = get_cbd_detalle_buses_data(
            db, request.eot_ids, request.fecha, franjas, request.modo_visualizacion
        )
        
        # Construir respuesta
        datos_eots = []
        
        for eot_id in request.eot_ids:
            if eot_id not in eot_info:
                continue
            
            info = eot_info[eot_id]
            
            # Construir datos por franja/hora
            if request.modo_visualizacion == "franja":
                keys = [str(f['id_franja']) for f in franjas]
            else:
                # Generar lista de horas (0-23)
                keys = [str(h) for h in range(24)]
            
            # Construir fila de servicios diarios
            datos_servicios = {}
            # Total es la cantidad de idsam distintos en el día completo
            total_servicios = servicios_data.get(eot_id, {}).get('totales', 0)
            
            for key in keys:
                cantidad = servicios_data.get(eot_id, {}).get(key, 0)
                parametro_minimo = None
                if request.modo_visualizacion == "franja":
                    franja_id = int(key)
                    if franja_id in parametros:
                        parametro_minimo = parametros[franja_id].get('cbd_minimo_franja')
                else:
                    # Para modo hora, buscar el parámetro en la franja que contenga esa hora
                    hora_actual = int(key)
                    for franja in franjas:
                        # Extraer hora de inicio y fin
                        h_inicio = franja['hora_inicio'].hour
                        h_fin = franja['hora_fin'].hour
                        # Ajuste para "04:59:59" -> hora 4 está incluida
                        # Si hora_fin es '24:00', tratar como 24
                        
                        # La franja incluye desde hora_inicio hasta hora_fin (inclusive la hora del timestamp si es menor a XX:59:59)
                        # Como comparamos enteros de hora (0-23):
                        # Franja 03:00-04:59 -> horas 3 y 4.
                        # h_inicio=3, h_fin=4.  3 <= hora <= 4.
                        
                        if h_inicio <= hora_actual <= h_fin:
                            franja_id = franja['id_franja']
                            if franja_id in parametros:
                                parametro_minimo = parametros[franja_id].get('cbd_minimo_hora')
                                break
                
                # Determinar si cumple el parámetro
                cumple = True
                if parametro_minimo is not None:
                    cumple = cantidad >= parametro_minimo
                
                datos_servicios[key] = DatoCelda(
                    cantidad_buses=cantidad,
                    cumple_parametro=cumple,
                    parametro_minimo=parametro_minimo
                )
            
            fila_servicios = FilaEOT(
                tipo_fila="servicios_diarios",
                datos_por_franja=datos_servicios,
                total=total_servicios
            )
            
            # Construir fila de CBD detalle buses
            datos_cbd = {}
            # Total es la cantidad de mean_id distintos en el día completo
            total_cbd = cbd_data.get(eot_id, {}).get('totales', 0)
            
            for key in keys:
                cantidad = cbd_data.get(eot_id, {}).get(key, 0)
                
                # Determinar parámetro mínimo
                parametro_minimo = None
                if request.modo_visualizacion == "franja":
                    franja_id = int(key)
                    if franja_id in parametros:
                        parametro_minimo = parametros[franja_id].get('cbd_minimo_franja')
                else:
                    # Para modo hora, buscar el parámetro en la franja que contenga esa hora
                    hora_actual = int(key)
                    for franja in franjas:
                        # Extraer hora de inicio y fin
                        h_inicio = franja['hora_inicio'].hour
                        h_fin = franja['hora_fin'].hour
                        
                        if h_inicio <= hora_actual <= h_fin:
                            franja_id = franja['id_franja']
                            if franja_id in parametros:
                                parametro_minimo = parametros[franja_id].get('cbd_minimo_hora')
                                break
                
                # Determinar si cumple el parámetro
                cumple = True
                if parametro_minimo is not None:
                    cumple = cantidad >= parametro_minimo
                
                datos_cbd[key] = DatoCelda(
                    cantidad_buses=cantidad,
                    cumple_parametro=cumple,
                    parametro_minimo=parametro_minimo
                )
            
            fila_cbd = FilaEOT(
                tipo_fila="cbd_detalle_buses",
                datos_por_franja=datos_cbd,
                total=total_cbd
            )
            
            # Agregar datos del EOT
            datos_eots.append(DatosEOT(
                eot_id=eot_id,
                eot_nombre=info['eot_nombre'],
                gre_nombre=info.get('gre_nombre'),
                fila_servicios=fila_servicios,
                fila_cbd=fila_cbd
            ))
        
        # Construir respuesta final
        return CBDDataResponse(
            fecha=request.fecha,
            id_tipo_dia=id_tipo_dia,
            nombre_tipo_dia=nombre_tipo_dia,
            modo_visualizacion=request.modo_visualizacion,
            franjas_operativas=[FranjaOperativa(**f) for f in franjas],
            datos_eots=datos_eots,
            parametros_minimos=parametros
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener datos de CBD: {str(e)}"
        )
