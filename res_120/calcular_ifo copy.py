import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from datetime import datetime, timedelta, date, time
import os
from dotenv import load_dotenv
import sys
import traceback
import math
import calendar

try:
    from enviar_informe import enviar_informe_incumplimientos
except ImportError:
    def enviar_informe_incumplimientos(datos, fecha):
        print("⚠ Módulo enviar_informe no encontrado. No se enviará correo.")
        return False

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# --- CONSTANTES BASE ---
# IDs de tipo de día según tabla control_metricas.franjas_operativas
TIPO_DIA_ID_LV = 5      # Laboral
TIPO_DIA_ID_SAB = 6     # Sábado
TIPO_DIA_ID_DOM = 7     # Domingo/Feriado

MESES_TIPICOS = {2, 4, 5, 6, 7, 8, 9, 10, 11}
MESES_ATIPICOS = {1, 3, 12}

datos_incumplimientos = []

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"✗ Error conexión DB: {e}")
        sys.exit(1)

def identificar_tipo_dia(fecha, conn):
    """
    Determina el ID de tipo de día (5, 6, 7) consultando feriados.
    """
    es_feriado = False
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT descripcion FROM feriados WHERE fecha = %s", (fecha,))
            res = cur.fetchone()
            if res:
                es_feriado = True
        except psycopg2.Error:
            pass 
    
    weekday = fecha.weekday() # 0=Mon, 6=Sun
    
    if es_feriado or weekday == 6:
        return TIPO_DIA_ID_DOM, es_feriado, "Domingo o Feriado"
    elif weekday == 5:
        return TIPO_DIA_ID_SAB, False, "Sábado"
    else:
        return TIPO_DIA_ID_LV, False, "Lunes a Viernes"

