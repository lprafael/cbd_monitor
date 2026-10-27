"""
USO:
1. Con fecha específica (formato YYYY-MM-DD):
   python servicios_diariosv3.py 2025-12-01

2. Rango de fechas (desde-hasta inclusive):
   python servicios_diariosv3.py 2025-11-01 2025-11-30

3. Sin parámetros (usa la fecha de ayer):
   python servicios_diariosv3.py

Ejemplos:
   python servicios_diariosv3.py 2025-11-30
   python servicios_diariosv3.py 2025-11-01 2025-11-30
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
from typing import Optional

# Configurar codificación UTF-8 para consola en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

# Cargar .env: busca primero en el directorio local del script (res_120/.env)
# y luego en directorios padres si faltan variables clave
SCRIPT_DIR = Path(__file__).resolve().parent
env_candidates = [
    SCRIPT_DIR / ".env",
    SCRIPT_DIR.parent / ".env",
    SCRIPT_DIR.parent / "backend" / ".env",
    SCRIPT_DIR.parents[2] / ".env",
]
for env_path in env_candidates:
    if env_path.exists():
        load_dotenv(env_path)

# Importar Prefect si está disponible, o definir decoradores vacíos si se ejecuta standalone
try:
    from prefect import flow, task
except ImportError:
    def flow(*dargs, **dkwargs):
        def decorator(func):
            return func
        if dargs and callable(dargs[0]):
            return dargs[0]
        return decorator

    def task(*dargs, **dkwargs):
        def decorator(func):
            return func
        if dargs and callable(dargs[0]):
            return dargs[0]
        return decorator

import psycopg2

def get_db_connection():
    """
    Establece conexión con la base de datos usando variables de entorno.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except Exception as e:
        print(f"  ⚠ Error al conectar con la base de datos: {e}")
        return None

