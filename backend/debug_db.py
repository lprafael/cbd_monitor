
import os
import sys
from datetime import date
from database.connection import get_db_connection
from routes.cbd_data import get_parametros_minimos

# Mock the current working directory to be the backend folder so imports work
sys.path.append(os.getcwd())

def debug_query():
    print("Connecting to DB...")
    db = next(get_db_connection())
    
    target_date = date(2025, 11, 4)
    id_tipo_dia = 5 # Laboral
    
    print(f"Querying for date: {target_date}, id_tipo_dia: {id_tipo_dia}")
    
    params = get_parametros_minimos(db, id_tipo_dia, target_date)
    
    print(f"Found {len(params)} parameters.")
    for k, v in params.items():
        print(f"Franja {k}: {v}")

    # Also run a raw query to check the rows without date filter to see what's there
    cursor = db.get_cursor()
    cursor.execute("SELECT id, id_franja, vigencia_desde, vigencia_hasta FROM control_metricas.cbd_parametros_minimos WHERE id_tipo_dia = 5 AND id_franja = 30")
    rows = cursor.fetchall()
    print("\nRaw check for Franja 30 (Laboral):")
    for row in rows:
        print(dict(row))
        
    cursor.close()

if __name__ == "__main__":
    debug_query()
