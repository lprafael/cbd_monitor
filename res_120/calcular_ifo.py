"""
Script para calcular IFO según Resolución 120/2025 y guardar resultados en base de datos.
Usa la API del backend para los cálculos y para guardar en control_metricas.ifo_historico.

EJEMPLOS DE USO:
---------------

# 1. Calcular y guardar para el día de ayer (sin notificaciones)
python calcular_ifo.py

# 2. Calcular y guardar para una fecha específica
python calcular_ifo.py --fecha 2025-11-25

# 3. Calcular y guardar para un rango de fechas
python calcular_ifo.py --desde 2025-11-01 --hasta 2025-11-30

# 4. Calcular, guardar y enviar notificación a cada empresa con incumplimientos
python calcular_ifo.py --fecha 2025-11-25 --notificacion

# 5. Calcular, guardar y enviar informe consolidado al director
python calcular_ifo.py --fecha 2025-11-25 --verificacion

# 6. Procesar rango de fechas y enviar notificaciones a empresas
python calcular_ifo.py --desde 2025-11-01 --hasta 2025-11-30 --notificacion

# 7. Procesar rango y enviar informe al director
python calcular_ifo.py --desde 2025-11-01 --hasta 2025-11-30 --verificacion

NOTAS:
- Si no se especifican parámetros, procesa el día anterior (D-1)
- --notificacion y --verificacion son mutuamente exclusivos
- Los resultados se guardan en control_metricas.ifo_historico a través de la API
- El nivel (A/B/C) se calcula automáticamente según el IFO
- Requiere que la API esté ejecutándose (configurar CBD_API_URL si es necesario)
- Ya no requiere credenciales de base de datos
"""

import requests
from datetime import datetime, timedelta, date
import sys
import traceback
import argparse
from dotenv import load_dotenv
import os
import concurrent.futures

try:
    from enviar_informe import enviar_informe_incumplimientos, get_db_connection
except ImportError:
    def enviar_informe_incumplimientos(datos, fecha):
        print("⚠ Módulo enviar_informe no encontrado. No se enviará correo.")
        return False
    
    def get_db_connection():
        # Ya no se necesita, pero mantenemos por compatibilidad con enviar_informe
        pass

load_dotenv()

# Configuración del API
API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:8000')
API_URL = f"{API_BASE_URL}/api"

datos_incumplimientos = []


