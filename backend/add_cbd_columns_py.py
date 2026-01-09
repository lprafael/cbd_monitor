
import psycopg2
from config.settings import settings

def add_columns():
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            print("Agregando columna cbd_indice...")
            try:
                cur.execute("ALTER TABLE control_metricas.ifo_historico ADD COLUMN cbd_indice numeric(10,4);")
                cur.execute("COMMENT ON COLUMN control_metricas.ifo_historico.cbd_indice IS 'Índice CBD de la franja (0.0 a 1.0+)';")
                print("  ✓ cbd_indice agregada")
            except psycopg2.errors.DuplicateColumn:
                print("  ⚠ Columna cbd_indice ya existe")
            
            print("Agregando columna cbd_cantidad...")
            try:
                cur.execute("ALTER TABLE control_metricas.ifo_historico ADD COLUMN cbd_cantidad integer;")
                cur.execute("COMMENT ON COLUMN control_metricas.ifo_historico.cbd_cantidad IS 'Cantidad de buses únicos operando en la franja';")
                print("  ✓ cbd_cantidad agregada")
            except psycopg2.errors.DuplicateColumn:
                print("  ⚠ Columna cbd_cantidad ya existe")
                
        conn.close()
        print("\nColumnas agregadas exitosamente")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_columns()
