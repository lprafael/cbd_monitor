"""
Script para calcular IFO según Resolución 120/2025 y guardar resultados en base de datos.
Usa la API del backend para los cálculos y para guardar en control_metricas.ifo_historico.

EJEMPLOS DE USO:
---------------

# 1. Calcular y guardar para el día de ayer (sin notificaciones)
python calcular_ifo.py

# 2. Calcular y guardar para una fecha específica
python calcular_ifo.py --fecha 2026-01-14

# 3. Calcular y guardar para un rango de fechas
python calcular_ifo.py --desde 2026-01-14 --hasta 2026-01-14

# 4. Calcular, guardar y enviar notificación a cada empresa con incumplimientos
python calcular_ifo.py --fecha 2026-01-14 --notificacion

# 5. Calcular, guardar y enviar informe consolidado al director
python calcular_ifo.py --fecha 2026-01-14 --verificacion

# 6. Procesar rango de fechas y enviar notificaciones a empresas
python calcular_ifo.py --desde 2026-01-14 --hasta 2026-01-14 --notificacion

# 7. Procesar rango y enviar informe al director
python calcular_ifo.py --desde 2026-01-14 --hasta 2026-01-14 --verificacion

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
import time

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

# Configuración de procesamiento
TAMANO_LOTE = 50  # Aumentado para aprovechar la optimización de batch del backend
MAX_WORKERS = 3   # Menos workers para no saturar la BD, ya que cada batch es más eficiente

datos_incumplimientos = []


ALERTA_GENERADA = False

def registrar_ejecucion_correcta(id_script: int = 4):
    """
    Registra una ejecución correcta en la tabla alertas.registro_ejecuciones.
    Requiere conexión a BD (get_db_connection); si no hay .env/DB_* no se guarda.
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("  ⚠ No se pudo conectar a la BD para registrar en alertas.registro_ejecuciones (verifique DB_HOST, DB_NAME, etc. en backend/.env o res_120/.env)")
            return

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alertas.registro_ejecuciones 
            (id_script, fecha_ejecucion, estado, detalles)
            VALUES (%s, NOW(), %s, %s)
        """, (id_script, 'OK', 'Ejecución completada correctamente'))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("  ℹ Ejecución registrada en alertas.registro_ejecuciones")

    except Exception as e:
        print(f"  ⚠ Error al registrar ejecución en BD: {e}")


def registrar_alerta(descripcion: str, id_tipo_alerta: int = 1):
    """
    Registra una alerta en la tabla alertas.control_alertas cuando ocurre un error.
    
    Args:
        descripcion: Descripción del error/incidente
        id_tipo_alerta: ID del tipo de alerta (por defecto 1)
    """
    global ALERTA_GENERADA
    ALERTA_GENERADA = True
    try:
        conn = get_db_connection()
        if not conn:
            print(f"  ⚠ No se pudo conectar a BD para registrar alerta: {descripcion[:50]}...")
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alertas.control_alertas 
            (fuente, fechahora_alerta, id_tipo_alerta, verificado, corregido, descripcion_incidente)
            VALUES (%s, NOW(), %s, false, false, %s)
        """, ('script_calcular_ifo.py', id_tipo_alerta, descripcion))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"  ℹ Alerta registrada en control_alertas")
        return True
    except Exception as e:
        print(f"  ⚠ Error al registrar alerta en BD: {e}")
        return False