def registrar_ejecucion_correcta(id_script: int = 2):
    """
    Registra una ejecución correcta en la tabla alertas.registro_ejecuciones.
    Usa la misma estructura que script_lluvia (fecha_proceso, fecha_ejecucion).
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("  ⚠ No se pudo conectar a BD para registrar_ejecucion_correcta (revisar .env/conexión).")
            return

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alertas.registro_ejecuciones 
            (id_script, fecha_proceso, fecha_ejecucion, estado, detalles)
            VALUES (%s, CURRENT_DATE, NOW(), %s, %s)
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
    try:
        conn = get_db_connection()
        if not conn:
            print(f"  ⚠ No se pudo conectar a BD para registrar alerta: {descripcion[:50]}...")
            return False
        
        cursor = conn.cursor()
        script_name = os.path.basename(__file__)
        cursor.execute("""
            INSERT INTO alertas.control_alertas 
            (fuente, fechahora_alerta, id_tipo_alerta, verificado, corregido, descripcion_incidente)
            VALUES (%s, NOW(), %s, false, false, %s)
        """, (script_name, id_tipo_alerta, descripcion))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"  ℹ Alerta registrada en control_alertas")
        return True
    except Exception as e:
        print(f"  ⚠ Error al registrar alerta en BD: {e}")
        return False

def verificar_existencia_alertas(minutes_lookback=60):
    """
    Verifica si existen alertas recientes para este script en la BD.
    """
    try:
        conn = get_db_connection()
        if not conn:
            return True # Asumir riesgo si no hay conexión
        
        cursor = conn.cursor()
        script_name = os.path.basename(__file__)
        
        # Consultar alertas registradas recientemente por este script
        cursor.execute("""
            SELECT COUNT(*) 
            FROM alertas.control_alertas 
            WHERE fuente = %s 
            AND fechahora_alerta >= NOW() - (interval '1 minute' * %s)
        """, (script_name, minutes_lookback))
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if count > 0:
            print(f"  ⚠ Se detectaron {count} alertas recientes. No se registrará ejecución correcta.")
            return True
        return False
        
    except Exception as e:
        print(f"  ⚠ Error al verificar alertas: {e}")
        return True # Por seguridad, asumir que hay alertas


@task(name="Consultar Datos Azure")
def get_azure_data(fecha_inicio, fecha_fin):
    host = os.getenv('VMT_DB_HOST')
    port = os.getenv('VMT_DB_PORT')
    db_name = os.getenv('VMT_DB_NAME')
    user = os.getenv('VMT_DB_USER')
    password = os.getenv('VMT_DB_PASSWORD')

    azure_engine = create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{db_name}",
        connect_args={"connect_timeout": 10}
    )
    
    query_principal = """
        SELECT 
            idsam, 
            idrutaestacion, 
            fechahoraevento::date AS fecha, 
            EXTRACT(hour FROM fechahoraevento) AS hora,
            COUNT(DISTINCT idsam || '' || COALESCE(serialmediopago::text, '') || '' || COALESCE(consecutivoevento::text, '')) AS validaciones
        FROM public.c_transacciones
        WHERE fechahoraevento >= :fecha_inicio 
        AND fechahoraevento < :fecha_fin
        AND tipoevento IN (4, 8)
        AND idproducto IN ('4d4f', '4553')
        GROUP BY idsam, idrutaestacion, fecha, hora
        ORDER BY fecha, hora, idsam, idrutaestacion
    """
    
    try:
        with azure_engine.connect() as conn:
            df = pd.read_sql(
                text(query_principal), 
                conn, 
                params={
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin
                }
            )
        return df
    except UnicodeDecodeError as e:
        raise RuntimeError(
            f"Error de conexión a la BD VMT ({host}:{port}/{db_name}): "
            "Falló la autenticación o la conexión en el servicio local/remoto. "
            "Asegúrese de tener activa la VPN (IP 192.168.174.21) o el túnel SSH hacia la base de datos VMT."
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Error al conectar/consultar la BD VMT ({host}:{port}/{db_name}): {e}"
        ) from e

@task(name="Consultar Catálogo MITIC")
def get_mitic_catalogo(fecha: Optional[str] = None):
    mitic_engine = create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

    if fecha is None:
        fecha = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # linea se separó de catalogo_rutas → lineas + linea_ruta_catalogo (malla temporal).
    # Preferimos la vinculación vigente en :fecha; si no hay, la más reciente disponible.
    mitic_query = text("""
        SELECT
            cr.ruta_hex,
            cr.id_eot_catalogo,
            COALESCE(NULLIF(TRIM(cr.identificador_troncal), ''), l.identificador_troncal) AS identificador_troncal,
            l.numero_linea AS linea,
            cr.identificacion
        FROM catalogo_rutas cr
        LEFT JOIN LATERAL (
            SELECT lrc2.id_linea
            FROM linea_ruta_catalogo lrc2
            WHERE lrc2.ruta_hex = cr.ruta_hex
            ORDER BY
                CASE
                    WHEN lrc2.fecha_inicio <= CAST(:fecha AS date)
                     AND (lrc2.fecha_fin IS NULL OR lrc2.fecha_fin >= CAST(:fecha AS date))
                    THEN 0 ELSE 1
                END,
                lrc2.fecha_inicio DESC
            LIMIT 1
        ) lrc ON TRUE
        LEFT JOIN lineas l ON l.id_linea = lrc.id_linea
    """)
    eots_query = "SELECT cod_catalogo, eot_nombre, gre_id FROM eots"
    gremios_query = "SELECT gre_id, gre_nombre FROM gremios"

    with mitic_engine.connect() as conn:
        mitic_df = pd.read_sql(mitic_query, conn, params={"fecha": fecha})
        eots_df = pd.read_sql(eots_query, conn)
        gremios_df = pd.read_sql(gremios_query, conn)

    return mitic_df, eots_df, gremios_df

@task(name="Procesar e Insertar Datos")
def process_and_insert(azure_df, mitic_df, eots_df, gremios_df, fecha_inicio_str):
    if azure_df.empty:
        print("No hay datos de Azure para procesar.")
        return
    
    mitic_engine = create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    
    # Unir (machear) los datos
    merged_df = pd.merge(azure_df, mitic_df, how='left', left_on='idrutaestacion', right_on='ruta_hex')
    merged_df = pd.merge(merged_df, eots_df, how='left', left_on='id_eot_catalogo', right_on='cod_catalogo')
    merged_df = pd.merge(merged_df, gremios_df, how='left', left_on='gre_id', right_on='gre_id')
    
    columns_to_keep = ['idsam', 'idrutaestacion', 'fecha', 'hora', 'id_eot_catalogo',
                       'identificador_troncal', 'linea', 'identificacion', 'eot_nombre', 'gre_nombre', 'validaciones']
    merged_df = merged_df[columns_to_keep]
    
    try:
        with mitic_engine.connect() as conn:
            existing_count = conn.execute(
                text("SELECT COUNT(*) FROM servicios_diarios WHERE fecha = :fecha"),
                {"fecha": fecha_inicio_str}
            ).scalar()
            
            if existing_count > 0:
                print(f"Ya existen {existing_count} registros para la fecha {fecha_inicio_str}.")
                
                # No-interactivo para Prefect o ejecuciones programadas
                is_scheduled = (
                    os.getenv('PREFECT_MODE') == 'true' or 
                    os.getenv('PREFECT_FLOW_RUN_ID') is not None or
                    not sys.stdin or 
                    not sys.stdin.isatty()
                )
                
                if is_scheduled:
                    print("Ejecución no interactiva detectada. Continuando con la eliminación de registros...")
                    respuesta = 's'
                else:
                    try:
                        respuesta = input("¿Desea eliminar los registros existentes y continuar? (s/n) [s]: ").strip().lower() or 's'
                    except EOFError:
                        respuesta = 's'
                
                if respuesta.lower() == 's':
                    conn.execute(text("DELETE FROM servicios_diarios WHERE fecha = :fecha"), {"fecha": fecha_inicio_str})
                    conn.commit()
                    print(f"Se eliminaron {existing_count} registros.")
                else:
                    print("Operación cancelada.")
                    return

            total_rows = len(merged_df)
            print(f"Insertando {total_rows} registros...")
            merged_df.to_sql('servicios_diarios', mitic_engine, if_exists='append', index=False, method='multi', chunksize=1000)
            print("Inserción completada con éxito.")
            
    except Exception as e:
        print(f"Error en la inserción: {e}")
        registrar_alerta(f"Error en process_and_insert: {str(e)[:200]}")
        raise

def _parse_fecha(s: str):
    """Parsea YYYY-MM-DD; lanza ValueError si es inválido."""
    return datetime.strptime(s.strip(), '%Y-%m-%d')

@flow(name="Servicios Diarios V3 Flow")
def run_servicios_diarios(fecha: Optional[str] = None, fecha_hasta: Optional[str] = None):
    """
    Procesa servicios diarios para una fecha o un rango de fechas (inclusive).
    - fecha solo: un día.
    - fecha y fecha_hasta: desde fecha hasta fecha_hasta (ambas inclusive).
    """
    ayer = datetime.now() - timedelta(days=1)
    if fecha:
        try:
            fecha_desde_dt = _parse_fecha(fecha)
        except ValueError:
            print(f"Fecha inválida: {fecha}. Usando ayer.")
            fecha_desde_dt = ayer
    else:
        fecha_desde_dt = ayer

    if fecha_hasta:
        try:
            fecha_hasta_dt = _parse_fecha(fecha_hasta)
        except ValueError:
            print(f"Fecha hasta inválida: {fecha_hasta}. Procesando solo {fecha_desde_dt.date()}.")
            fecha_hasta_dt = fecha_desde_dt
    else:
        fecha_hasta_dt = fecha_desde_dt

    if fecha_hasta_dt < fecha_desde_dt:
        fecha_desde_dt, fecha_hasta_dt = fecha_hasta_dt, fecha_desde_dt

    dias = (fecha_hasta_dt - fecha_desde_dt).days + 1
    print(f"Iniciando proceso para el rango: {fecha_desde_dt.date()} a {fecha_hasta_dt.date()} ({dias} día(s))")

    try:
        current = fecha_desde_dt
        while current <= fecha_hasta_dt:
            fecha_inicio = current.strftime('%Y-%m-%d')
            fecha_fin = (current + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"  Procesando fecha: {fecha_inicio}")
            mitic_df, eots_df, gremios_df = get_mitic_catalogo(fecha_inicio)
            azure_df = get_azure_data(fecha_inicio, fecha_fin)
            process_and_insert(azure_df, mitic_df, eots_df, gremios_df, fecha_inicio)
            current += timedelta(days=1)

        if not verificar_existencia_alertas():
            registrar_ejecucion_correcta()
    except Exception as e:
        print(f"Error crítico en el flujo: {e}")
        registrar_alerta(f"Error crítico en el flujo principal: {str(e)[:200]}")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help', 'help'):
        print(__doc__)
        sys.exit(0)

    arg_fecha = sys.argv[1] if len(sys.argv) > 1 else None
    arg_fecha_hasta = sys.argv[2] if len(sys.argv) > 2 else None
    run_servicios_diarios(arg_fecha, arg_fecha_hasta)
