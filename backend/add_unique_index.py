
import os
import sys
from database.connection import get_db_connection

# Mock current working directory
sys.path.append(os.getcwd())

def add_unique_index():
    print("Adding unique index to control_metricas.cbd_detalle_buses...")
    db = next(get_db_connection())
    conn = db.get_cursor().connection
    cursor = conn.cursor()
    
    # Nombre del índice
    index_name = "idx_cbd_detalle_buses_unique_hora"
    
    # Query para crear el índice único
    query = f"""
    CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
    ON control_metricas.cbd_detalle_buses (id_eot_vmt_hex, fecha, hora, mean_id);
    """
    
    try:
        print(f"Executing: {query}")
        cursor.execute(query)
        conn.commit()
        print("Index created successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Error creating index: {e}")
        
    cursor.close()

if __name__ == "__main__":
    add_unique_index()
