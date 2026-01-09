
import os
import sys
from database.connection import get_db_connection
from sqlalchemy import text

# Mock current working directory
sys.path.append(os.getcwd())

def check_indexes():
    print("Checking indexes for control_metricas.cbd_detalle_buses...")
    db = next(get_db_connection())
    conn = db.get_cursor().connection
    cursor = conn.cursor()
    
    query = """
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'cbd_detalle_buses' 
    AND schemaname = 'control_metricas';
    """
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if not results:
            print("No indexes found!")
        for row in results:
            print(f"Index: {row[0]}")
            print(f"Def: {row[1]}")
            print("-" * 20)
    except Exception as e:
        print(f"Error: {e}")
        
    cursor.close()

if __name__ == "__main__":
    check_indexes()
