
import psycopg2
from config.settings import settings

def check_franja_40():
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        with conn.cursor() as cur:
            cur.execute("SELECT id_franja, denominacion, id_tipo_dia, activo, inicio_vigencia, fin_vigencia FROM control_metricas.franjas_operativas WHERE id_franja = 40")
            row = cur.fetchone()
            print(f"ID: {row[0]}")
            print(f"Nombre: {row[1]}")
            print(f"Tipo: {row[2]}")
            print(f"Activo: {row[3]}")
            print(f"Inicio: {row[4]}")
            print(f"Fin: {row[5]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_franja_40()
