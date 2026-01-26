from database.connection import get_db_connection

def check_rain_casuisticas():
    db = next(get_db_connection())
    cursor = db.get_cursor()
    try:
        # Note plural: t_casuisticas_lluvia (found in previous step)
        cursor.execute("SELECT * FROM control_metricas.t_casuisticas_lluvia LIMIT 1")
        row = cursor.fetchone()
        if row:
            print("Columns in control_metricas.t_casuisticas_lluvia:")
            print(row.keys())
        else:
            print("Table found but empty.")
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'control_metricas' 
                AND table_name = 't_casuisticas_lluvia'
            """)
            cols = cursor.fetchall()
            for c in cols:
                print(c)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()

if __name__ == "__main__":
    check_rain_casuisticas()
