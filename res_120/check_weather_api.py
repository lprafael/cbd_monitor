import requests
from datetime import datetime

def check_open_meteo():
    fecha_str = "2026-01-09"
    latitud = -25.3
    longitud = -57.6
    
    params = {
        'latitude': latitud,
        'longitude': longitud,
        'start_date': fecha_str,
        'end_date': fecha_str,
        'daily': ['weathercode', 'precipitation_sum'],
        'timezone': 'America/Asuncion',
        'precipitation_unit': 'mm'
    }
    
    try:
        response = requests.get('https://archive-api.open-meteo.com/v1/archive', params=params)
        data = response.json()
        if 'daily' in data:
            precip = data['daily']['precipitation_sum'][0]
            code = data['daily']['weathercode'][0]
            print(f"Open-Meteo para {fecha_str}:")
            print(f"Precipitación: {precip} mm")
            print(f"Código clima: {code}")
        else:
            print("No daily data in response")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_open_meteo()
