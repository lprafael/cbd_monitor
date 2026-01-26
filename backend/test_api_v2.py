
from database.connection import get_db_connection
import requests
import json

def get_real_sample():
    db = next(get_db_connection())
    c = db.get_cursor()
    c.execute("SELECT id_eot_catalogo, fecha FROM public.servicios_diarios LIMIT 1")
    row = c.fetchone()
    if not row:
        return None
    return row['id_eot_catalogo'], row['fecha'].month, row['fecha'].year

sample = get_real_sample()
if sample:
    eot_id, month, year = sample
    url = "http://localhost:8000/api/verify-290"
    payload = {"eot_id": eot_id, "month": month, "year": year}
    print(f"Testing with EOT {eot_id}, Month {month}, Year {year}")
    resp = requests.post(url, json=payload)
    data = resp.json()
    if 'detalles_troncal' in data and len(data['detalles_troncal']) > 0:
        first_franja = data['detalles_troncal'][0]['resultados_franjas'][0]
        print(json.dumps(first_franja, indent=2))
    else:
        print("No troncales found in response")
else:
    print("No data in servicios_diarios")
