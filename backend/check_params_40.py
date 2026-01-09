
import psycopg2
from config.settings import settings

def check_params():
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_franja, cbd_minimo_hora, cbd_minimo_franja, vigencia_desde, vigencia_hasta
                FROM control_metricas.cbd_parametros_minimos
                WHERE id_franja = 40
            """)
            rows = cur.fetchall()
            for r in rows:
                print(r)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_params()
