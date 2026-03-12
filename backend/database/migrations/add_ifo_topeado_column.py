
import psycopg2
import os
import sys

# Add backend to path to import settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from config.settings import settings
except ImportError:
    # Fallback if settings cannot be imported
    class Settings:
        def __init__(self):
            from dotenv import load_dotenv
            load_dotenv('backend/.env')
            self.DB_HOST = os.getenv('DB_HOST', 'localhost')
            self.DB_PORT = os.getenv('DB_PORT', '5432')
            self.DB_NAME = os.getenv('DB_NAME', 'cbd_monitor')
            self.DB_USER = os.getenv('DB_USER', 'postgres')
            self.DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    settings = Settings()

def add_columns():
    try:
        print(f"Connecting to {settings.DB_NAME} on {settings.DB_HOST}...")
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            print("Agregando columna ifo_topeado...")
            try:
                cur.execute("ALTER TABLE control_metricas.ifo_historico ADD COLUMN ifo_topeado numeric(10,4);")
                cur.execute("COMMENT ON COLUMN control_metricas.ifo_historico.ifo_topeado IS 'Índice IFO topeado al 110% (0.0 a 1.1)';")
                print("  ✓ ifo_topeado agregada")
            except psycopg2.errors.DuplicateColumn:
                print("  ⚠ Columna ifo_topeado ya existe")
            except Exception as e:
                print(f"  ✗ Error agregando columna: {e}")
                
        conn.close()
        print("\nProceso completado.")
        
    except Exception as e:
        print(f"Error crítico: {e}")

if __name__ == "__main__":
    add_columns()