def verificar_dependencias():
    """
    Verifica si los scripts 1, 2 y 3 se ejecutaron correctamente hoy.
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("  ⚠ No se pudo conectar a BD para verificar dependencias (scripts 1, 2, 3)")
            # Si no hay conexión, asumimos que no se puede verificar y por seguridad retornamos False
            # según el requerimiento estricto del usuario.
            return False
        
        cursor = conn.cursor()
        # Verificar scripts 1, 2 y 3
        cursor.execute("""
            SELECT COUNT(DISTINCT id_script)
            FROM alertas.registro_ejecuciones
            WHERE id_script IN (1, 2, 3)
            AND fecha_ejecucion::date = CURRENT_DATE
            AND estado = 'OK'
        """)
        resultado = cursor.fetchone()
        cantidad = resultado[0] if resultado else 0
        
        cursor.close()
        conn.close()
        
        if cantidad >= 3:
            print("  ✓ Dependencias verificadas: Scripts 1, 2 y 3 ejecutados hoy.")
            return True
        else:
            print(f"  ⚠ Dependencias NO cumplidas: Solo {cantidad}/3 scripts (1,2,3) ejecutados hoy.")
            print("      El script no se ejecutará hasta que se completen las dependencias.")
            return False
            
    except Exception as e:
        print(f"  ⚠ Error verificando dependencias: {e}")
        return False


def get_eots():
    """Obtiene la lista de EOTs desde la API."""
    try:
        response = requests.get(f"{API_URL}/eots", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error obteniendo EOTs de la API: {e}. API URL: {API_BASE_URL}"
        print(f"✗ {error_msg}")
        print(f"  Verifique que la API esté ejecutándose en {API_BASE_URL}")
        registrar_alerta(error_msg)
        return None


def get_performance_data(fecha, eot_ids, max_retries=2):
    """
    Obtiene datos de performance desde la API para una fecha y lista de EOTs.
    Procesa en lotes para evitar timeouts y saturación.
    """
    try:
        # Si hay muchos EOTs, procesar en lotes
        if len(eot_ids) > TAMANO_LOTE:
            print(f"  Procesando {len(eot_ids)} EOTs en lotes de {TAMANO_LOTE}...")
            resultados_combinados = {
                'fecha_analisis': fecha,
                'tipo_dia': None,
                'resultados_eots': []
            }
            
            def procesar_lote(lote_actual, num_lote):
                for intento in range(max_retries):
                    try:
                        payload = {
                            "fecha": fecha.strftime("%Y-%m-%d"),
                            "eot_ids": lote_actual
                        }
                        # Timeout para batch: 150 segundos
                        response = requests.post(f"{API_URL}/performance", json=payload, timeout=150)
                        
                        if response.status_code != 200:
                            print(f"      ⚠ Lote {num_lote} (intento {intento+1}): Server Error {response.status_code}")
                            if intento < max_retries - 1: continue
                            return None
                            
                        return response.json()
                    except requests.exceptions.Timeout:
                        print(f"      ⚠ Lote {num_lote} (intento {intento+1}): Timeout")
                        if intento < max_retries - 1: continue
                    except Exception as e:
                        print(f"      ✗ Lote {num_lote}: Error inesperado: {e}")
                        break
                return None

            lotes = [eot_ids[i:i + TAMANO_LOTE] for i in range(0, len(eot_ids), TAMANO_LOTE)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Pasar el número de lote para mejor logging
                future_to_lote = {executor.submit(procesar_lote, lote, i+1): i for i, lote in enumerate(lotes)}
                
                for future in concurrent.futures.as_completed(future_to_lote):
                    i = future_to_lote[future]
                    try:
                        data_lote = future.result()
                        if data_lote:
                            print(f"    ✓ Lote {i+1}/{len(lotes)} procesado con éxito")
                            if resultados_combinados['tipo_dia'] is None:
                                resultados_combinados['tipo_dia'] = data_lote.get('tipo_dia')
                            resultados_combinados['resultados_eots'].extend(data_lote.get('resultados_eots', []))
                        else:
                            error_msg = f"Lote {i+1}/{len(lotes)} falló definitivamente en fecha {fecha}"
                            print(f"    ✗ {error_msg}")
                            registrar_alerta(error_msg)
                    except Exception as exc:
                        error_msg = f"Excepción en Lote {i+1} ({fecha}): {exc}"
                        print(f"    ✗ {error_msg}")
                        registrar_alerta(error_msg)

            return resultados_combinados
        else:
            # Procesar todos los EOTs de una vez
            for intento in range(max_retries):
                try:
                    payload = {
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "eot_ids": eot_ids
                    }
                    # Timeout dinámico: 60s base + 2s por EOT
                    timeout_segundos = 60 + (len(eot_ids) * 2)
                    response = requests.post(f"{API_URL}/performance", json=payload, timeout=timeout_segundos)
                    
                    if response.status_code == 200:
                        return response.json()
                    else:
                        print(f"  ⚠ Intento {intento+1}: Error API {response.status_code}")
                except requests.exceptions.Timeout:
                    print(f"  ⚠ Intento {intento+1}: Timeout ({timeout_segundos}s)")
                except Exception as e:
                    print(f"  ⚠ Intento {intento+1}: Error - {e}")
                
                if intento < max_retries - 1:
                    time.sleep(2) # Pequeña espera antes de reintentar
                else:
                    error_msg = f"Fallo total obteniendo performance para {fecha} después de {max_retries} intentos"
                    print(f"  ✗ {error_msg}")
                    registrar_alerta(error_msg)
            return None
            
    except Exception as e:
        error_msg = f"Error general en get_performance_data: {e}"
        print(f"  ✗ {error_msg}")
        traceback.print_exc()
        registrar_alerta(error_msg)
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
        error_msg = f"Error guardando resultados en la API: {e}"
        print(f"  ✗ {error_msg}")
        registrar_alerta(error_msg)
        return None


def procesar_fecha(fecha: date, modo_notificacion: str = None):
    """
    Procesa una fecha específica: obtiene datos de la API, guarda en BD y detecta incumplimientos.
    """
    inicio_calculo = time.time()
    try:
        # 1. Obtener EOTs desde la API
        eots_list = get_eots()
        if not eots_list:
            error_msg = f"No se pudieron obtener EOTs de la API para fecha {fecha}"
            print(f"  ✗ {error_msg}")
            registrar_alerta(error_msg)
            return
        
        eot_ids = [e['cod_catalogo'] for e in eots_list]
        print(f"  EOTs a procesar: {len(eot_ids)}")
        
        # 2. Obtener datos de performance desde la API
        data = get_performance_data(fecha, eot_ids)
        if not data:
            error_msg = f"No se pudieron obtener datos de performance de la API para fecha {fecha}"
            print(f"  ✗ {error_msg}")
            registrar_alerta(error_msg)
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
                # Si es modo notificación o verificación, incluimos a todos (antes se filtraba solo incumplimientos)
                incluir_en_reporte = (modo_notificacion is not None) or es_incumplimiento

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
                        'ajuste_aplicado': franja_result.get('ajuste_aplicado', ''),
                        'factor_ajuste': franja_result.get('b_dist_ajustado', 1.0)
                    })
        
        # 5. Guardar resultados en la BD a través de la API
        if resultados_para_guardar:
            resultado_guardado = save_ifo_historico(resultados_para_guardar)
            if resultado_guardado:
                print(f"  ✓ Guardados: {resultado_guardado['guardados']} nuevos, "
                      f"{resultado_guardado['actualizados']} actualizados "
                      f"(total: {resultado_guardado['total']})")
            else:
                error_msg = f"No se pudieron guardar los resultados de IFO para fecha {fecha}"
                print(f"  ✗ {error_msg}")
                registrar_alerta(error_msg)
        else:
            print(f"  ⚠ No hay resultados para guardar")
        
        if datos_incumplimientos:
            print(f"  ⚠ {len(datos_incumplimientos)} incumplimientos detectados")
            
        fin_calculo = time.time()
        print(f"  ⏱ Tiempo de cálculo y guardado: {fin_calculo - inicio_calculo:.2f} segundos")
        
    except Exception as e:
        error_msg = f"Error procesando fecha {fecha}: {e}"
        print(f"  ✗ {error_msg}")
        traceback.print_exc()
        registrar_alerta(error_msg)
        raise


import random

def enviar_notificaciones(datos_incumplimientos: list, fecha: date, modo: str):
    """
    Envía notificaciones según el modo:
    - --notificacion: envía a cada empresa con incumplimientos (requiere BD para obtener emails)
    - --verificacion: envía solo al director (consolidado + 1 simulación aleatoria)
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
                            SELECT e_mail FROM public.eots 
                            WHERE id_eot_vmt_hex = %s AND e_mail IS NOT NULL
                            AND cod_catalogo NOT IN (75)
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
                        # CORRECCIÓN: Pasar el email_destino de la tarea y enviar_cc=False (particular)
                        if enviar_informe_incumplimientos(incumplimientos_eot, fecha, email_destino=tarea['email'], incluir_resumen_infracciones=False, enviar_cc=False):
                            return f"    ✓ {tarea['data']['eot_nombre']}: {len(incumplimientos_eot)} incumplimientos - Enviado a {tarea['email']}"
                        else:
                            return f"    ✗ {tarea['data']['eot_nombre']}: Falló el envío a {tarea['email']}"
                    except Exception as e:
                        return f"    ✗ {tarea['data']['eot_nombre']}: Error enviando - {e}"

                if tareas_envio:
                    print(f"  Iniciando envío paralelo a {len(tareas_envio)} empresas con 6 workers...")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                        futures = [executor.submit(procesar_envio, tarea) for tarea in tareas_envio]
                        for future in concurrent.futures.as_completed(futures):
                            print(future.result())
                    
                    # ADICIÓN: Enviar también el consolidado al Director con CC
                    print(f"\n  Enviando copia del informe consolidado al Director (con CC)...")
                    enviar_informe_incumplimientos(datos_incumplimientos, fecha, incluir_resumen_infracciones=True, enviar_cc=True)
                else:
                    print("  No hay correos para enviar.")

            else:
                print("  ⚠ No se pudo conectar a la BD para obtener emails de empresas")

        except ImportError:
            print("  ⚠ psycopg2 no disponible. No se pueden obtener emails de empresas desde BD")
        except Exception as e:
            print(f"  ⚠ Error obteniendo emails de empresas: {e}")
        
    elif modo == 'verificacion':
        # 1. Enviar consolidado al director
        print(f"\n  Enviando informe consolidado al director...")
        director_email = os.getenv('EMAIL_TO', 'transporte.mopc@gmail.com')

        if datos_incumplimientos:
            try:
                # Add SMTP server info print before attempting to send
                print(f"  Enviando informe consolidado al director ({director_email})...")
                # Assuming SMTP_SERVER and SMTP_PORT are imported or globally available
                # If not, this line might cause a NameError.
                # For this file, we'll assume they are accessible, as per the instruction.
                print(f"    - Servidor SMTP: {os.getenv('SMTP_SERVER')}:{os.getenv('SMTP_PORT')}") # Assuming these are env vars
                if enviar_informe_incumplimientos(datos_incumplimientos, fecha, enviar_cc=True):
                    print(f"  ✓ Informe consolidado enviado correctamente")
                else:
                    print(f"  ✗ Falló el envío del informe consolidado")

                # 2. Enviar simulación de una empresa aleatoria (Solo al director)
                # Agrupar por EOT para elegir una
                eots_disponibles = list(set(d['eot_vmt_hex'] for d in datos_incumplimientos))
                
                if eots_disponibles:
                    eot_random_hex = random.choice(eots_disponibles)
                    incumplimientos_random = [d for d in datos_incumplimientos if d['eot_vmt_hex'] == eot_random_hex]
                    nombre_empresa = incumplimientos_random[0]['eot_nombre']
                    
                    print(f"  Enviando simulación de empresa ({nombre_empresa}) al Director ({director_email})...")
                    if enviar_informe_incumplimientos(incumplimientos_random, fecha, email_destino=director_email, incluir_resumen_infracciones=False, enviar_cc=True):
                        print(f"  ✓ Simulación enviada correctamente")
                    else:
                        print(f"  ✗ Falló el envío de la simulación")
                
            except Exception as e:
                print(f"  ✗ Error enviando informes: {e}")


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
    
    
    # Verificar dependencias antes de procesar
    if not verificar_dependencias():
        msg = "El script no se ejecutó debido a que los scripts necesarios no se ejecutaron previamente el día de hoy"
        # Usamos id_tipo_alerta=2 para advertencias de flujo/dependencias si se desea distinguir, 
        # pero por defecto se usa 1 (Error). El usuario no especificó ID, usaremos el default o uno genérico.
        # Usaré el default (1) ya que interrumpe el proceso esperado.
        registrar_alerta(msg)
        print(f"  ⚠ Alerta generada: {msg}")
        sys.exit(0)
    
    try:
        inicio_total = time.time()
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
        
        fin_total = time.time()
        print(f"\n=== Proceso completado en {fin_total - inicio_total:.2f} segundos ===")
        
        # Si no hubo alertas, registrar ejecución correcta (ID script 4)
        if not ALERTA_GENERADA:
            registrar_ejecucion_correcta(id_script=4)
        
    except Exception as e:
        error_msg = f"Error crítico en el proceso de cálculo IFO: {e}"
        print(f"\n✗ {error_msg}")
        traceback.print_exc()
        registrar_alerta(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Error fatal en script calcular_ifo.py: {e}"
        traceback.print_exc()
        registrar_alerta(error_msg)
        sys.exit(1)