def check_eventos_atipicos(fecha, conn):
    """
    Verifica eventos atípicos en la base de datos (Lluvia, etc).
    Retorna un diccionario con flags y datos relevantes.
    
    Para lluvia: Suma los mm del día (mm_caidos). Si >= 5mm, se considera día de lluvia.
    """
    eventos = {
        'es_dia_lluvia': False,
        'mm_acumulados': 0.0,
        'disruptivo': False,
        'pre_pos_feriado': False
    }

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(mm_caidos), 0) as mm_total
                FROM control_metricas.t_casuisticas_lluvia
                WHERE fecha_evento = %s
            """, (fecha,))
            
            resultado = cur.fetchone()
            if resultado:
                mm_total = float(resultado[0])
                eventos['mm_acumulados'] = mm_total
                
                if mm_total >= 5.0:
                    eventos['es_dia_lluvia'] = True

    except Exception as e:
        print(f"⚠ Error consultando eventos atípicos: {e}")
        
    return eventos

def get_configuracion_operativa(conn, fecha, id_tipo_dia):
    """
    Obtiene las franjas operativas y sus parámetros (CBD min, IFO min)
    desde la base de datos para la fecha y tipo de día especificados.
    """
    config = []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Obtener Franjas Operativas Vigentes y Activas
        query_franjas = """
            SELECT id_franja, denominacion, hora_inicio, hora_fin
            FROM control_metricas.franjas_operativas
            WHERE id_tipo_dia = %s
              AND activo = TRUE
              AND inicio_vigencia <= %s
              AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
            ORDER BY hora_inicio ASC
        """
        cur.execute(query_franjas, (id_tipo_dia, fecha, fecha))
        franjas = cur.fetchall()
        
        for f in franjas:
            f_id = f['id_franja']
            
            # 2. Obtener CBD Mínimos
            query_cbd = """
                SELECT cbd_minimo_hora, cbd_minimo_franja
                FROM control_metricas.cbd_parametros_minimos
                WHERE id_franja = %s
                  AND vigencia_desde <= %s
                  AND (vigencia_hasta IS NULL OR vigencia_hasta >= %s)
                ORDER BY vigencia_desde DESC LIMIT 1
            """
            cur.execute(query_cbd, (f_id, fecha, fecha))
            cbd_res = cur.fetchone()
            
            # Valores por defecto si no se configura
            cbd_h = cbd_res['cbd_minimo_hora'] if cbd_res else 0
            cbd_f = cbd_res['cbd_minimo_franja'] if cbd_res else 0
            
            # 3. Obtener Parámetros IFO (Umbral Cumplimiento)
            query_ifo = """
                SELECT porc_cumplimiento_minimo, id_infraccion
                FROM control_metricas.parametros_ifo
                WHERE id_franja_operativa = %s
                  AND inicio_vigencia <= %s
                  AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
                ORDER BY inicio_vigencia DESC LIMIT 1
            """
            cur.execute(query_ifo, (f_id, fecha, fecha))
            ifo_res = cur.fetchone()
            
            ifo_min_pct = ifo_res['porc_cumplimiento_minimo'] if ifo_res else 80.00
            
            # Convertir horas time a int (0-23) para el bucle
            # Asumimos horas enteras en punto según lógica anterior, o truncamos.
            h_start = f['hora_inicio'].hour
            h_end = f['hora_fin'].hour
            
            config.append({
                'id': f_id,
                'nombre': f['denominacion'],
                'start': h_start,
                'end': h_end,
                'cbd_min_h': cbd_h,
                'cbd_min_f': cbd_f,
                'ifo_min_pct': ifo_min_pct
            })
            
    return config

def get_b_obs_por_hora(conn, id_eot_catalogo, id_eot_hex, fecha, hora_inicio, hora_fin):
    """
    Calcula b_obs (Buses observados) para un rango horario.
    Max(Validaciones, GPS).
    """
    # 1. Validaciones
    b_obs_val = 0
    try:
        with conn.cursor() as cur:
            query_val = """
                SELECT COUNT(DISTINCT idsam) 
                FROM public.servicios_diarios 
                WHERE id_eot_catalogo = %s AND fecha = %s AND hora >= %s AND hora <= %s
            """
            cur.execute(query_val, (id_eot_catalogo, fecha, hora_inicio, hora_fin))
            res = cur.fetchone()
            if res: b_obs_val = res[0]
    except Exception: pass

    # 2. GPS
    b_obs_gps = 0
    try:
        with conn.cursor() as cur:
            query_gps = """
                SELECT COUNT(DISTINCT mean_id)
                FROM control_metricas.cbd_detalle_buses
                WHERE id_eot_vmt_hex = %s AND fecha = %s AND hora >= %s AND hora <= %s
            """
            cur.execute(query_gps, (id_eot_hex, fecha, hora_inicio, hora_fin))
            res = cur.fetchone()
            if res: b_obs_gps = res[0]
    except Exception: pass

    return max(b_obs_val, b_obs_gps), "VALIDACIONES" if b_obs_val >= b_obs_gps else "GPS"

def get_fechas_referencia(fecha_analisis, id_tipo_dia, conn):
    """
    Devuelve lista de fechas históricas (4 equivalentes válidos).
    """
    mes = fecha_analisis.month
    year = fecha_analisis.year
    fechas_ref = []
    
    if mes in MESES_TIPICOS:
        # Últimas 4 semanas
        for i in range(1, 6):
            cand = fecha_analisis - timedelta(weeks=i)
            tid, es_fer, _ = identificar_tipo_dia(cand, conn)
            # Solo comparar con mismo tipo de día lógico (Laboral con Laboral, etc.)
            # Nota: id_tipo_dia ya distingue feriados (7) de laborales (5)
            if tid == id_tipo_dia:
                fechas_ref.append(cand)
            if len(fechas_ref) == 4: break
        factor_mes = 1.0
    else:
        # Meses Atípicos (Ene, Mar, Dic)
        if mes == 1: # Enero -> Nov anterior * 0.80
            target_year, target_month, factor_mes = year - 1, 11, 0.80
        elif mes == 3: # Marzo -> Nov anterior * 1.00
            target_year, target_month, factor_mes = year - 1, 11, 1.00
        elif mes == 12: # Diciembre -> Nov mismo año * 0.80
            target_year, target_month, factor_mes = year, 11, 0.80
        else:
            factor_mes = 1.0

        c = calendar.Calendar()
        month_days = c.itermonthdates(target_year, target_month)
        # Mapear el tipo de día weekday de hoy
        weekday_target = fecha_analisis.weekday()
        
        # OJO: Si hoy es 'Laboral', buscamos Laborales en Noviembre.
        # Si hoy es 'Domingo', buscamos domingos.
        # La función identificar_tipo_dia devuelve ID.
        
        for d in month_days:
            if d.month == target_month and d.weekday() == weekday_target:
                tid, _, _ = identificar_tipo_dia(d, conn)
                if tid == id_tipo_dia: # Coincide tipo (ej. ambos laborales)
                    fechas_ref.append(d)

    return fechas_ref, factor_mes

def calcular_b_dist_hora(conn, id_eot_catalogo, id_eot_hex, fechas_ref, hora, factor_mes, ajustes_atipicos):
    if not fechas_ref: return 0
    
    sum_b = 0
    count = 0
    for fh in fechas_ref:
        val, _ = get_b_obs_por_hora(conn, id_eot_catalogo, id_eot_hex, fh, hora, hora)
        sum_b += val
        count += 1
    
    if count == 0: return 0
    base_avg = sum_b / count
    ref_final = base_avg * factor_mes
    
    # Ajustes por día atípico
    factor_final = 1.0
    
    if ajustes_atipicos.get('pre_pos_feriado'):
        factor_final = 0.70
        
    if ajustes_atipicos.get('es_dia_lluvia'):
        factor_final = min(factor_final, 0.50)
            
    # Chequear tipo de día para ajustes pre-definidos de feriados
    # (Ya vienen implícitos si la fecha analizada cayó en feriado, pero aplicamos por seguridad)
    if ajustes_atipicos.get('es_feriado_sab'): 
        factor_final = min(factor_final, 0.50)
    elif ajustes_atipicos.get('es_feriado_lv'): 
        factor_final = min(factor_final, 0.30)

    return ref_final * factor_final

def get_nivel_ifo(ifo_val, umbral_minimo_pct):
    pct = ifo_val * 100
    if pct >= 90: return 'A'
    if pct >= umbral_minimo_pct: return 'B' # Cumple (entre 80 y 90, o lo que defina DB)
    return 'C' # No cumple

def procesar_eot_dia(conn, eot, fecha):
    id_eot_hex = eot['id_eot_vmt_hex']
    cod_catalogo = eot['cod_catalogo']
    nombre_eot = eot['eot_nombre']
    
    # 1. Identificar Tipo de Día y Flags
    id_tipo_dia, es_feriado, desc_dia = identificar_tipo_dia(fecha, conn)
    flags_evento = check_eventos_atipicos(fecha, conn)
    
    ajustes = {}
    if es_feriado and id_tipo_dia == TIPO_DIA_ID_LV: # Feriado que cayó L-V (se vuelve ID_DOM, pero origen L-V)
        # OJO: La función devuelve ID_DOM si es feriado.
        # Si es feriado, la lógica de referencia buscará otros ID_DOM (domingos/feriados).
        # La norma dice "si el día analizado es atípico... Feriado día laborable: b_dist = 30%".
        # Esto implica comparar contra un día normal equivalente?
        # La norma: "Referencia: media... en 4 días equivalentes".
        # Si hoy es feriado (atípico), comparo con feriados o con días normales ajustados?
        # "Feriado día laborable: b_dist = 30% de la flota habitual... en un día equivalente".
        # Día equivalente de un "Lunes Feriado" es "Lunes Normal".
        # POR TANTO: Si hoy es feriado, debo forzar la búsqueda de referencias como si fuera un día NORMAL
        # y aplicar el factor 0.30.
        pass

    # REVISIÓN LOGICA FERIADOS:
    # Si la fecha es feriado, identificar_tipo_dia retorna TIPO_DIA_ID_DOM (7).
    # Pero para hallar las referencias (días equivalentes), queremos días "normales" de ese día de semana (ej. Lunes).
    weekday = fecha.weekday()
    tipo_dia_referencia = TIPO_DIA_ID_LV if weekday < 5 else (TIPO_DIA_ID_SAB if weekday==5 else TIPO_DIA_ID_DOM)
    
    # Ajustes flags
    if es_feriado:
        if weekday < 5: ajustes['es_feriado_lv'] = True
        elif weekday == 5: ajustes['es_feriado_sab'] = True
    
    if flags_evento['pre_pos_feriado']: ajustes['pre_pos_feriado'] = True
    if flags_evento['es_dia_lluvia']: ajustes['es_dia_lluvia'] = True
    
    # 2. Obtener fechas ref (usando el tipo de día "natural" del weekday para buscar históricos normales)
    fechas_ref, factor_mes = get_fechas_referencia(fecha, tipo_dia_referencia, conn)
    
    # 3. Obtener Configuración Dinámica (Franjas y Parámetros)
    # Aquí usamos el id_tipo_dia real de hoy. Si es feriado, traemos franjas de tipo 7 (Dom/Fer).
    franjas_config = get_configuracion_operativa(conn, fecha, id_tipo_dia)
    
    if not franjas_config:
        return

    resultados_franja = []

    for f_conf in franjas_config:
        f_id = f_conf['id']
        f_nombre = f_conf['nombre']
        h_start = f_conf['start']
        h_end = f_conf['end']
        cbd_min_h = f_conf['cbd_min_h']
        cbd_min_f = f_conf['cbd_min_f']
        ifo_min_pct = f_conf['ifo_min_pct'] # Ej: 80.0
        
        obs_horas = []
        cbd_min_horas = []
        ifo_horas = []
        
        horas_range = range(h_start, h_end + 1)
        
        for h in horas_range:
            b_obs, _ = get_b_obs_por_hora(conn, cod_catalogo, id_eot_hex, fecha, h, h)
            b_dist = calcular_b_dist_hora(conn, cod_catalogo, id_eot_hex, fechas_ref, h, factor_mes, ajustes)
            
            ifo_h = (b_obs / b_dist) if b_dist > 0 else (1.0 if b_obs > 0 else 0.0)
            
            obs_horas.append(b_obs)
            ifo_horas.append(ifo_h)
            cbd_min_horas.append(cbd_min_h)
            
        # Métricas Franja
        ifo_franja = sum(ifo_horas) / len(ifo_horas) if ifo_horas else 0
        b_obs_franja_total, _ = get_b_obs_por_hora(conn, cod_catalogo, id_eot_hex, fecha, h_start, h_end)
        
        # ICCBDM
        ratios_h = [min(obs/req, 1.0) if req > 0 else 1.0 for obs, req in zip(obs_horas, cbd_min_horas)]
        i_h = sum(ratios_h)/len(ratios_h) if ratios_h else 0
        i_f = min(b_obs_franja_total / cbd_min_f, 1.0) if cbd_min_f > 0 else 1.0
        iccbdm_franja = (0.7 * i_h) + (0.3 * i_f)
        
        nivel = get_nivel_ifo(ifo_franja, ifo_min_pct)
        cumple_cbd = b_obs_franja_total >= cbd_min_f
        
        # Reportar Incumplimientos
        if nivel == 'C':
            datos_incumplimientos.append({
                'eot_nombre': nombre_eot,
                'linea_ramal': f"Cat: {cod_catalogo}",
                'indicador': 'IFO Franja',
                'franja_horaria': f"{f_nombre} ({h_start}-{h_end})",
                'umbral_requerido': f"{ifo_min_pct:.0f}%",
                'valor_observado': f"{ifo_franja*100:.1f}%",
                'tipo_infraccion': 'IFO Insuficiente (Nivel C)',
                'normativa': 'Res. 120/2025'
            })
            
        if not cumple_cbd:
            datos_incumplimientos.append({
                'eot_nombre': nombre_eot,
                'linea_ramal': f"Cat: {cod_catalogo}",
                'indicador': 'CBD Min Franja',
                'franja_horaria': f"{f_nombre}",
                'umbral_requerido': str(cbd_min_f),
                'valor_observado': str(b_obs_franja_total),
                'tipo_infraccion': 'CBD Insuficiente',
                'normativa': 'Res. 120/2025'
            })

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Cálculo IFO/CBD Res 120/2025')
    parser.add_argument('--fecha', type=str, help='YYYY-MM-DD')
    parser.add_argument('--desde', type=str, help='YYYY-MM-DD')
    parser.add_argument('--hasta', type=str, help='YYYY-MM-DD')
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    if args.fecha:
        start = end = datetime.strptime(args.fecha, '%Y-%m-%d').date()
    elif args.desde and args.hasta:
        start = datetime.strptime(args.desde, '%Y-%m-%d').date()
        end = datetime.strptime(args.hasta, '%Y-%m-%d').date()
    else:
        start = end = date.today() - timedelta(days=1)
        
    print(f"=== Iniciando Cálculo Res 120/2025: {start} a {end} ===")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id_eot_vmt_hex, cod_catalogo, eot_nombre FROM eots WHERE permisionario = TRUE")
        eots = cur.fetchall()
        
    delta = end - start
    for i in range(delta.days + 1):
        dia = start + timedelta(days=i)
        print(f"\nProcesando fecha: {dia}")
        for eot in eots:
            procesar_eot_dia(conn, eot, dia)
            
    if datos_incumplimientos:
        print(f"\n⚠ {len(datos_incumplimientos)} incumplimientos detectados.")
        try:
            enviar_informe_incumplimientos(datos_incumplimientos, end)
        except Exception as e:
            print(f"Error informe: {e}")
            for inc in datos_incumplimientos: print(inc)
    else:
        print("\n✓ Sin incumplimientos.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt: pass
    except Exception as e: traceback.print_exc()