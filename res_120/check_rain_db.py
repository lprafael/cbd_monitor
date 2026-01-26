import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

def check_rain():
    current_dir = Path(__file__).parent.absolute()
    backend_env = current_dir.parent / 'backend' / '.env'
    load_dotenv(dotenv_path=backend_env)
    
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '2026'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        fecha = '2026-01-09'
        print(f"Buscando lluvia para {fecha}...")
        
        cur.execute("""
            SELECT * FROM control_metricas.t_casuisticas_lluvia
            WHERE fecha_evento = %s
        """, (fecha,))
        
        rows = cur.fetchall()
        if not rows:
            print(f"No hay registros para {fecha} en control_metricas.t_casuisticas_lluvia")
        else:
            colnames = [desc[0] for desc in cur.description]
            for row in rows:
                data = dict(zip(colnames, row))
                print(f"ID: {data['id']}")
                print(f"Fecha: {data['fecha_evento']}")
                print(f"Precipitación: {data['mm_caidos']} mm")
                print(f"Comprobado: {data['registro_comprobado']}")
                print(f"Descripción: {data.get('descripcion', 'N/A')}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_rain()
