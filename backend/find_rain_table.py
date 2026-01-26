from database.connection import get_db_connection

def find_rain_table():
    db = next(get_db_connection())
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name ILIKE '%lluvia%'")
        rows = cursor.fetchall()
        print("Tables finding 'lluvia':")
        for r in rows:
            print(f"{r['table_schema']}.{r['table_name']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()

if __name__ == "__main__":
    find_rain_table()
