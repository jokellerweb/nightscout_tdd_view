import requests
import os

NS_URL = os.getenv("NS_URL")
NS_SECRET = os.getenv("NS_SECRET")

# Minimaler Test: nur Treatments abrufen
r = requests.get(f"{NS_URL}/api/v1/treatments.json?count=5&api_secret={NS_SECRET}")
if r.status_code == 200:
    print("Treatments fetched successfully")
    print(r.json())
else:
    print("Failed to fetch treatments", r.status_code)
