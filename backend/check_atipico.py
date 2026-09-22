from database.connection import get_db_connection
db = next(get_db_connection())
cursor = db.get_cursor()
cursor.execute("SELECT * FROM control_metricas.dias_atipicos WHERE fecha = %s", ('2026-06-08',))
print("dias_atipicos:", cursor.fetchall())
cursor.execute("SELECT * FROM control_metricas.t_casuisticas_lluvia WHERE fecha_evento = %s", ('2026-06-08',))
print("lluvia:", cursor.fetchall())
cursor.close()
