
from database.connection import get_db_connection

def list_tables():
    db = next(get_db_connection())
    cursor = db.get_cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print("Tables in public schema:")
    for t in tables:
        print(t['table_name'])
        
    # Also check if there is a 'rutas' table and what columns it has
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'servicios_diarios'")
    columns = cursor.fetchall()
    print("\nColumns in servicios_diarios:")
    for c in columns:
        print(c['column_name'])
        
    cursor.close()

if __name__ == "__main__":
    list_tables()
