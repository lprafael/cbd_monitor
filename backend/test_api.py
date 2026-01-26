import requests
import json

url = "http://localhost:8000/api/verify-290"
payload = {
    "eot_id": 1, # Use a valid ID from the logs if known, or try 1
    "month": 1,
    "year": 2026
}
try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
