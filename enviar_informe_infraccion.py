import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
import psycopg2
from typing import Optional, Dict, Any

def get_db_connection():
    """Establece conexión con la base de datos"""
    # Buscar .env en backend/.env primero, luego en el directorio actual
    import os as os_module
    from pathlib import Path
    
    # Obtener la ruta del directorio actual (res_120)
    current_dir = Path(__file__).parent.absolute()
    # Ir al directorio padre y luego a backend
    backend_env = current_dir.parent / 'backend' / '.env'
    local_env = current_dir / '.env'
    
    # Intentar cargar desde backend/.env primero
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    elif local_env.exists():
        load_dotenv(dotenv_path=local_env)
    else:
        # Último recurso: buscar en cualquier parte
        load_dotenv()
    
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '2026'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"✗ Error al conectar a la base de datos: {e}")
        return None

def formatear_fecha_con_dia(fecha_obj):
    """
    Formatea una fecha al formato: "Lun, 07-01-2026"
    
    Args:
        fecha_obj: Objeto date
    
    Returns:
        str: Fecha formateada
    """
    from datetime import date
    dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    dia_semana = dias_semana[fecha_obj.weekday()]
    return f"{dia_semana}, {fecha_obj.strftime('%d-%m-%Y')}"


def get_tipo_dia_id(fecha_obj):
    """
    Determinar el id_tipo_dia basado en la fecha.
    
    Args:
        fecha_obj: Objeto date
    
    Returns:
        int: ID del tipo de día (5=LABORAL, 6=SABADO, 7=NO LABORAL)
    """
    from datetime import date
    conn = get_db_connection()
    if not conn:
        # Fallback sin BD: usar solo día de semana
        dia_semana = fecha_obj.weekday()
        if dia_semana == 5:  # Sábado
            return 6
        elif dia_semana == 6:  # Domingo
            return 7
        else:  # Lunes a Viernes
            return 5
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT fecha FROM public.feriados WHERE fecha = %s", (fecha_obj,))
        es_feriado = cur.fetchone() is not None
        cur.close()
        conn.close()
        
        dia_semana = fecha_obj.weekday()
        
        if es_feriado or dia_semana == 6:  # Domingo o Feriado
            return 7  # NO LABORAL
        elif dia_semana == 5:  # Sábado
            return 6  # SABADO
        else:  # Lunes a Viernes
            return 5  # LABORAL
    except:
        if conn:
            conn.close()
        # Fallback
        dia_semana = fecha_obj.weekday()
        if dia_semana == 5:
            return 6
        elif dia_semana == 6:
            return 7
        else:
            return 5