def get_eots():
    """Obtiene la lista de EOTs desde la API."""
    try:
        response = requests.get(f"{API_URL}/eots", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Error obteniendo EOTs de la API: {e}")
        print(f"  Verifique que la API esté ejecutándose en {API_BASE_URL}")
        return None


def get_performance_data(fecha, eot_ids, max_retries=2):
    """
    Obtiene datos de performance desde la API para una fecha y lista de EOTs.
    Procesa en lotes si hay muchos EOTs para evitar timeouts.
    """
    try:
        # Si hay muchos EOTs, procesar en lotes de 10
        TAMANO_LOTE = 5
        if len(eot_ids) > TAMANO_LOTE:
            print(f"  Procesando {len(eot_ids)} EOTs en lotes de {TAMANO_LOTE}...")
            resultados_combinados = {
                'fecha_analisis': fecha,
                'tipo_dia': None,
                'resultados_eots': []
            }
            
            def procesar_lote(lote_actual):
                for intento in range(max_retries):
                    try:
                        payload = {
                            "fecha": fecha.strftime("%Y-%m-%d"),
                            "eot_ids": lote_actual
                        }
                        # Timeout más largo para cada lote: 120 segundos
                        response = requests.post(f"{API_URL}/performance", json=payload, timeout=120)
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.Timeout:
                        if intento < max_retries - 1:
                            continue
                    except Exception as e:
                        print(f"      ✗ Error en lote: {e}")
                return None

            lotes = [eot_ids[i:i + TAMANO_LOTE] for i in range(0, len(eot_ids), TAMANO_LOTE)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                future_to_lote = {executor.submit(procesar_lote, lote): i for i, lote in enumerate(lotes)}
                
                for future in concurrent.futures.as_completed(future_to_lote):
                    i = future_to_lote[future]
                    try:
                        data_lote = future.result()
                        if data_lote:
                            print(f"    ✓ Lote {i+1}/{len(lotes)} procesado")
                            if resultados_combinados['tipo_dia'] is None:
                                resultados_combinados['tipo_dia'] = data_lote.get('tipo_dia')
                            resultados_combinados['resultados_eots'].extend(data_lote.get('resultados_eots', []))
                        else:
                            print(f"    ✗ Lote {i+1}/{len(lotes)} falló después de reintentos")
                    except Exception as exc:
                        print(f"    ✗ Lote {i+1} generó una excepción: {exc}")

            return resultados_combinados
        else:
            # Procesar todos los EOTs de una vez si son pocos
            for intento in range(max_retries):
                try:
                    payload = {
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "eot_ids": eot_ids
                    }
                    # Timeout más largo: 120 segundos para todos los EOTs
                    timeout_segundos = max(60, len(eot_ids) * 3)  # 3 segundos por EOT, mínimo 60
                    response = requests.post(f"{API_URL}/performance", json=payload, timeout=timeout_segundos)
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.Timeout:
                    if intento < max_retries - 1:
                        print(f"  ⚠ Timeout en intento {intento + 1}/{max_retries}, reintentando...")
                        continue
                    else:
                        print(f"  ✗ Timeout después de {max_retries} intentos (timeout configurado: {timeout_segundos}s)")
                        return None
                except requests.exceptions.RequestException as e:
                    print(f"  ✗ Error consultando API de performance para {fecha}: {e}")
                    return None
            
    except Exception as e:
        print(f"  ✗ Error inesperado obteniendo datos de performance: {e}")
        traceback.print_exc()
        return None


def save_ifo_historico(resultados_ifo):
    """
    Guarda resultados de IFO en la base de datos a través de la API.
    
    Args:
        resultados_ifo: Lista de diccionarios con los datos a guardar
    
    Returns:
        dict: Respuesta de la API con cantidad de registros guardados/actualizados
    """
    try:
        payload = {
            "resultados": [
                {
                    "id_eot_vmt_hex": r["id_eot_vmt_hex"],
                    "fecha": r["fecha"].strftime("%Y-%m-%d"),
                    "id_franja": r["id_franja"],
                    "ifo": r["ifo"],
                    "ifo_minimo": r["ifo_minimo"],
                    "cbd_indice": r["cbd_indice"],
                    "cbd_cantidad": r["cbd_cantidad"]
                }
                for r in resultados_ifo
            ]
        }
        # Timeout basado en la cantidad de registros
        timeout_segundos = max(60, len(resultados_ifo) * 2)  # 2 segundos por registro, mínimo 60
        response = requests.post(f"{API_URL}/performance/save-ifo", json=payload, timeout=timeout_segundos)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error guardando resultados en la API: {e}")
        return None


def procesar_fecha(fecha: date, modo_notificacion: str = None):
    """
    Procesa una fecha específica: obtiene datos de la API, guarda en BD y detecta incumplimientos.
    """
    try:
        # 1. Obtener EOTs desde la API
        eots_list = get_eots()
        if not eots_list:
            print(f"  ✗ No se pudieron obtener EOTs de la API")
            return
        
        eot_ids = [e['cod_catalogo'] for e in eots_list]
        print(f"  EOTs a procesar: {len(eot_ids)}")
        
        # 2. Obtener datos de performance desde la API
        data = get_performance_data(fecha, eot_ids)
        if not data:
            print(f"  ✗ No se pudieron obtener datos de performance de la API")
            return
        
        tipo_dia = data.get('tipo_dia', 'Desconocido')
        print(f"  Tipo de día: {tipo_dia}")
        
        # 3. Crear diccionario para mapear cod_catalogo a id_eot_vmt_hex
        eot_map = {eot['cod_catalogo']: eot.get('id_eot_vmt_hex') for eot in eots_list}
        
        # 4. Procesar cada EOT y cada franja
        resultados_para_guardar = []
        
        for eot_result in data.get('resultados_eots', []):
            eot_id = eot_result['eot_id']
            eot_nombre = eot_result['eot_nombre']
            id_eot_vmt_hex = eot_map.get(eot_id)
            
            if not id_eot_vmt_hex:
                print(f"  ⚠ EOT {eot_id} ({eot_nombre}) no tiene id_eot_vmt_hex, saltando...")
                continue
            
            for franja_result in eot_result.get('resultados_franjas', []):
                id_franja = franja_result['id_franja']
                denominacion_franja = franja_result['denominacion_franja']
                ifo_val = franja_result['ifo_franja_calculado']
                ifo_min_pct = franja_result.get('ifo_minimo_exigido', 80.0)
                
                # Agregar a la lista para guardar
                resultados_para_guardar.append({
                    'id_eot_vmt_hex': id_eot_vmt_hex,
                    'fecha': fecha,
                    'id_franja': id_franja,
                    'ifo': ifo_val,
                    'cbd_indice': franja_result['cbd_cumplimiento_franja_indice'],
                    'cbd_cantidad': int(franja_result['cbd_obs_promedio']),
                    'ifo_minimo': ifo_min_pct
                })
                
                # Detectar incumplimientos para notificaciones
                # Si es modo verificación (Director), incluimos todo. Si es notificación (Empresa), solo incumplimientos.
                es_incumplimiento = ifo_val < ifo_min_pct
                incluir_en_reporte = es_incumplimiento or (modo_notificacion == 'verificacion')

                if incluir_en_reporte:
                    datos_incumplimientos.append({
                        'eot_nombre': eot_nombre,
                        'eot_id': eot_id,
                        'eot_vmt_hex': id_eot_vmt_hex,
                        'linea_ramal': f"Cat: {eot_id}",
                        'indicador': 'IFO Franja',
                        'franja_horaria': denominacion_franja,
                        'id_franja': id_franja,
                        'umbral_requerido': f"{ifo_min_pct:.0f}%",
                        'valor_observado': f"{ifo_val:.1f}%",
                        'tipo_infraccion': franja_result.get('ifo_estado_cumplimiento', 'IFO Insuficiente'),
                        'normativa': 'Res. 120/2025',
                        'ajuste_aplicado': franja_result.get('ajuste_aplicado', '')
                    })
        
        # 5. Guardar resultados en la BD a través de la API
        if resultados_para_guardar:
            resultado_guardado = save_ifo_historico(resultados_para_guardar)
            if resultado_guardado:
                print(f"  ✓ Guardados: {resultado_guardado['guardados']} nuevos, "
                      f"{resultado_guardado['actualizados']} actualizados "
                      f"(total: {resultado_guardado['total']})")
            else:
                print(f"  ✗ No se pudieron guardar los resultados")
        else:
            print(f"  ⚠ No hay resultados para guardar")
        
        if datos_incumplimientos:
            print(f"  ⚠ {len(datos_incumplimientos)} incumplimientos detectados")
        
    except Exception as e:
        print(f"  ✗ Error procesando fecha {fecha}: {e}")
        traceback.print_exc()
        raise


def enviar_notificaciones(datos_incumplimientos: list, fecha: date, modo: str):
    """
    Envía notificaciones según el modo:
    - --notificacion: envía a cada empresa con incumplimientos (requiere BD para obtener emails)
    - --verificacion: envía solo al director
    """
    if modo == 'notificacion':
        # Agrupar por EOT
        eots_incumplimientos = {}
        for inc in datos_incumplimientos:
            eot_vmt_hex = inc['eot_vmt_hex']
            if eot_vmt_hex not in eots_incumplimientos:
                eots_incumplimientos[eot_vmt_hex] = {
                    'eot_nombre': inc['eot_nombre'],
                    'eot_id': inc['eot_id'],
                    'incumplimientos': []
                }
            eots_incumplimientos[eot_vmt_hex]['incumplimientos'].append(inc)
        
        # Obtener emails de las empresas desde la BD (solo para notificaciones)
        print(f"\n  Enviando notificaciones a {len(eots_incumplimientos)} empresas...")
        
        # Obtener emails de las empresas desde la BD (solo si get_db_connection está disponible)
        try:
            import psycopg2
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                tareas_envio = []
                
                # 1. Recolectar emails (rápido, secuencial)
                print("  Recopilando emails de empresas...")
                for eot_vmt_hex, data in eots_incumplimientos.items():
                    email_eot = None
                    try:
                        cursor.execute("""
                            SELECT email FROM public.eots 
                            WHERE id_eot_vmt_hex = %s AND email IS NOT NULL
                        """, (eot_vmt_hex,))
                        result = cursor.fetchone()
                        email_eot = result[0] if result else None
                    except (Exception, psycopg2.Error):
                        pass
                    
                    if email_eot:
                        tareas_envio.append({
                            'eot_vmt_hex': eot_vmt_hex,
                            'data': data,
                            'email': email_eot
                        })
                    else:
                        print(f"    ⚠ {data['eot_nombre']}: {len(data['incumplimientos'])} incumplimientos - Sin email configurado")
                
                cursor.close()
                conn.close()
                
                # 2. Enviar correos en paralelo
                def procesar_envio(tarea):
                    try:
                        incumplimientos_eot = tarea['data']['incumplimientos']
                        enviar_informe_incumplimientos(incumplimientos_eot, fecha)
                        return f"    ✓ {tarea['data']['eot_nombre']}: {len(incumplimientos_eot)} incumplimientos - Enviado a {tarea['email']}"
                    except Exception as e:
                        return f"    ✗ {tarea['data']['eot_nombre']}: Error enviando - {e}"

                if tareas_envio:
                    print(f"  Iniciando envío paralelo a {len(tareas_envio)} empresas con 6 workers...")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                        futures = [executor.submit(procesar_envio, tarea) for tarea in tareas_envio]
                        for future in concurrent.futures.as_completed(futures):
                            print(future.result())
                else:
                    print("  No hay correos para enviar.")

            else:
                print("  ⚠ No se pudo conectar a la BD para obtener emails de empresas")

        except ImportError:
            print("  ⚠ psycopg2 no disponible. No se pueden obtener emails de empresas desde BD")
        except Exception as e:
            print(f"  ⚠ Error obteniendo emails de empresas: {e}")
        
    elif modo == 'verificacion':
        # Enviar consolidado al director
        print(f"\n  Enviando informe consolidado al director...")
        if datos_incumplimientos:
            try:
                enviar_informe_incumplimientos(datos_incumplimientos, fecha)
                print(f"  ✓ Informe enviado correctamente")
            except Exception as e:
                print(f"  ✗ Error enviando informe: {e}")


def main():
    parser = argparse.ArgumentParser(description='Cálculo IFO Res 120/2025 - Usa API del backend')
    parser.add_argument('--fecha', type=str, help='YYYY-MM-DD')
    parser.add_argument('--desde', type=str, help='YYYY-MM-DD')
    parser.add_argument('--hasta', type=str, help='YYYY-MM-DD')
    parser.add_argument('--notificacion', action='store_true', 
                       help='Envía notificación a cada empresa con incumplimientos')
    parser.add_argument('--verificacion', action='store_true',
                       help='Envía informe consolidado al director')
    args = parser.parse_args()
    
    if args.fecha:
        start = end = datetime.strptime(args.fecha, '%Y-%m-%d').date()
    elif args.desde and args.hasta:
        start = datetime.strptime(args.desde, '%Y-%m-%d').date()
        end = datetime.strptime(args.hasta, '%Y-%m-%d').date()
    else:
        start = end = date.today() - timedelta(days=1)
    
    modo_notificacion = None
    if args.notificacion:
        modo_notificacion = 'notificacion'
    elif args.verificacion:
        modo_notificacion = 'verificacion'
    
    print(f"=== Cálculo IFO Res 120/2025 ===")
    print(f"API: {API_BASE_URL}")
    print(f"Fechas: {start} a {end}")
    print(f"Modo: {modo_notificacion if modo_notificacion else 'Solo cálculo (sin notificaciones)'}")
    print()
    
    # Verificar que la API esté disponible
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API disponible")
        else:
            print(f"⚠ API respondió con código {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ No se pudo conectar a la API en {API_BASE_URL}")
        print(f"  Asegúrese de que el backend esté ejecutándose")
        sys.exit(1)
    
    try:
        # Procesar cada fecha
        delta = end - start
        for i in range(delta.days + 1):
            dia = start + timedelta(days=i)
            print(f"\nProcesando fecha: {dia}")
            datos_incumplimientos.clear()  # Limpiar para cada fecha
            
            procesar_fecha(dia, modo_notificacion)
            
            # Enviar notificaciones si corresponde
            if modo_notificacion and datos_incumplimientos:
                enviar_notificaciones(datos_incumplimientos, dia, modo_notificacion)
        
        print(f"\n=== Proceso completado ===")
        
    except Exception as e:
        print(f"\n✗ Error en el proceso: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
