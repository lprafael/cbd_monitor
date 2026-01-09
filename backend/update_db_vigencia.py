
import os
import sys
from database.connection import get_db_connection

# Mock the current working directory to be the backend folder so imports work
sys.path.append(os.getcwd())

def update_vigencia():
    print("Connecting to DB...")
    db = next(get_db_connection())
    conn = db.get_cursor().connection
    cursor = conn.cursor()
    
    print("Updating vigencia_desde for Laboral parameters...")
    
    # Check before
    cursor.execute("SELECT count(*) FROM control_metricas.cbd_parametros_minimos WHERE id_tipo_dia = 5 AND vigencia_desde = '2025-11-17'")
    count_before = cursor.fetchone()[0]
    print(f"Records to update: {count_before}")
    
    update_query = """
    UPDATE control_metricas.cbd_parametros_minimos
    SET vigencia_desde = '2025-11-01'
    WHERE id_tipo_dia = 5 
      AND vigencia_desde = '2025-11-17';
    """
    
    try:
        cursor.execute(update_query)
        updated_rows = cursor.rowcount
        conn.commit()
        print(f"Updated {updated_rows} rows successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error updating DB: {e}")
        
    cursor.close()

if __name__ == "__main__":
    update_vigencia()