def obtener_datos_mensuales_eot(id_eot_vmt_hex: str, fecha_referencia: date):
    """
    Obtiene los datos mensuales de IFO para un EOT desde el primer día del mes hasta la fecha de referencia.
    Agrupa los datos por tipo de día (Laboral, Sábado, Domingo).
    También obtiene el índice CBD para cada franja desde la API.
    
    Returns:
        dict: {
            'tipos_dia': {
                5: {  # LABORAL
                    'nombre': 'Día Laboral',
                    'franjas': {id_franja: nombre_franja},
                    'dias': {fecha: {'franjas': {...}, 'ifo_diario': ...}}
                },
                6: {  # SABADO
                    'nombre': 'Sábado',
                    'franjas': {id_franja: nombre_franja},
                    'dias': {fecha: {'franjas': {...}, 'ifo_diario': ...}}
                },
                7: {  # NO LABORAL
                    'nombre': 'Domingo',
                    'franjas': {id_franja: nombre_franja},
                    'dias': {fecha: {'franjas': {...}, 'ifo_diario': ...}}
                }
            },
            'ifo_mes': promedio del IFO mensual
        }
    """
    conn = get_db_connection()
    if not conn:
        print(f"⚠ No se pudo conectar a la BD para obtener datos mensuales del EOT {id_eot_vmt_hex}")
        return None
    
    try:
        import psycopg2.extras
        from psycopg2.extras import RealDictCursor
        import concurrent.futures
        
        # Primer día del mes
        primer_dia_mes = fecha_referencia.replace(day=1)
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener franjas por tipo de día
        tipos_dia_info = {
            5: {'nombre': 'Día Laboral', 'franjas': {}, 'dias': {}},
            6: {'nombre': 'Sábado', 'franjas': {}, 'dias': {}},
            7: {'nombre': 'Domingo', 'franjas': {}, 'dias': {}}
        }
        
        # Obtener franjas para cada tipo de día con información completa
        for id_tipo_dia in [5, 6, 7]:
            cur.execute("""
                SELECT DISTINCT f.id_franja, f.denominacion, f.hora_inicio, f.hora_fin
                FROM control_metricas.franjas_operativas f
                WHERE f.id_tipo_dia = %s
                  AND (f.inicio_vigencia IS NULL OR f.inicio_vigencia <= %s)
                  AND (f.fin_vigencia IS NULL OR f.fin_vigencia >= %s)
                ORDER BY f.hora_inicio
            """, (id_tipo_dia, fecha_referencia, primer_dia_mes))
            franjas_tipo = cur.fetchall()
            franjas_ordenadas = sorted(franjas_tipo, key=lambda x: x['hora_inicio'] if x['hora_inicio'] else '')
            
            # Crear diccionario con información completa de franjas
            franjas_info = {}
            for f in franjas_ordenadas:
                id_franja = f['id_franja']
                # Obtener cbd_minimo_franja desde cbd_parametros_minimos
                cur.execute("""
                    SELECT cbd_minimo_franja
                    FROM control_metricas.cbd_parametros_minimos
                    WHERE id_franja = %s
                      AND id_tipo_dia = %s
                      AND (vigencia_desde IS NULL OR vigencia_desde <= %s)
                      AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
                    ORDER BY vigencia_desde DESC NULLS LAST
                    LIMIT 1
                """, (id_franja, id_tipo_dia, fecha_referencia, primer_dia_mes))
                param_result = cur.fetchone()
                cbd_minimo = param_result['cbd_minimo_franja'] if param_result else None
                
                franjas_info[id_franja] = {
                    'denominacion': f['denominacion'],
                    'hora_inicio': f['hora_inicio'],
                    'hora_fin': f['hora_fin'],
                    'cbd_minimo': cbd_minimo
                }
            
            tipos_dia_info[id_tipo_dia]['franjas'] = franjas_info
        
        # Obtener datos de IFO del mes desde la BD
        cur.execute("""
            SELECT fecha, id_franja, ifo, cbd_indice, cbd_cantidad
            FROM control_metricas.ifo_historico
            WHERE id_eot_vmt_hex = %s 
              AND fecha >= %s 
              AND fecha <= %s
            ORDER BY fecha, id_franja
        """, (id_eot_vmt_hex, primer_dia_mes, fecha_referencia))
        datos_ifo = cur.fetchall()
        
        # Inicializar todas las fechas del mes agrupadas por tipo de día
        from datetime import date, timedelta
        fecha_actual = primer_dia_mes
        while fecha_actual <= fecha_referencia:
            id_tipo_dia = get_tipo_dia_id(fecha_actual)
            if id_tipo_dia in tipos_dia_info:
                tipos_dia_info[id_tipo_dia]['dias'][fecha_actual] = {'franjas': {}, 'ifo_diario': None}
            fecha_actual += timedelta(days=1)
        
        # Organizar datos de IFO por fecha y tipo de día
        for row in datos_ifo:
            fecha = row['fecha']
            id_franja = row['id_franja']
            ifo = row['ifo']
            cbd_idx = row['cbd_indice']
            cbd_cant = row['cbd_cantidad']
            
            id_tipo_dia = get_tipo_dia_id(fecha)
            if id_tipo_dia in tipos_dia_info and fecha in tipos_dia_info[id_tipo_dia]['dias']:
                tipos_dia_info[id_tipo_dia]['dias'][fecha]['franjas'][id_franja] = {
                    'ifo': (float(ifo) * 100) if ifo is not None else 0, # Convertir a porcentaje para visualización 
                    'cbd': float(cbd_idx) if cbd_idx is not None else 0,
                    'cbd_cantidad': int(cbd_cant) if cbd_cant is not None else 0
                }
        
        # Calcular IFO diario promedio usando solo los datos de BD
        for tipo_data in tipos_dia_info.values():
            for fecha, dia_data in tipo_data['dias'].items():
                franjas_dia = dia_data['franjas']
                ifos = [f['ifo'] for f in franjas_dia.values() if f.get('ifo') is not None]
                if ifos:
                    dia_data['ifo_diario'] = sum(ifos) / len(ifos)
        
        # YA NO SE NECESITA LLAMAR A LA API (Optimización completa)
        # Los datos ya se cargaron desde la BD arriba
        print(f"  ✓ Datos obtenidos directamente de BD (optimizado)")
        
        # Calcular IFO MES (promedio de IFO diario del mes, todos los tipos de día)
        ifos_diarios = []
        for tipo_data in tipos_dia_info.values():
            for dia_data in tipo_data['dias'].values():
                if dia_data.get('ifo_diario') is not None:
                    ifos_diarios.append(dia_data['ifo_diario'])
        
        ifo_mes = sum(ifos_diarios) / len(ifos_diarios) if ifos_diarios else 0
        
        # Retornar datos agrupados por tipo de día
        resultado = {
            'tipos_dia': tipos_dia_info,
            'ifo_mes': ifo_mes
        }
        
        total_franjas = sum(len(t['franjas']) for t in tipos_dia_info.values())
        total_dias = sum(len(t['dias']) for t in tipos_dia_info.values())
        print(f"  ✓ Datos mensuales obtenidos para EOT {id_eot_vmt_hex}: {total_franjas} franjas, {total_dias} días, IFO MES: {ifo_mes:.2f}%")
        return resultado
    
    except Exception as e:
        print(f"⚠ Error obteniendo datos mensuales para EOT {id_eot_vmt_hex}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except:
                pass


def obtener_parametros_ifo_resumen(fecha_referencia):
    """
    Obtiene un resumen de los parámetros de IFO vigentes para la fecha de referencia.
    
    Args:
        fecha_referencia (date): Fecha de referencia para obtener los parámetros
    
    Returns:
        str: Texto descriptivo de los parámetros de cumplimiento
    """
    conn = get_db_connection()
    if not conn:
        return "Los incumplimientos para el IFO son sancionables según normativa vigente."
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    f.denominacion,
                    p.porc_cumplimiento_minimo,
                    p.normativa
                FROM control_metricas.parametros_ifo p
                JOIN control_metricas.franjas_operativas f ON p.id_franja_operativa = f.id_franja
                WHERE p.inicio_vigencia <= %s 
                    AND (p.fin_vigencia IS NULL OR p.fin_vigencia >= %s)
                ORDER BY f.denominacion
            """, (fecha_referencia, fecha_referencia))
            
            parametros = cur.fetchall()
            
            if not parametros:
                return "Los incumplimientos para el IFO son sancionables según normativa vigente."
            
            # Agrupar por porcentaje de cumplimiento
            franjas_por_porcentaje = {}
            normativa = None
            
            for franja, porcentaje, norm in parametros:
                if normativa is None:
                    normativa = norm
                if porcentaje not in franjas_por_porcentaje:
                    franjas_por_porcentaje[porcentaje] = []
                franjas_por_porcentaje[porcentaje].append(franja)
            
            # Construir el texto descriptivo
            descripciones = []
            for porcentaje, franjas in sorted(franjas_por_porcentaje.items()):
                franjas_texto = ", ".join(franjas)
                descripciones.append(f"{int(porcentaje)}% en franjas {franjas_texto}")
            
            texto_base = f"Los incumplimientos para el <strong>IFO</strong> son sancionables cuando están por debajo del {' y '.join(descripciones)}."
            
            if normativa:
                texto_base += f" <strong>Base legal:</strong> {normativa}"
            
            return texto_base
    
    except Exception as e:
        print(f"⚠ Error al obtener parámetros IFO: {e}")
        return "Los incumplimientos para el IFO son sancionables según normativa vigente."
    
    finally:
        conn.close()

def obtener_clima(fecha: datetime) -> Optional[Dict[str, Any]]:
    """
    Obtiene datos climáticos históricos para el departamento Central, Paraguay.
    
    Args:
        fecha: Fecha para la que se desea obtener el clima
        
    Returns:
        dict: Datos climáticos o None si hay un error
    """
    # Coordenadas aproximadas del departamento Central, Paraguay
    latitud = -25.3
    longitud = -57.6
    
    # Formatear la fecha para la API
    fecha_str = fecha.strftime("%Y-%m-%d")
    
    try:
        # Parámetros para la API de Open-Meteo
        params = {
            'latitude': latitud,
            'longitude': longitud,
            'start_date': fecha_str,
            'end_date': fecha_str,
            'daily': ['weathercode', 'precipitation_sum', 'windspeed_10m_max'],
            'timezone': 'America/Asuncion',
            'precipitation_unit': 'mm'
        }
        
        # Hacer la petición a la API
        response = requests.get(
            'https://archive-api.open-meteo.com/v1/archive',
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Mapeo de códigos de clima a descripciones e íconos
        weather_codes = {
            0: {'desc': 'Despejado', 'icon': '☀️'},
            1: {'desc': 'Mayormente despejado', 'icon': '🌤️'},
            2: {'desc': 'Parcialmente nublado', 'icon': '⛅'},
            3: {'desc': 'Nublado', 'icon': '☁️'},
            45: {'desc': 'Niebla', 'icon': '🌫️'},
            48: {'desc': 'Niebla con escarcha', 'icon': '❄️🌫️'},
            51: {'desc': 'Llovizna ligera', 'icon': '🌧️'},
            53: {'desc': 'Llovizna moderada', 'icon': '🌧️'},
            55: {'desc': 'Llovizna intensa', 'icon': '🌧️'},
            56: {'desc': 'Llovizna helada ligera', 'icon': '🌨️'},
            57: {'desc': 'Llovizna helada densa', 'icon': '🌨️'},
            61: {'desc': 'Lluvia débil', 'icon': '🌧️'},
            63: {'desc': 'Lluvia moderada', 'icon': '🌧️'},
            65: {'desc': 'Lluvia fuerte', 'icon': '🌧️💦'},
            66: {'desc': 'Lluvia helada', 'icon': '🌨️'},
            67: {'desc': 'Lluvia helada intensa', 'icon': '🌨️💦'},
            71: {'desc': 'Nieve débil', 'icon': '❄️'},
            73: {'desc': 'Nieve moderada', 'icon': '❄️'},
            75: {'desc': 'Nieve fuerte', 'icon': '❄️❄️'},
            77: {'desc': 'Granizo', 'icon': '🌨️'},
            80: {'desc': 'Ligeras precipitaciones', 'icon': '🌧️'},
            81: {'desc': 'Precipitaciones moderadas', 'icon': '🌧️💧'},
            82: {'desc': 'Precipitaciones intensas', 'icon': '🌧️💦'},
            85: {'desc': 'Nevadas ligeras', 'icon': '❄️'},
            86: {'desc': 'Nevadas intensas', 'icon': '❄️❄️'},
            95: {'desc': 'Tormenta eléctrica', 'icon': '⛈️'},
            96: {'desc': 'Tormenta con granizo ligero', 'icon': '⛈️🌨️'},
            99: {'desc': 'Tormenta con granizo fuerte', 'icon': '⛈️🌨️💥'}
        }
        
        # Procesar los datos de la respuesta
        if 'daily' in data and data['daily'] and data['daily']['time']:
            weather_code = data['daily']['weathercode'][0]
            precipitation = data['daily']['precipitation_sum'][0]
            wind_speed = data['daily']['windspeed_10m_max'][0]
            
            weather_info = weather_codes.get(weather_code, {'desc': 'Condición desconocida', 'icon': '❓'})
            return {
                'fecha': fecha_str,
                'descripcion': weather_info['desc'],
                'icono': weather_info['icon'],
                'precipitacion': precipitation,
                'viento': wind_speed,
                'codigo_clima': weather_code
            }
    
    except Exception as e:
        print(f"⚠️ No se pudo obtener datos climáticos: {str(e)}")
    
    return None

def analizar_infracciones_res_120(eot_nombre, datos_mensuales, fecha_referencia):
    """
    Analiza las infracciones según los Artículos 15 y 16 de la Resolución 120/2025.
    Retorna una lista de todas las sanciones detectadas en el mes hasta la fecha_referencia.
    """
    if not datos_mensuales:
        return []

    # Categorización de franjas
    def categorizar(nombre):
        nombre = (nombre or "").upper()
        if "PICO" in nombre and "POS" not in nombre: return "PICO"
        if "POS PICO" in nombre: return "POS_PICO"
        return "OTRO"

    # Agrupar datos por fecha (solo laborales y sábados)
    todas_fechas_dict = {}
    for td_id, td_data in datos_mensuales['tipos_dia'].items():
        if td_id == 7: continue 
        franjas_metadata = td_data['franjas']
        for fecha, d_data in td_data['dias'].items():
            if fecha <= fecha_referencia:
                todas_fechas_dict[fecha] = {'data': d_data, 'metadata': franjas_metadata}
    
    fechas_ordenadas = sorted(todas_fechas_dict.keys())
    
    # Acumuladores y estado
    acum_b = {'PICO': 0, 'POS_PICO': 0}
    historial_faltas = [] # Lista de todas las sanciones detectadas
    
    # Trackers para reincidencia
    ultimo_15_3 = None # Fecha del último Art 15.3 (C Pico)
    ultimo_15_5 = None # Fecha del último Art 15.5 (C PosPico)
    ultimo_15_6 = None # Fecha del último Art 15.6 (ICCBDM)
    
    # Trackers para Art 15.2 -> 16.2 (B Pico)
    trigger_15_2 = False
    acum_b_reinc = 0
    start_reinc_16_2 = None
    trigger_16_2 = False

    # Trackers para Art 15.4 -> 16.4 (B PosPico)
    trigger_15_4 = False
    acum_b_reinc_pos = 0
    start_reinc_16_4 = None
    trigger_16_4 = False

    for fecha in fechas_ordenadas:
        dia_info = todas_fechas_dict[fecha]
        franjas_dia = dia_info['data']['franjas']
        franjas_metadata = dia_info['metadata']
        
        fail_15_3 = False; fail_15_5 = False; fail_15_6 = False
        count_b_pico = 0; count_b_pospico = 0

        for fid, f_res in franjas_dia.items():
            cat = categorizar(franjas_metadata.get(fid, {}).get('denominacion', ''))
            if cat == "OTRO" or f_res.get('ifo') is None: continue
            
            ifo = f_res.get('ifo')
            cbd = f_res.get('cbd')
            
            if cbd is not None and cbd < 1.0: fail_15_6 = True
            
            if cat == 'PICO':
                if ifo < 80: fail_15_3 = True
                elif ifo < 90: 
                    count_b_pico += 1
                    if not trigger_15_2: acum_b['PICO'] += 1
                    elif not trigger_16_2: acum_b_reinc += 1
            elif cat == 'POS_PICO':
                if ifo < 80: fail_15_5 = True
                elif ifo < 90:
                    count_b_pospico += 1
                    if not trigger_15_4: acum_b['POS_PICO'] += 1
                    elif not trigger_16_4: acum_b_reinc_pos += 1

        # EVALUACIÓN DE REGLAS
        # 1. ICCBDM (15.6 / 16.6)
        if fail_15_6:
            if ultimo_15_6 and (fecha - ultimo_15_6).days <= 2:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 16.6', 'desc': 'Reincidencia ICCBDM (2 días)', 'jornales': 45})
            else:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM (Buses Mínimos)', 'jornales': 20})
                ultimo_15_6 = fecha

        # 2. NIVEL C PICO (15.3 / 16.3)
        if fail_15_3:
            if ultimo_15_3 and (fecha - ultimo_15_3).days <= 7:
                # Solo una reincidencia 16.3 al mes según prompt
                if not any(f['base'] == 'Art. 16.3' for f in historial_faltas):
                    historial_faltas.append({'fecha': fecha, 'base': 'Art. 16.3', 'desc': 'Reincidencia Nivel C Pico (7 días)', 'jornales': 45})
            else:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
                ultimo_15_3 = fecha

        # 3. NIVEL C POS PICO (15.5 / 16.5)
        if fail_15_5:
            if ultimo_15_5 and (fecha - ultimo_15_5).days <= 7:
                if not any(f['base'] == 'Art. 16.5' for f in historial_faltas):
                    historial_faltas.append({'fecha': fecha, 'base': 'Art. 16.5', 'desc': 'Reincidencia Nivel C Pos Pico (7 días)', 'jornales': 45})
            else:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})
                ultimo_15_5 = fecha

        # 4. ACUMULACIÓN NIVEL B (15.2 / 16.2 y 15.4 / 16.4)
        if not trigger_15_2 and acum_b['PICO'] >= 5:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.2', 'desc': 'Acumulación 5 Franjas Pico Nivel B', 'jornales': 10})
            trigger_15_2 = True
            start_reinc_16_2 = fecha
        
        if trigger_15_2 and not trigger_16_2 and acum_b_reinc >= 5:
            if (fecha - start_reinc_16_2).days <= 7:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 16.2', 'desc': 'Reincidencia Nivel B Pico (5 adicionales en 7 días)', 'jornales': 20})
                trigger_16_2 = True

        if not trigger_15_4 and acum_b['POS_PICO'] >= 5:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.4', 'desc': 'Acumulación 5 Franjas Pos Pico Nivel B', 'jornales': 10})
            trigger_15_4 = True
            start_reinc_16_4 = fecha

        if trigger_15_4 and not trigger_16_4 and acum_b_reinc_pos >= 5:
            if (fecha - start_reinc_16_4).days <= 7:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 16.4', 'desc': 'Reincidencia Nivel B Pos Pico (5 adicionales en 7 días)', 'jornales': 20})
                trigger_16_4 = True

    # Transformar para el reporte
    sanciones = []
    for f in historial_faltas:
        sanciones.append({
            'fecha': f['fecha'].strftime('%d/%m'),
            'base': f['base'],
            'desc': f['desc'],
            'jornales': f['jornales']
        })
        
    return sanciones

def generar_html_informe(datos_incumplimientos, fecha_referencia):
    """
    Genera el contenido HTML del informe de incumplimientos.
    
    Args:
        datos_incumplimientos (list): Lista de diccionarios con los datos de incumplimientos
        fecha_referencia (date): Fecha de referencia para el informe (D-1)
    
    Returns:
        str: Contenido HTML del informe
    """
    fecha_formato = fecha_referencia.strftime("%Y-%m-%d")
    fecha_envio = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    # Obtener descripción dinámica de parámetros
    nota_parametros = obtener_parametros_ifo_resumen(fecha_referencia)
    
    # Obtener datos climáticos
    datos_clima = obtener_clima(fecha_referencia)
    
    # Generar sección de clima
    seccion_clima = ""
    if datos_clima:
        condiciones_especiales = []
        if datos_clima['precipitacion'] > 5:  # Más de 5mm de lluvia
            precipitacion_icon = '💧' if datos_clima['precipitacion'] < 15 else '💦' if datos_clima['precipitacion'] < 30 else '🌊'
            condiciones_especiales.append(f"{precipitacion_icon} precipitaciones significativas ({datos_clima['precipitacion']}mm)")
        
        if datos_clima['viento'] > 40:  # Vientos fuertes (km/h)
            viento_icon = '💨' if datos_clima['viento'] < 60 else '🌬️' if datos_clima['viento'] < 80 else '🌪️'
            condiciones_especiales.append(f"{viento_icon} vientos fuertes ({datos_clima['viento']} km/h)")
        
        # Ícono principal del clima
        icono_principal = datos_clima.get('icono', '🌡️')
        
        # Construir la nota del clima
        nota_clima = f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 24px; margin-right: 10px;">{icono_principal}</span>
            <div>
                <div>Condiciones: <strong>{datos_clima['descripcion']}</strong></div>
                <div style="font-size: 13px; color: #4b5563;">Precipitación: <strong>{datos_clima['precipitacion']} mm</strong></div>
            </div>
        </div>
        """
        
        # Agregar detalles adicionales si hay condiciones especiales
        if condiciones_especiales:
            detalles = ""
            for condicion in condiciones_especiales:
                detalles += f"<div style='margin: 5px 0;'>{condicion}</div>"
            
            nota_clima += f"""
            <div style="margin-top: 10px; padding: 10px; background-color: rgba(0,0,0,0.05); border-radius: 5px;">
                <div style="font-weight: bold; margin-bottom: 5px;">⚠️ Condiciones especiales:</div>
                {detalles}
                <div style="margin-top: 5px; font-size: 0.9em; color: #666;">
                    Estas condiciones podrían haber afectado la operación del transporte.
                </div>
            </div>
            """
        
        seccion_clima = f"""
        <div class="note" style="background-color: #f8fafc; border-left: 5px solid #4dabf7; border-radius: 5px; padding: 15px; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #1e40af; font-size: 16px;">
                    🌦️ Información Meteorológica - {fecha_formato} (Central, PY)
                </h3>
                <span style="font-size: 12px; color: #4b5563;">Datos de Open-Meteo</span>
            </div>
            {nota_clima}
        </div>
        """

    else:
        seccion_clima = """
        <div class="note" style="background-color: #fff3bf; border-left: 5px solid #ffd43b;">
            <p><strong>Información Meteorológica no disponible</strong></p>
            <p>No se pudieron obtener datos climáticos para la fecha del informe.</p>
        </div>
        """

    # Generar Sección de Ajuste Aplicado (Si existe en los datos)
    seccion_ajuste = ""
    if datos_incumplimientos:
        # Extraemos el ajuste y factor del primer registro
        primer_registro = datos_incumplimientos[0]
        ajuste_texto = primer_registro.get('ajuste_aplicado', 'Ninguno')
        factor_total = primer_registro.get('factor_ajuste', 1.0)
        
        if ajuste_texto and ajuste_texto != 'Ninguno':
            # Determinar si hay múltiples ajustes
            lista_ajustes = [a.strip() for a in ajuste_texto.split(',')]
            hay_multiples = len(lista_ajustes) > 1
            
            tipo_ajuste_clase = "Ajuste por Multiplicidad de Factores" if hay_multiples else "Ajuste Operativo Aplicado"
            
            detalles_ajuste = ""
            for ajuste in lista_ajustes:
                detalles_ajuste += f"<li>{ajuste}</li>"
            
            seccion_ajuste = f"""
            <div class="note" style="background-color: #f0f7ff; border-left: 5px solid #004a99; margin-top: 15px; color: #1e40af; padding: 15px;">
                <div style="display: flex; align-items: start;">
                    <span style="font-size: 24px; margin-right: 12px;">⚖️</span>
                    <div>
                        <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px;">{tipo_ajuste_clase} (Res. GVMT N° 120/2025)</div>
                        <div style="font-size: 13px; line-height: 1.4;">
                            Se ha aplicado una reducción proporcional a la exigencia operativa basal (Promedio Histórico) debido a condiciones externas comprobadas:
                        </div>
                        <ul style="margin: 8px 0; padding-left: 20px; font-size: 12px; color: #334155;">
                            {detalles_ajuste}
                        </ul>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #bfdbfe; font-weight: bold; font-size: 13px;">
                            Factor de Ajuste Total Aplicado: {factor_total:.2f}
                        </div>
                    </div>
                </div>
            </div>
            """
    
    # Agrupar incumplimientos por EOT
    eots_incumplimientos = {}
    for inc in datos_incumplimientos:
        eot_vmt_hex = inc.get('eot_vmt_hex')
        if eot_vmt_hex and eot_vmt_hex not in eots_incumplimientos:
            eots_incumplimientos[eot_vmt_hex] = {
                'eot_nombre': inc.get('eot_nombre', ''),
                'incumplimientos': []
            }
        if eot_vmt_hex:
            eots_incumplimientos[eot_vmt_hex]['incumplimientos'].append(inc)
    
    # Acumulador para el resumen de infracciones (solo si hay datos)
    resumen_infracciones_lista = []
    VALOR_JORNAL = 111502

    # Generar sección por EOT con tabla detalle (Ordenado alfabéticamente)
    secciones_eot_html = ""
    eot_ordenados_keys = sorted(eots_incumplimientos.keys(), key=lambda k: eots_incumplimientos[k]['eot_nombre'])
    
    for eot_vmt_hex in eot_ordenados_keys:
        eot_data = eots_incumplimientos[eot_vmt_hex]
        eot_nombre = eot_data['eot_nombre']
        
        # Obtener datos mensuales del EOT
        try:
            datos_mensuales = obtener_datos_mensuales_eot(eot_vmt_hex, fecha_referencia)
        except Exception as e:
            print(f"⚠ Error obteniendo datos mensuales para {eot_nombre}: {e}")
            datos_mensuales = None
        
        # Analizar infracciones para el resumen (Art 15/16)
        if datos_mensuales:
            inf_detectadas = analizar_infracciones_res_120(eot_nombre, datos_mensuales, fecha_referencia)
            for inf in inf_detectadas:
                resumen_infracciones_lista.append({
                    'empresa': eot_nombre,
                    'fecha': inf['fecha'],
                    'base': inf['base'],
                    'descripcion': inf['desc'],
                    'jornales': inf['jornales'],
                    'monto': inf['jornales'] * VALOR_JORNAL
                })

        if not datos_mensuales:
            # Si no hay datos, mostrar solo el nombre y IFO MES como N/A
            secciones_eot_html += f"""
            <div style="margin-top: 30px; page-break-inside: avoid;">
                <h4 style="color: #004a99; margin-bottom: 10px;">{eot_nombre}</h4>
                <p style="margin-bottom: 10px;"><strong>IFO MES:</strong> N/A</p>
                <p style="color: #666; font-style: italic;">No hay datos disponibles para este período.</p>
            </div>
            """
            continue
        
        ifo_mes = datos_mensuales['ifo_mes']
        tipos_dia = datos_mensuales['tipos_dia']
        
        # Generar sección para este EOT con 3 tablas (una por tipo de día)
        secciones_eot_html += f"""
        <div style="margin-top: 30px; page-break-inside: avoid;">
            <h4 style="color: #004a99; margin-bottom: 10px;">{eot_nombre}</h4>
            <p style="margin-bottom: 15px;"><strong>IFO MES:</strong> {ifo_mes:.2f}%</p>
        """
        
        # Generar tabla para cada tipo de día (5=Laboral, 6=Sábado, 7=Domingo)
        for id_tipo_dia in [5, 6, 7]:
            tipo_data = tipos_dia.get(id_tipo_dia, {'nombre': '', 'franjas': {}, 'dias': {}})
            nombre_tipo = tipo_data['nombre']
            franjas = tipo_data['franjas']
            dias_data = tipo_data['dias']
            
            # Ordenar fechas
            fechas_ordenadas = sorted(dias_data.keys())
            
            if not fechas_ordenadas or not franjas:
                continue  # Saltar si no hay datos para este tipo de día
            
            # Ordenar franjas por hora de inicio para las columnas
            franjas_ids = sorted(franjas.keys(), key=lambda fid: franjas[fid]['hora_inicio'] if franjas[fid]['hora_inicio'] else '')
            encabezado_franjas = ""
            for fid in franjas_ids:
                franja_info = franjas[fid]
                nombre = franja_info['denominacion']
                hora_inicio = franja_info['hora_inicio'].strftime('%H:%M') if franja_info['hora_inicio'] else ''
                hora_fin = franja_info['hora_fin'].strftime('%H:%M') if franja_info['hora_fin'] else ''
                cbd_min = franja_info.get('cbd_minimo', '')
                encabezado_franjas += f"""
                    <th style="border: 1px solid #ccc; padding: 8px; text-align: center; vertical-align: top;">
                        <div style="font-weight: bold;">{nombre}</div>
                        <div style="font-size: 10px; color: #666;">{hora_inicio} - {hora_fin}</div>
                        <div style="font-size: 10px; color: #cc0000;">Mín: {cbd_min if cbd_min else '-'}</div>
                    </th>
                """
            
            # Generar filas de la tabla
            filas_tabla_html = ""
            
            for fecha in fechas_ordenadas:
                fecha_str = formatear_fecha_con_dia(fecha)
                data_dia = dias_data.get(fecha, {'franjas': {}, 'ifo_diario': None})
                ifo_diario = data_dia.get('ifo_diario', 0) if data_dia.get('ifo_diario') is not None else 0
                
                # Fila CBD Cantidad (nueva fila)
                fila_cbd_cant = f"<td rowspan=\"3\" style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">{fecha_str}</td><td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">CBD</td>"
                for fid in franjas_ids:
                    cbd_cant = data_dia['franjas'].get(fid, {}).get('cbd_cantidad')
                    if cbd_cant is not None:
                        fila_cbd_cant += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">{cbd_cant:.0f}</td>"
                    else:
                        fila_cbd_cant += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"
                fila_cbd_cant += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"  # CBD cantidad no tiene promedio diario
                fila_cbd_cant += "</tr>"
                
                # Fila Índice CBD
                fila_cbd = "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">ICCBDM</td>"
                for fid in franjas_ids:
                    cbd_val = data_dia['franjas'].get(fid, {}).get('cbd')
                    if cbd_val is not None:
                        # Formato porcentaje y colores: < 100% rojo, >= 100% verde
                        cbd_pct = cbd_val * 100
                        bg_color = "#e6ffe6" if cbd_val >= 1.0 else "#ffe6e6"  # Verde claro vs Rojo claro
                        color_text = "#006600" if cbd_val >= 1.0 else "#cc0000"
                        fila_cbd += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center; background-color: {bg_color}; color: {color_text};\">{cbd_pct:.0f}%</td>"
                    else:
                        fila_cbd += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"
                fila_cbd += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"  # CBD no tiene promedio diario
                fila_cbd += "</tr>"
                
                # Fila IFO
                fila_ifo = "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">IFO</td>"
                for fid in franjas_ids:
                    ifo_val = data_dia['franjas'].get(fid, {}).get('ifo')
                    if ifo_val is not None:
                        # Colores IFO: >=90 Verde, 80-89 Amarillo, <80 Rojo
                        bg_color = "#e6ffe6" # Verde
                        color_text = "#006600"
                        if ifo_val < 80:
                            bg_color = "#ffe6e6" # Rojo
                            color_text = "#cc0000"
                        elif ifo_val < 90:
                            bg_color = "#ffffe6" # Amarillo
                            color_text = "#999900"
                            
                        fila_ifo += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center; background-color: {bg_color}; color: {color_text};\">{ifo_val:.2f}</td>"
                    else:
                        fila_ifo += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"
                
                # IFO Diario (Promedio) con mismos colores
                if ifo_diario > 0:
                    bg_color_d = "#e6ffe6"
                    color_text_d = "#006600"
                    if ifo_diario < 80:
                        bg_color_d = "#ffe6e6"
                        color_text_d = "#cc0000"
                    elif ifo_diario < 90:
                        bg_color_d = "#ffffe6"
                        color_text_d = "#999900"
                        
                    fila_ifo += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center; background-color: {bg_color_d}; color: {color_text_d};\"><strong>{ifo_diario:.2f}</strong></td>"
                else:
                    fila_ifo += "<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center;\">-</td>"
                fila_ifo += "</tr>"
                
                filas_tabla_html += f"<tr>{fila_cbd_cant}</tr><tr>{fila_cbd}</tr><tr>{fila_ifo}</tr>"
            
            # Construir tabla para este tipo de día
            secciones_eot_html += f"""
            <div style="margin-top: 20px;">
                <h5 style="color: #0066cc; margin-bottom: 10px; font-size: 14px;">{nombre_tipo}</h5>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; overflow-x: auto;">
                    <thead>
                        <tr style="background-color: #d9e3f1;">
                            <th rowspan="2" style="border: 1px solid #ccc; padding: 8px; text-align: center;">Fecha</th>
                            <th rowspan="2" style="border: 1px solid #ccc; padding: 8px; text-align: center;">Métrica</th>
                            <th colspan="{len(franjas_ids)}" style="border: 1px solid #ccc; padding: 8px; text-align: center;">Franjas Operativas</th>
                            <th rowspan="2" style="border: 1px solid #ccc; padding: 8px; text-align: center;">Promedio IFO Diario</th>
                        </tr>
                        <tr style="background-color: #d9e3f1;">
                            {encabezado_franjas}
                        </tr>
                    </thead>
                    <tbody>
                        {filas_tabla_html}
                    </tbody>
                </table>
            </div>
            """
        
        # Cerrar div del EOT
        secciones_eot_html += "</div>"
    
    # Generar filas de la tabla de resumen con subtotales (solo para modo verificación)
    filas_resumen_infracciones_html = ""
    total_general_jornales = 0
    total_general_monto = 0
    
    if resumen_infracciones_lista:
        resumen_infracciones_lista.sort(key=lambda x: x['empresa'])
        empresa_actual = None
        sub_j = 0
        sub_m = 0
        
        for i, inf in enumerate(resumen_infracciones_lista):
            if empresa_actual and inf['empresa'] != empresa_actual:
                filas_resumen_infracciones_html += f"""
                <tr style="background-color: #f1f5f9; font-weight: bold; border-top: 2px solid #1e40af;">
                    <td colspan="4" style="border: 1px solid #ccc; padding: 8px; text-align: right;">Total {empresa_actual}:</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{sub_j}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right;">{sub_m:,.0f}</td>
                </tr>"""
                sub_j, sub_m = 0, 0
            
            empresa_actual = inf['empresa']
            sub_j += inf['jornales']
            sub_m += inf['monto']
            total_general_jornales += inf['jornales']
            total_general_monto += inf['monto']
            
            filas_resumen_infracciones_html += f"""
            <tr>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{inf.get('fecha', '')}</td>
                <td style="border: 1px solid #ccc; padding: 8px;">{inf['empresa']}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center; font-weight: bold;">{inf['base']}</td>
                <td style="border: 1px solid #ccc; padding: 8px;">{inf['descripcion']}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{inf['jornales']}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right;">{inf['monto']:,.0f}</td>
            </tr>"""
            
            if i == len(resumen_infracciones_lista) - 1:
                filas_resumen_infracciones_html += f"""
                <tr style="background-color: #f1f5f9; font-weight: bold; border-top: 2px solid #1e40af;">
                    <td colspan="4" style="border: 1px solid #ccc; padding: 8px; text-align: right;">Total {empresa_actual}:</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{sub_j}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right;">{sub_m:,.0f}</td>
                </tr>"""
    
    # Plantilla HTML completa
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alerta Diaria CID(CCM) - Control de Métricas IFO/ICCBDM</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
                color: #333;
            }}
            .container {{
                width: 100%;
                max-width: 800px;
                margin: 20px auto;
                background-color: #fff;
                border: 1px solid #ddd;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background-color: #004a99;
                color: #fff;
                padding: 15px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .section-title {{
                color: #004a99;
                border-bottom: 2px solid #eee;
                padding-bottom: 5px;
                margin-top: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 12px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #d9e3f1;
                font-weight: bold;
                color: #1a1a1a;
            }}
            .note {{
                margin-top: 20px;
                padding: 10px;
                background-color: #fff3cd;
                border: 1px solid #ffeeba;
                color: #856404;
                border-left: 5px solid #ffc107;
                font-size: 12px;
            }}
            .signature {{
                margin-top: 30px;
                border-top: 1px solid #ccc;
                padding-top: 10px;
                font-size: 12px;
            }}
            .cuerpo-texto {{
                line-height: 1.6;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>VICEMINISTERIO DE TRANSPORTE - CENTRAL DE CONTROL Y MONITOREO (CID-DMT)</h2>
            </div>

            <p style="text-align: right; font-size: 12px;"><strong>ASUNTO:</strong> <strong>REPORTE DIARIO D+1:</strong> Consolidado de las verificaciones (CBD/ICCBDM/IFO) - {fecha_formato}</p>
            <p style="font-size: 12px;"><strong>DE:</strong> Coordinación de Innovación y Desarrollo (CID)</p>
            <p style="font-size: 12px;"><strong>PARA:</strong> Ing. ROLANDO GONZÁLEZ, Director (Dirección Metropolitana de Transporte - DMT)</p>
            <p style="font-size: 12px;"><strong>FECHA:</strong> {fecha_envio}</p>
            # <p style="font-size: 12px;"><strong>CC:</strong> Coordinación de Transporte Área Metropolitana (CTAM), Coordinación Jurídica (GVMT)</p>

            <hr style="border-top: 1px solid #004a99;">

            <div class="cuerpo-texto">
                <p>Estimado Ing. ROLANDO GONZÁLEZ, Director (Dirección Metropolitana de Transporte - DMT):</p>
                <p>La <strong>Coordinación de Innovación y Desarrollo (CID),</strong> a través de la Central de Control y Monitoreo (CCM), eleva el presente <strong>Informe Diario de Control y Monitoreo</strong> correspondiente a la operación del día <strong>{fecha_formato}</strong>.</p>
                
                {seccion_clima}

                {seccion_ajuste}
                
                <p>Este informe se basa en el procesamiento de datos de monitoreo (GPS y billetaje electrónico), conforme a los nuevos conceptos y criterios de desempeño establecidos en la Resolución GVMT N° 120/2025 y el procedimiento correspondiente.</p>

                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0; font-size: 12px;">
                    <h4 style="margin-top: 0; color: #1e40af; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">Glosario y Referencia de Colores</h4>
                    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <strong style="color: #1e40af;">Definiciones:</strong>
                            <ul style="margin: 5px 0; padding-left: 15px; list-style-type: none;">
                                <li><strong>• CBD:</strong> Cantidad de Buses Diferentes (unidades físicas observadas).</li>
                                <li><strong>• ICCBDM:</strong> Índice de Cumplimiento de Cantidad de Buses Diferentes Mínimos.</li>
                                <li><strong>• IFO:</strong> Índice de Flota Operativa (Regularidad de la oferta).</li>
                            </ul>
                        </div>
                        <div style="flex: 1; min-width: 250px;">
                            <strong style="color: #1e40af;">Referencia por Colores:</strong>
                            <div style="margin-top: 5px;">
                                <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                                    <span style="background-color: #e6ffe6; border: 1px solid #b7eb8f; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Verde</span>
                                    <span>Cumplimiento Óptimo (IFO &ge; 90% | ICCBDM &ge; 100%)</span>
                                </div>
                                <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                                    <span style="background-color: #ffffe6; border: 1px solid #ffe58f; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Amarillo</span>
                                    <span>Cumplimiento Regular (IFO 80% - 89%)</span>
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <span style="background-color: #ffe6e6; border: 1px solid #ffa39e; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Rojo</span>
                                    <span>Cumplimiento Crítico / Insuficiente (IFO < 80% | ICCBDM < 100%)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <h3 class="section-title">CONSOLIDADO DE MONITOREOS DIARIOS (CBD/ICCBDM/IFO)</h3>

                {secciones_eot_html}

                <div class="note">
                    <p><strong>Nota:</strong> Los niveles de servicio para el IFO por franja operativa se clasifican y sancionan de la siguiente manera:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>Nivel de Servicio B (Cumplimiento entre 80% y 89%):</strong> Constituye una Infracción Leve (Multa de 10 jornales).</li>
                        <li><strong>Nivel de Servicio C (Cumplimiento inferior al 80%):</strong> Constituye una Infracción Intermedia (Multa de 20 jornales).</li>
                    </ul>
                    <p>Estas disposiciones son aplicables a todas las franjas operativas reguladas: Madrugada, Pico (Mañana y Tarde), Pos Pico (Entre picos y Tarde) y Nocturna para días laborales y sábados; y la franja Pos Pico para domingos y feriados.</p>
                </div>

                <h3 class="section-title">PROCEDIMIENTO Y BASE LEGAL</h3>
                <ul>
                    <li><strong>Alerta Automática:</strong> El sistema ha generado este informe interno de manera automatizada tras la detección de niveles de servicio tipo B o C en la operación evaluada.</li>
                    <li><strong>Generación de Acta:</strong> Tras la validación técnica del incumplimiento, la Coordinación de Innovación y Desarrollo (CID) procederá a la emisión del Acta de Comprobación correspondiente, conforme al Artículo 19.</li>
                    <li><strong>Marco Regulatorio:</strong> Las sanciones y reincidencias se aplicarán estrictamente según lo establecido en el Capítulo IV de la Resolución GVMT N° 120/2025.</li>
                </ul>

                {f'''
                <h3 class="section-title">RESUMEN DE INFRACCIONES DETECTADAS (Mes Actual - Acumulativo)</h3>
                <div style="background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-top: 15px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                        <thead>
                            <tr style="background-color: #1e40af; color: white;">
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: left; width: 80px;">Fecha</th>
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: left;">Empresa / EOT</th>
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: center;">Base Legal</th>
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: left;">Descripción de la Falta</th>
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: center;">Jornales</th>
                                <th style="border: 1px solid #ccc; padding: 8px; text-align: right;">Monto (Gs.)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_resumen_infracciones_html}
                            <tr style="background-color: #334155; color: white; font-weight: bold;">
                                <td colspan="4" style="border: 1px solid #ccc; padding: 8px; text-align: right;">TOTAL GENERAL ESTIMADO (MES):</td>
                                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{total_general_jornales}</td>
                                <td style="border: 1px solid #ccc; padding: 8px; text-align: right;">{total_general_monto:,.0f} Gs.</td>
                            </tr>
                        </tbody>
                    </table>
                    <p style="font-size: 10px; color: #666; margin-top: 10px; font-style: italic;">
                        * El valor del jornal utilizado para el cálculo es de 111,502 Gs. Los montos son estimaciones preliminares sujetas a confirmación técnica.
                    </p>
                </div>
                ''' if resumen_infracciones_lista else ''}
            </div>

            <div class="signature">
                <p>Atentamente,</p>
                <p><strong>Coordinación de Innovación y Desarrollo (CID)</strong><br>Dirección Metropolitana de Transporte (DMT)<br>Viceministerio de Transporte (GVMT)<br>Ministerio de Obras Públicas y Comunicaciones</p>
                <p style="color: #888; margin-top: 10px;">*Este es un mensaje generado automáticamente por el Sistema de Control y Monitoreo (CID/DMT)*</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def enviar_informe_incumplimientos(datos_incumplimientos, fecha_referencia=None):
    """
    Envía por correo electrónico el informe de incumplimientos.
    
    Args:
        datos_incumplimientos (list): Lista de diccionarios con los datos de incumplimientos
        fecha_referencia (date, optional): Fecha de referencia para el informe. Si es None, usa el día anterior.
    """
    # Cargar variables de entorno desde backend/.env
    from pathlib import Path
    current_dir = Path(__file__).parent.absolute()
    backend_env = current_dir.parent / 'backend' / '.env'
    local_env = current_dir / '.env'
    
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    elif local_env.exists():
        load_dotenv(dotenv_path=local_env)
    else:
        load_dotenv()
    
    # Configuración del correo desde .env
    # Configuración de correo
    SMTP_SERVER = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('EMAIL_PORT', 587))
    SMTP_USER = os.getenv('EMAIL_HOST_USER', 'billetajevmt@gmail.com')
    SMTP_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'qlju dhxo jbon exlg')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'billetajevmt@gmail.com')
    EMAIL_TO = os.getenv('EMAIL_TO', 'lprafael1710@gmail.com')
    EMAIL_CC = os.getenv('EMAIL_CC', 'dgeec2011@gmail.com')
    USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        print("✗ Error: Faltan configuraciones de correo electrónico en el archivo .env")
        print(f"SMTP_SERVER: {SMTP_SERVER}")
        print(f"SMTP_USER: {SMTP_USER}")
        print(f"EMAIL_FROM: {EMAIL_FROM}")
        print(f"EMAIL_TO: {EMAIL_TO}")
        print(f"SMTP_PASSWORD: {'*' * 8 if SMTP_PASSWORD else 'No configurada'}")
        return False
    
    # Establecer fecha de referencia (por defecto, el día anterior)
    if fecha_referencia is None:
        fecha_referencia = datetime.now().date() - timedelta(days=1)
    
    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = f'[DMT] Reporte Diario - Métricas IFO/ICCBDM - {fecha_referencia.strftime("%Y-%m-%d")}'
        
        # Generar el contenido HTML del informe
        html_content = generar_html_informe(datos_incumplimientos, fecha_referencia)
        msg.attach(MIMEText(html_content, 'html'))
        
        # Configurar conexión SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        
        # Iniciar conexión segura si es necesario
        if USE_TLS:
            server.starttls()
        
        # Iniciar sesión
        server.login(SMTP_USER, SMTP_PASSWORD.strip())
        
        # Configurar destinatarios
        destinatarios = [EMAIL_TO]
        if EMAIL_CC:
            destinatarios.extend([email.strip() for email in EMAIL_CC.split(',')])
            msg['Cc'] = EMAIL_CC
        
        # Enviar correo
        server.send_message(msg, to_addrs=destinatarios)
        server.quit()
        
        print(f"✓ Correo de incumplimientos enviado correctamente a {EMAIL_TO}")
        return True
    
    except Exception as e:
        print(f"✗ Error al enviar el correo: {str(e)}")
        return False

if __name__ == "__main__":
    # Ejemplo de uso para pruebas
    datos_ejemplo = [
        {
            'eot_nombre': 'EJEMPLO EOT S.A.',
            'linea_ramal': '30-1 LÍNEA EJEMPLO',
            'indicador': 'IFO',
            'franja_horaria': 'Pico Mañana (07:00-09:59)',
            'umbral_requerido': '80%',
            'valor_observado': '65.2',
            'tipo_infraccion': 'Infracción Intermedia'
        },
        {
            'eot_nombre': 'OTRA EOT S.R.L.',
            'linea_ramal': '45-2 RAMAL EJEMPLO',
            'indicador': 'IFO',
            'franja_horaria': 'Pico Tarde (16:00-18:59)',
            'umbral_requerido': '80%',
            'valor_observado': '72.8',
            'tipo_infraccion': 'Infracción Leve'
        }
    ]
    
    enviar_informe_incumplimientos(datos_ejemplo)