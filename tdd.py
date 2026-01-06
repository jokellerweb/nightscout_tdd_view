import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

NS_URL = os.getenv("NS_URL")
NS_SECRET = os.getenv("NS_SECRET")

# Treatments abrufen
r = requests.get(f"{NS_URL}/api/v1/treatments.json?count=5000&api_secret={NS_SECRET}")
data = r.json()

# Dictionary für tägliche TDD
tdd_per_day = defaultdict(lambda: {"bolus":0, "basal":0, "total":0})

for t in data:
    date = datetime.fromisoformat(t["created_at"][:-1]).date()  # Datum extrahieren
    if t["eventType"].lower() == "bolus":
        tdd_per_day[date]["bolus"] += t.get("amount",0)
    elif t["eventType"].lower() == "temp basal":
        # rate in U/h, duration in Minuten (falls vorhanden)
        duration_min = t.get("duration",0)/60  # Stunden
        tdd_per_day[date]["basal"] += t.get("rate",0) * duration_min

# Gesamt berechnen
for d in tdd_per_day:
    tdd_per_day[d]["total"] = tdd_per_day[d]["bolus"] + tdd_per_day[d]["basal"]

# Ausgabe
print("Tag       Bolus   Basal   Gesamt")
for d in sorted(tdd_per_day.keys(), reverse=True):
    bolus = tdd_per_day[d]["bolus"]
    basal = tdd_per_day[d]["basal"]
    total = tdd_per_day[d]["total"]
    print(f"{d}   {bolus:.1f}   {basal:.1f}   {total:.1f}")
