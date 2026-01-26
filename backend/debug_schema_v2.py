
from database.connection import get_db_connection

def list_columns():
    db = next(get_db_connection())
    cursor = db.get_cursor()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'servicios_diarios' ORDER BY ordinal_position")
    columns = cursor.fetchall()
    print("\nColumns in servicios_diarios:")
    for c in columns:
        print(c['column_name'])
    cursor.close()

if __name__ == "__main__":
    list_columns()
