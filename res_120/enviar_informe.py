import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
import psycopg2
from typing import Optional, Dict, Any

def get_db_connection():
    """Establece conexión con la base de datos utilizando rutas absolutas para el .env"""
    import os
    from pathlib import Path
    
    # Ruta absoluta al .env del backend
    current_dir = Path(__file__).parent.absolute()
    backend_env = current_dir.parent / 'backend' / '.env'
    
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
    else:
        load_dotenv(override=True)
    
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
    except Exception as e:
        print(f"✗ Error crítico al conectar a la base de datos: {e}")
        # Mostrar variables detectadas (sin password) para diagnóstico
        print(f"  Config detectada: Host={DB_CONFIG['host']}, DB={DB_CONFIG['database']}, User={DB_CONFIG['user']}")
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
    """Obtiene los datos mensuales de IFO desde la API del backend."""
    # Obtener API_URL desde el entorno
    # API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:8000')
    API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:5001')
    API_URL = f"{API_BASE_URL}/api"
    
    try:
        payload = {
            "id_eot_vmt_hex": id_eot_vmt_hex,
            "fecha_referencia": fecha_referencia.strftime("%Y-%m-%d")
        }
        response = requests.post(f"{API_URL}/reports/res120/monthly-summary", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Convertir llaves de tipo_dia (vienen como strings desde JSON) y fechas
        resultado = {
            'tipos_dia': {},
            'ifo_mes': data['ifo_mes']
        }
        
        for tid_str, td_data in data['tipos_dia'].items():
            tid = int(tid_str)
            # Re-formatear fechas de d['dias'] a objetos date
            dias_dict = {}
            for fecha_str, dia_val in td_data['dias'].items():
                f_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                dias_dict[f_obj] = dia_val
                
            resultado['tipos_dia'][tid] = {
                'nombre': td_data['nombre'],
                'franjas': td_data['franjas'],
                'dias': dias_dict
            }
        
        print(f"  ✓ Datos mensuales obtenidos vía API para EOT {id_eot_vmt_hex}")
        return resultado
    except Exception as e:
        print(f"⚠ Error obteniendo datos mensuales vía API para EOT {id_eot_vmt_hex}: {e}")
        return None


def obtener_ifo_sistema_mes_anterior(fecha_referencia: date) -> float:
    """Obtiene el IFO del sistema del mes anterior desde la API."""
    # Obtener API_URL desde el entorno
    # API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:8000')
    API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:5001')
    API_URL = f"{API_BASE_URL}/api"
    
    try:
        fecha_str = fecha_referencia.strftime("%Y-%m-%d")
        response = requests.get(f"{API_URL}/reports/res120/system-ifo-baseline/{fecha_str}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get('ifo_sistema_mes_anterior', 0.0))
    except Exception as e:
        print(f"⚠ Error obteniendo IFO sistema vía API: {e}")
        return 0.0


def obtener_parametros_ifo_resumen(fecha_referencia: date) -> str:
    """Obtiene el resumen de parámetros de IFO desde la API."""
    # Obtener API_URL desde el entorno
    # API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:8000')
    API_BASE_URL = os.getenv('CBD_API_URL', 'http://localhost:5001')
    API_URL = f"{API_BASE_URL}/api"
    
    try:
        fecha_str = fecha_referencia.strftime("%Y-%m-%d")
        response = requests.get(f"{API_URL}/reports/res120/parameters-summary/{fecha_str}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('resumen', "Los incumplimientos para el IFO son sancionables según normativa vigente.")
    except Exception as e:
        print(f"⚠ Error obteniendo parámetros IFO vía API: {e}")
        return "Los incumplimientos para el IFO son sancionables según normativa vigente."

def obtener_clima(fecha: date) -> Optional[Dict[str, Any]]:
    """
    Obtiene la descripción e ícono de Open-Meteo, pero el valor de lluvia de la DB.
    """
    # 1. Obtener Descripción e Ícono de Open-Meteo
    latitud, longitud = -25.3, -57.6
    fecha_str = fecha.strftime("%Y-%m-%d")
    desc_final = "Despejado"
    icon_final = "☀️"
    viento_final = 0
    
    try:
        params = {
            'latitude': latitud, 'longitude': longitud,
            'start_date': fecha_str, 'end_date': fecha_str,
            'daily': ['weathercode', 'windspeed_10m_max'],
            'timezone': 'America/Asuncion'
        }
        res = requests.get('https://archive-api.open-meteo.com/v1/archive', params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if 'daily' in data and data['daily']['weathercode']:
                code = data['daily']['weathercode'][0]
                viento_final = data['daily']['windspeed_10m_max'][0]
                weather_codes = {
                    0: ('Despejado', '☀️'), 1: ('Mayormente despejado', '🌤️'), 
                    2: ('Parcialmente nublado', '⛅'), 3: ('Nublado', '☁️'),
                    45: ('Niebla', '🌫️'), 51: ('Llovizna', '🌦️'), 
                    61: ('Lluvia débil', '🌧️'), 63: ('Lluvia moderada', '🌧️'),
                    65: ('Lluvia fuerte', '🌧️💦'), 80: ('Chubascos', '🌧️'),
                    95: ('Tormenta', '⛈️'), 96: ('Tormenta con granizo', '⛈️🌨️')
                }
                desc_final, icon_final = weather_codes.get(code, ('Condición variable', '🌡️'))
    except Exception as e:
        print(f"⚠️ Error consultando Open-Meteo: {e}")

    # 2. Obtener Valor de Lluvia de la Base de Datos (Fuente de verdad para ajustes)
    mm_caidos = 0
    comprobado = False
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT mm_caidos, registro_comprobado
                FROM control_metricas.t_casuisticas_lluvia
                WHERE fecha_evento = %s
                ORDER BY mm_caidos DESC LIMIT 1
            """, (fecha,))
            row = cur.fetchone()
            if row:
                mm_caidos = float(row[0]) if row[0] is not None else 0.0
                comprobado = row[1]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error al obtener lluvia de la DB: {e}")
            if conn: conn.close()

    return {
        'fecha': fecha_str,
        'descripcion': desc_final,
        'icono': icon_final,
        'precipitacion': mm_caidos,
        'viento': viento_final,
        'comprobado': comprobado
    }

def analizar_infracciones_res_120(eot_nombre, datos_mensuales, fecha_referencia, umbral_obligatorio):
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

    # Agrupar datos por fecha (incluye todos los tipos de día)
    todas_fechas_dict = {}
    for td_id, td_data in datos_mensuales['tipos_dia'].items():
        franjas_metadata = td_data['franjas']
        for fecha, d_data in td_data['dias'].items():
            if fecha <= fecha_referencia:
                todas_fechas_dict[fecha] = {'data': d_data, 'metadata': franjas_metadata}
    
    fechas_ordenadas = sorted(todas_fechas_dict.keys())
    
    # Acumuladores y estado
    acum_b = {'PICO': 0, 'POS_PICO': 0}
    historial_faltas = [] # Lista de todas las sanciones detectadas

    # 0. Verificar Art 15.1 (IFO Mensual EOT < Umbral Obligatorio)
    # Se evalúa solo a fin de mes o diario según el acumulado actual
    ifo_mes_eot = datos_mensuales.get('ifo_mes', 0)
    if ifo_mes_eot < umbral_obligatorio:
        historial_faltas.append({
            'fecha': fecha_referencia, 
            'base': 'Art. 15.1', 
            'desc': f'IFO Mensual ({ifo_mes_eot:.2f}%) inferior al Umbral Obligatorio ({umbral_obligatorio:.2f}%)', 
            'jornales': 173
        })
    
    # Acumuladores y estado Art 15.2-15.6
    
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

def generar_html_informe(datos_incumplimientos, fecha_referencia, email_cc=None, incluir_resumen_infracciones=True):
    """
    Genera el contenido HTML del informe de incumplimientos.
    
    Args:
        datos_incumplimientos (list): Lista de diccionarios con los datos de incumplimientos
        fecha_referencia (date): Fecha de referencia para el informe (D-1)
        email_cc (str, optional): Lista de correos en CC para mostrar en el encabezado
    
    Returns:
        str: Contenido HTML del informe
    """
    fecha_formato = fecha_referencia.strftime("%Y-%m-%d")
    fecha_envio = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    # Calcular Umbral Obligatorio del IFO (Res. 120/2025)
    ifo_sistema_anterior = obtener_ifo_sistema_mes_anterior(fecha_referencia)
    if ifo_sistema_anterior > 95:
        umbral_obligatorio = 95.0
    elif ifo_sistema_anterior < 90:
        umbral_obligatorio = 90.0
    else:
        umbral_obligatorio = round(ifo_sistema_anterior, 2)
    
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
            inf_detectadas = analizar_infracciones_res_120(eot_nombre, datos_mensuales, fecha_referencia, umbral_obligatorio)
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
            <div style="margin-bottom: 15px;">
                <span style="background-color: #f0f7ff; padding: 5px 10px; border-radius: 4px; margin-right: 15px;">
                    <strong>IFO MES (Acumulado):</strong> {ifo_mes:.2f}%
                </span>
                <span style="background-color: #fff3cd; padding: 5px 10px; border-radius: 4px;">
                    <strong>Umbral Obligatorio:</strong> &ge; {umbral_obligatorio:.2f}%
                </span>
            </div>
        """
        
        # Generar tabla para cada tipo de día (5=Laboral, 6=Sábado, 7=Domingo/Feriado)
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
                hora_inicio = franja_info['hora_inicio'] if franja_info['hora_inicio'] else ''
                hora_fin = franja_info['hora_fin'] if franja_info['hora_fin'] else ''
                # Si vienen con segundos (HH:MM:SS), recortar a HH:MM
                if len(hora_inicio) > 5: hora_inicio = hora_inicio[:5]
                if len(hora_fin) > 5: hora_fin = hora_fin[:5]
                cbd_min = franja_info.get('cbd_minimo', '')
                encabezado_franjas += f"""
                    <th style="border: 1px solid #ccc; padding: 8px; text-align: center; vertical-align: top;">
                        <div style="font-weight: bold;">{nombre}</div>
                        <div style="font-size: 10px; color: #666;">{hora_inicio} - {hora_fin}</div>
                        <div style="font-size: 10px; color: #cc0000; cursor: help;" title="Cantidad Mínima de Buses Diferentes exigida para esta franja">CBD Mín: {cbd_min if cbd_min else '-'}</div>
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
                            
                        fila_ifo += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center; background-color: {bg_color}; color: {color_text};\">{ifo_val:.2f}%</td>"
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
                        
                    fila_ifo += f"<td style=\"border: 1px solid #ccc; padding: 8px; text-align: center; background-color: {bg_color_d}; color: {color_text_d};\"><strong>{ifo_diario:.2f}%</strong></td>"
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
                            <th rowspan="2" style="border: 1px solid #ccc; padding: 8px; text-align: center;">IFO Promedio Diario (%)</th>
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
                text-align: center;
                margin-bottom: 20px;
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
                <img src="cid:vmt_logo" alt="Logo MOPC VMT" style="width: 100%; max-width: 800px; height: auto; display: block; margin: 0 auto;">
            </div>

            <p style="text-align: left; font-size: 12px;"><strong>ASUNTO:</strong> Reporte Oficial de Desempeño Operativo – Etapa 1 (Adaptación)</p>
            <p style="font-size: 12px;"><strong>FECHA DE OPERACIÓN:</strong> {fecha_formato}</p>
            <p style="font-size: 12px;"><strong>FECHA DE EMISIÓN:</strong> {fecha_envio}</p>

            <hr style="border-top: 1px solid #004a99;">

            <div class="cuerpo-texto">
                <p>Estimados Permisionarios del Servicio de Transporte Público Metropolitano:</p>
                
                <p>La <strong>Dirección Metropolitana de Transporte (DMT),</strong> en cumplimiento de lo establecido en el <strong>Artículo 14 de la Resolución GVMT N° 120/2025</strong>, remite el presente reporte de desempeño acumulado del mes, hasta la operativa del día <strong>{fecha_formato}</strong>.</p>
                
                <p>Se deja constancia de que, con fecha <strong>1 de febrero de 2026</strong>, se ha dado inicio oficial a la <strong>Etapa 1: Adaptación Operativa</strong>, la cual tendrá una duración de dos meses. Esta fase es fundamental para la consolidación del Sistema Integral de Control y Monitoreo basado en los datos de GPS y Billetaje Electrónico.</p>

                <div style="background-color: #f0f7ff; border-left: 5px solid #004a99; padding: 15px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #004a99;">Pautas de la Etapa Actual (Febrero - Marzo 2026):</h4>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>Sin Sanciones Pecuniarias:</strong> Durante estos dos meses, de acuerdo con el <strong>Artículo 21.1</strong>, los eventuales incumplimientos de los indicadores de desempeño (IFO y CBDmin) serán reportados a las empresas con fines informativos, pero <strong>no se aplicarán las sanciones pecuniarias</strong> previstas en el catálogo de infracciones.</li>
                        <li><strong>Propósito de Adaptación:</strong> Esta comunicación tiene como objetivo principal que cada empresa pueda:
                            <ol>
                                <li>Ajustar su operación a los nuevos niveles de servicio (Niveles A, B y C) y parámetros de buses mínimos (CBDmin).</li>
                                <li>Verificar la precisión de la transmisión de sus datos operativos (GPS) y validaciones de billetaje.</li>
                                <li>Realizar correcciones técnicas antes del inicio de la Etapa 2 (Parcial), donde comenzarán a regir las multas en franjas pico y pospico.</li>
                            </ol>
                        </li>
                        <li><strong>Tratamiento de Datos:</strong> El cálculo del Índice de Flota Operativa (IFO) y de Cantidad Mínima de Buses Diferentes (CBDmin) aplica factores de ajustes correspondientes a días atípicos, cuyos cálculos podría arrojar valores superlativos, los cuales serán analizados durante esta Etapa 1 (Adaptación).</li>
                    </ul>
                </div>

                <p>Este reporte diario constituye el canal oficial de comunicación para garantizar la transparencia y la robustez técnica del sistema antes de la plena vigencia del régimen sancionatorio.</p>

                {seccion_clima}

                {seccion_ajuste}

                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 20px 0; font-size: 12px;">
                    <h4 style="margin-top: 0; color: #1e40af; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">Glosario y Referencia de Colores</h4>
                    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <strong style="color: #1e40af;">Definiciones:</strong>
                            <ul style="margin: 5px 0; padding-left: 15px; list-style-type: none;">
                                <li><strong>• CBD:</strong> Cantidad de Buses Diferentes (unidades físicas observadas).</li>
                                <li><strong>• ICCBDM:</strong> Índice de Cumplimiento de Cantidad de Buses Diferentes Mínimos.</li>
                                <li><strong>• IFO:</strong> Índice de Flota Operativa (Regularidad de la oferta).</li>
                                <li><strong>• Umbral Obligatorio:</strong> Mínimo exigible según el IFO Sistema del mes anterior:
                                    <ul style="margin: 2px 0 2px 10px; font-size: 11px; color: #475569; list-style-type: none;">
                                        <li>- Si Sistema &gt; 95% &rarr; Umbral = 95%</li>
                                        <li>- Si Sistema &lt; 90% &rarr; Umbral = 90%</li>
                                        <li>- Si 90% &le; Sistema &le; 95% &rarr; Umbral = IFO Sistema</li>
                                    </ul>
                                </li>
                            </ul>
                        </div>
                        <div style="flex: 1; min-width: 250px;">
                            <strong style="color: #1e40af;">Referencia por Colores:</strong>
                            <div style="margin-top: 5px;">
                                <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                                    <span style="background-color: #e6ffe6; border: 1px solid #b7eb8f; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Verde</span>
                                    <span>Cumplimiento Óptimo (IFO &ge; 90%(Nivel A) | ICCBDM &ge; 100% | Mensual &ge; Umbral)</span>
                                </div>
                                <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                                    <span style="background-color: #ffffe6; border: 1px solid #ffe58f; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Amarillo</span>
                                    <span>Cumplimiento Regular (IFO 80% - 89%) - (Nivel B)</span>
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <span style="background-color: #ffe6e6; border: 1px solid #ffa39e; padding: 2px 8px; border-radius: 3px; font-size: 10px;">Rojo</span>
                                    <span>Cumplimiento Crítico / Insuficiente (IFO < 80%(Nivel C) | ICCBDM < 100%)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <h3 class="section-title">CONSOLIDADO DE MONITOREOS DIARIOS</h3>

                {secciones_eot_html}


                <h3 class="section-title">PROCEDIMIENTO Y BASE LEGAL</h3>
                <ul>
                    <li><strong>Alerta Automática:</strong> El sistema genera este informe de manera automatizada.</li>
                    <li><strong>Vigencia Gradual:</strong> Conforme al Artículo 21, durante la Etapa 1 (febrero y marzo de 2026), los incumplimientos se reportarán únicamente a efectos informativos, sin aplicación de multas. Las sanciones efectivas iniciarán en la Etapa 2 (abril de 2026) solo para picos y pos picos de lunes a sábado.</li>
                    <li><strong>Marco Regulatorio:</strong> Todo el proceso se rige por el Capítulo IV de la Resolución GVMT N° 120/2025.</li>
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
                ''' if resumen_infracciones_lista and incluir_resumen_infracciones else ''}
            </div>

            <div class="signature">
                <p>Para consultas técnicas sobre los valores obtenidos en este informe, pueden dirigirse a la Coordinación de Innovación y Desarrollo (CID) a través del correo oficial: <strong>billetajevmt@gmail.com</strong>.</p>
                <br>
                <p>Atentamente,</p>
                <p><strong>Ing. ROLANDO GONZÁLEZ</strong><br>Director – Dirección Metropolitana de Transporte (DMT)<br>Viceministerio de Transporte (GVMT)</p>
                <p style="color: #888; margin-top: 10px; font-size: 10px;">*Este es un mensaje generado automáticamente por el Sistema Integral de Control y Monitoreo (CID/DMT)*</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def registrar_alerta(descripcion: str, id_tipo_alerta: int = 5):
    """
    Registra una alerta en la tabla alertas.control_alertas cuando ocurre un error de envío de correo.
    """
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
        """, ('enviar_informe.py', id_tipo_alerta, descripcion))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"  ℹ Alerta registrada en control_alertas (Tipo {id_tipo_alerta})")
        return True
    except Exception as e:
        print(f"  ⚠ Error al registrar alerta en BD: {e}")
        return False

def enviar_informe_incumplimientos(datos_incumplimientos, fecha_referencia=None, email_destino=None, incluir_resumen_infracciones=True, enviar_cc=False):
    """
    Envía por correo electrónico el informe de incumplimientos.
    
    Args:
        datos_incumplimientos (list): Lista de diccionarios con los datos de incumplimientos
        fecha_referencia (date, optional): Fecha de referencia para el informe. Si es None, usa el día anterior.
        email_destino (str, optional): Dirección de correo de destino. Si se omite, usa EMAIL_TO del .env
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
    
    # Cargar variables de entorno (forzar actualización)
    from pathlib import Path
    current_dir = Path(__file__).parent.absolute()
    backend_env = current_dir.parent / 'backend' / '.env'
    
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
    else:
        load_dotenv(override=True)
    
    # Configuración del correo (mismo .env que backend: backend/.env)
    SMTP_SERVER = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('EMAIL_PORT', 587))
    SMTP_USER = os.getenv('EMAIL_USERNAME', '')
    SMTP_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', '')

    # Determinar destinatario
    if email_destino:
        EMAIL_TO = email_destino
    else:
        EMAIL_TO = os.getenv('EMAIL_TO', '')

    # Tomamos el CC del .env si enviar_cc es True
    EMAIL_CC = os.getenv('EMAIL_CC') if enviar_cc else None
    
    USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    
    # Debug para el usuario
    print(f"  ℹ Configuración de correos detectada:")
    print(f"    - PARA: {EMAIL_TO}")
    print(f"    - CC: {EMAIL_CC if EMAIL_CC else '(No configurado o deshabilitado por override)'}")

    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        msg = "Faltan configuraciones de correo electrónico críticas (.env)"
        print(f"✗ Error: {msg}")
        registrar_alerta(msg)
        print(f"  ⚠ Alerta generada: {msg}")
        return False
    
    # Establecer fecha de referencia (por defecto, el día anterior)
    if fecha_referencia is None:
        fecha_referencia = datetime.now().date() - timedelta(days=1)
    
    # Configurar destinatarios (Soporta listas separadas por comas)
    destinatarios_to = [e.strip() for e in EMAIL_TO.split(',') if e.strip()]
    destinatarios_cc = [e.strip() for e in EMAIL_CC.split(',') if e.strip()] if EMAIL_CC else []
    
    all_recipients = destinatarios_to + destinatarios_cc

    try:
        # Crear el mensaje (related = permite cid: para imágenes inline)
        msg = MIMEMultipart('related')
        msg['From'] = EMAIL_FROM
        msg['To'] = ", ".join(destinatarios_to)
        if destinatarios_cc:
            msg['Cc'] = ", ".join(destinatarios_cc)
        
        # Ajustar asunto según si es simulación o informe oficial
        #prefix = "[SIMULACIÓN EMPRESA]" if email_destino else "[DMT] OFICIAL" 
        #msg['Subject'] = f'{prefix} Reporte Diario - Métricas IFO/ICCBDM - {fecha_referencia.strftime("%Y-%m-%d")}'
        
        # Nuevo Asunto Oficial Etapa 1
        msg['Subject'] = f'Reporte Oficial de Desempeño Operativo – Etapa 1 (Adaptación) - Res. GVMT N° 120/2025 - {fecha_referencia.strftime("%Y-%m-%d")}'
        
        # Generar el contenido HTML del informe (incluyendo visualización de CC)
        html_content = generar_html_informe(datos_incumplimientos, fecha_referencia, EMAIL_CC, incluir_resumen_infracciones=incluir_resumen_infracciones)
        msg.attach(MIMEText(html_content, 'html'))

        # Adjuntar LOGO MOPC VMT (Si existe). Varias rutas por si se ejecuta desde servidor/Prefect.
        try:
            from pathlib import Path
            current_dir = Path(__file__).resolve().parent
            logo_name = 'Logo MOPC VMT.png'
            candidatos = [
                current_dir.parent / 'frontend' / 'public' / 'imagenes' / logo_name,
                current_dir / 'imagenes' / logo_name,
                current_dir / logo_name,
            ]
            logo_path = None
            for p in candidatos:
                if p.exists():
                    logo_path = p
                    break
            if logo_path:
                with open(logo_path, 'rb') as f:
                    logo_img = MIMEImage(f.read(), _subtype='png')
                    logo_img.add_header('Content-ID', '<vmt_logo>')
                    logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
                    msg.attach(logo_img)
            else:
                print(f"⚠ Logo no encontrado. Buscado en: {candidatos}")
        except Exception as e:
            print(f"⚠ Error adjuntando logo: {e}")
        
        # Configurar conexión SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60)
        
        # Iniciar conexión segura si es necesario
        if USE_TLS:
            server.starttls()
        
        # Iniciar sesión
        server.login(SMTP_USER, SMTP_PASSWORD.strip())
        
        # Enviar correo a todos los destinatarios (To + Cc)
        server.send_message(msg, to_addrs=all_recipients)
        server.quit()
        
        print(f"✓ Correo enviado a: {msg['To']}")
        if destinatarios_cc:
            print(f"✓ CC enviado a: {msg['Cc']}")
        return True
    
    except Exception as e:
        msg = f"Error al enviar el correo a {EMAIL_TO}: {str(e)}"
        print(f"✗ {msg}")
        import traceback
        traceback.print_exc()
        registrar_alerta(msg)
        print(f"  ⚠ Alerta generada: {msg}")
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