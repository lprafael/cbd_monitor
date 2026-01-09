
import psycopg2
from datetime import date
from config.settings import settings

def check_franjas():
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        fecha_analisis = date(2025, 12, 2)
        id_tipo_dia = 5
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_franja, denominacion
                FROM control_metricas.franjas_operativas
                WHERE id_tipo_dia = %s
                  AND activo = TRUE
                  AND (inicio_vigencia IS NULL OR inicio_vigencia <= %s)
                  AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
                ORDER BY hora_inicio
            """, (id_tipo_dia, fecha_analisis, fecha_analisis))
            rows = cur.fetchall()
            print(f"Total franjas: {len(rows)}")
            for r in rows:
                print(f"{r[0]}: {r[1]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_franjas()
