from database.connection import get_db_connection
from datetime import date

def main():
    db = next(get_db_connection())
    cursor = db.get_cursor()
    dates = ['2026-05-11', '2026-05-18', '2026-05-25', '2026-06-01', '2026-06-08']
    
    print("t_casuisticas_lluvia:")
    for d in dates:
        cursor.execute("SELECT mm_caidos FROM control_metricas.t_casuisticas_lluvia WHERE fecha_evento=%s", (d,))
        res = cursor.fetchone()
        if res:
            print(f"Date: {d}, Rain: {res['mm_caidos']} mm")
        else:
            print(f"Date: {d}, No rain data")
            
    print("\ndias_atipicos:")
    for d in dates:
        cursor.execute("SELECT descripcion FROM control_metricas.dias_atipicos WHERE fecha=%s", (d,))
        res = cursor.fetchone()
        if res:
            print(f"Date: {d}, Atipico: {res['descripcion']}")
        else:
            print(f"Date: {d}, Not atipico")
            
    cursor.close()

if __name__ == '__main__':
    main()
