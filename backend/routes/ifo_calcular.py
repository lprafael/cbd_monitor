"""Endpoint para calcular IFO según Resolución 120/2025 desde n8n u otros sistemas.

Este endpoint encapsula la lógica del script calcular_ifo.py para poder ser llamado
desde n8n o cualquier otro sistema de automatización.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel
# No necesitamos importar eots y performance aquí, los usamos directamente
from database.connection import DatabaseConnection, get_db_connection
from models.performance_schemas import SaveIFORequest, IFOHistoricoItem

router = APIRouter(prefix="/api/ifo", tags=["IFO"])


class CalcularIFORequest(BaseModel):
    """Request para calcular IFO."""
    fecha: Optional[str] = None  # YYYY-MM-DD, si no se especifica usa ayer
    desde: Optional[str] = None  # YYYY-MM-DD para rango
    hasta: Optional[str] = None  # YYYY-MM-DD para rango
    solo_calculo: bool = True  # Si False, también detecta incumplimientos
    notificacion: bool = False  # Si True, prepara datos para notificar a empresas
    verificacion: bool = False  # Si True, prepara datos para informe al director


class CalcularIFOResponse(BaseModel):
    """Response del cálculo de IFO."""
    fecha_procesada: str
    tipo_dia: str
    eots_procesados: int
    registros_guardados: int
    registros_actualizados: int
    total_registros: int
    incumplimientos_detectados: int
    modo: Optional[str] = None  # 'notificacion', 'verificacion' o None
    correos_enviados: int = 0
    errores_envio: List[str] = []
    resultados: List[dict] = []


@router.post("/calcular", response_model=CalcularIFOResponse)
async def calcular_ifo(
    request: CalcularIFORequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Calcula IFO para una fecha o rango de fechas y guarda en ifo_historico.
    
    Este endpoint replica la funcionalidad del script calcular_ifo.py pero
    como API REST para poder ser llamado desde n8n.
    
    Args:
        request: Parámetros de cálculo (fecha, desde, hasta)
    
    Returns:
        CalcularIFOResponse: Resultados del cálculo
    """
    try:
        # Determinar fechas a procesar
        if request.fecha:
            fecha_procesar = date.fromisoformat(request.fecha)
            fechas = [fecha_procesar]
        elif request.desde and request.hasta:
            desde = date.fromisoformat(request.desde)
            hasta = date.fromisoformat(request.hasta)
            fechas = []
            delta = hasta - desde
            for i in range(delta.days + 1):
                fechas.append(desde + timedelta(days=i))
        else:
            # Por defecto, procesar ayer
            fechas = [date.today() - timedelta(days=1)]
        
        # Validar que no se usen ambos modos a la vez
        if request.notificacion and request.verificacion:
            raise HTTPException(
                status_code=400,
                detail="Los parámetros 'notificacion' y 'verificacion' son mutuamente exclusivos"
            )
        
        # Determinar modo
        modo = None
        if request.verificacion:
            modo = 'verificacion'
        elif request.notificacion:
            modo = 'notificacion'
        
        # Procesar cada fecha
        resultados_totales = []
        total_guardados = 0
        total_actualizados = 0
        total_incumplimientos = 0
        
        for fecha_procesar in fechas:
            # 1. Obtener EOTs
            cursor = db.get_cursor()
            cursor.execute("""
                SELECT cod_catalogo, eot_nombre, id_eot_vmt_hex
                FROM public.eots
                WHERE permisionario IS TRUE
                ORDER BY eot_nombre
            """)
            eots_list = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            
            if not eots_list:
                raise HTTPException(status_code=404, detail="No se encontraron EOTs")
            
            eot_ids = [e['cod_catalogo'] for e in eots_list]
            eot_map = {eot['cod_catalogo']: eot.get('id_eot_vmt_hex') for eot in eots_list}
            
            # 2. Obtener datos de performance usando el endpoint existente
            from routes.performance import get_performance_data
            from models.performance_schemas import PerformanceRequest
            
            perf_request = PerformanceRequest(
                fecha=fecha_procesar,
                eot_ids=eot_ids
            )
            
            # Llamar directamente a la función del endpoint (es async)
            perf_response = await get_performance_data(perf_request, db)
            
            tipo_dia = perf_response.tipo_dia
            
            # 3. Procesar resultados y preparar para guardar
            resultados_para_guardar = []
            incumplimientos = []
            
            for eot_result in perf_response.resultados_eots:
                eot_id = eot_result.eot_id
                eot_nombre = eot_result.eot_nombre
                id_eot_vmt_hex = eot_map.get(eot_id)
                
                if not id_eot_vmt_hex:
                    continue
                
                for franja_result in eot_result.resultados_franjas:
                    # Preparar datos para guardar
                    resultados_para_guardar.append({
                        'id_eot_vmt_hex': id_eot_vmt_hex,
                        'fecha': fecha_procesar,
                        'id_franja': franja_result.id_franja,
                        'ifo': franja_result.ifo_franja_calculado,
                        'ifo_minimo': franja_result.ifo_minimo_exigido,
                        'cbd_indice': franja_result.cbd_cumplimiento_franja_indice,
                        'cbd_cantidad': int(franja_result.cbd_obs_promedio)
                    })
                    
                    # Detectar incumplimientos
                    # Si es modo verificación (Director), incluimos todo. Si es notificación (Empresa), solo incumplimientos.
                    es_incumplimiento = franja_result.ifo_franja_calculado < franja_result.ifo_minimo_exigido
                    incluir_en_reporte = es_incumplimiento or (modo == 'verificacion')
                    
                    if incluir_en_reporte:
                        incumplimientos.append({
                            'eot_nombre': eot_nombre,
                            'eot_id': eot_id,
                            'eot_vmt_hex': id_eot_vmt_hex,
                            'linea_ramal': f"Cat: {eot_id}",
                            'indicador': 'IFO Franja',
                            'franja_horaria': franja_result.denominacion_franja,
                            'id_franja': franja_result.id_franja,
                            'umbral_requerido': f"{franja_result.ifo_minimo_exigido:.0f}%",
                            'valor_observado': f"{franja_result.ifo_franja_calculado:.1f}%",
                            'tipo_infraccion': franja_result.ifo_estado_cumplimiento,
                            'normativa': 'Res. 120/2025',
                            'ajuste_aplicado': franja_result.ajuste_aplicado
                        })
            
            # 4. Guardar en ifo_historico
            if resultados_para_guardar:
                from routes.performance import save_ifo_historico
                from models.performance_schemas import SaveIFORequest, IFOHistoricoItem
                
                save_request = SaveIFORequest(
                    resultados=[
                        IFOHistoricoItem(
                            id_eot_vmt_hex=r['id_eot_vmt_hex'],
                            fecha=r['fecha'],
                            id_franja=r['id_franja'],
                            ifo=r['ifo'],
                            ifo_minimo=r['ifo_minimo'],
                            cbd_indice=r['cbd_indice'],
                            cbd_cantidad=r['cbd_cantidad']
                        )
                        for r in resultados_para_guardar
                    ]
                )
                
                save_response = await save_ifo_historico(save_request, db)
                total_guardados += save_response.guardados
                total_actualizados += save_response.actualizados
            else:
                save_response = None
            
            total_incumplimientos += len(incumplimientos)
            
            # 5. Enviar correos si corresponde (solo para modo verificacion o notificacion)
            correos_enviados = 0
            errores_envio = []
            
            if modo and incumplimientos:
                try:
                    # Intentar importar función de envío de correo desde utils
                    try:
                        from utils.enviar_informe import enviar_informe_incumplimientos
                    except ImportError:
                        # Si no está en utils, intentar desde res_120 (para desarrollo local)
                        import sys
                        from pathlib import Path
                        project_root = Path(__file__).parent.parent.parent
                        res_120_path = project_root / 'res_120'
                        if res_120_path.exists():
                            sys.path.insert(0, str(res_120_path))
                            from enviar_informe import enviar_informe_incumplimientos
                        else:
                            raise ImportError("Módulo enviar_informe no encontrado")
                    
                    if modo == 'verificacion':
                        # Enviar informe consolidado al director
                        if enviar_informe_incumplimientos(incumplimientos, fecha_procesar):
                            correos_enviados = 1
                        else:
                            errores_envio.append("Error al enviar informe al director")
                    
                    elif modo == 'notificacion':
                        # Agrupar por EOT y enviar a cada empresa
                        eots_incumplimientos = {}
                        for inc in incumplimientos:
                            eot_vmt_hex = inc.get('eot_vmt_hex')
                            if eot_vmt_hex and eot_vmt_hex not in eots_incumplimientos:
                                eots_incumplimientos[eot_vmt_hex] = {
                                    'eot_nombre': inc.get('eot_nombre', ''),
                                    'incumplimientos': []
                                }
                            if eot_vmt_hex:
                                eots_incumplimientos[eot_vmt_hex]['incumplimientos'].append(inc)
                        
                        # Obtener emails de empresas desde BD
                        cursor = db.get_cursor()
                        try:
                            for eot_vmt_hex, data in eots_incumplimientos.items():
                                try:
                                    cursor.execute("""
                                        SELECT email FROM public.eots 
                                        WHERE id_eot_vmt_hex = %s AND email IS NOT NULL
                                    """, (eot_vmt_hex,))
                                    result = cursor.fetchone()
                                    email_eot = result[0] if result else None
                                    
                                    if email_eot:
                                        if enviar_informe_incumplimientos(data['incumplimientos'], fecha_procesar):
                                            correos_enviados += 1
                                        else:
                                            errores_envio.append(f"Error enviando a {data['eot_nombre']}")
                                    else:
                                        errores_envio.append(f"{data['eot_nombre']}: Sin email configurado")
                                except Exception as e:
                                    errores_envio.append(f"Error obteniendo email para {data['eot_nombre']}: {str(e)}")
                        finally:
                            cursor.close()
                
                except ImportError as e:
                    errores_envio.append(f"Módulo enviar_informe no disponible: {str(e)}")
                except Exception as e:
                    errores_envio.append(f"Error en envío de correos: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            resultados_totales.append({
                'fecha': fecha_procesar.isoformat(),
                'tipo_dia': tipo_dia,
                'eots_procesados': len(eot_ids),
                'registros_guardados': save_response.guardados if save_response else 0,
                'registros_actualizados': save_response.actualizados if save_response else 0,
                'incumplimientos': len(incumplimientos),
                'correos_enviados': correos_enviados,
                'errores_envio': errores_envio,
                'detalle_incumplimientos': incumplimientos if (modo or not request.solo_calculo) else []
            })
        
        # Retornar respuesta consolidada
        fecha_principal = fechas[0] if len(fechas) == 1 else None
        
        # Calcular totales de correos enviados
        total_correos_enviados = sum(r.get('correos_enviados', 0) for r in resultados_totales)
        todos_errores_envio = []
        for r in resultados_totales:
            todos_errores_envio.extend(r.get('errores_envio', []))
        
        return CalcularIFOResponse(
            fecha_procesada=fecha_principal.isoformat() if fecha_principal else f"{fechas[0].isoformat()} a {fechas[-1].isoformat()}",
            tipo_dia=resultados_totales[0]['tipo_dia'] if resultados_totales else 'Desconocido',
            eots_procesados=len(eot_ids) if eots_list else 0,
            registros_guardados=total_guardados,
            registros_actualizados=total_actualizados,
            total_registros=total_guardados + total_actualizados,
            incumplimientos_detectados=total_incumplimientos,
            modo=modo,
            correos_enviados=total_correos_enviados,
            errores_envio=todos_errores_envio,
            resultados=resultados_totales
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculando IFO: {str(e)}")
