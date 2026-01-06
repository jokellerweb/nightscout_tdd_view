import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

NS_URL = os.getenv("NS_URL")
NS_SECRET = os.getenv("NS_SECRET")

# Treatments abrufen
r = requests.get(f"{NS_URL}/api/v1/treatments.json?count=1000&api_secret={NS_SECRET}")
data = r.json()

# Dictionary für tägliche TDD
tdd_per_day = defaultdict(lambda: {"bolus":0, "basal":0, "total":0})

for t in data:
    date = datetime.fromisoformat(t["created_at"][:-1]).date()  # Datum extrahieren
    if t["eventType"].lower() == "bolus":
        tdd_per_day[date]["bolus"] += t.get("amount",0)
    elif t["eventType"].lower() == "temp basal":
        duration_min = t.get("duration",0)/60  # Stunden
        tdd_per_day[date]["basal"] += t.get("rate",0) * duration_min

# Gesamt berechnen
for d in tdd_per_day:
    tdd_per_day[d]["total"] = tdd_per_day[d]["bolus"] + tdd_per_day[d]["basal"]

# Letzte 7 Tage
today = datetime.today().date()
last_7_days = [today - timedelta(days=i) for i in range(7)]

# HTML erzeugen
html = "<html><head><title>TDD Übersicht</title></head><body>"
html += "<h2>TDD pro Tag (letzte 7 Tage)</h2>"
html += "<table border='1' cellpadding='5'><tr><th>Datum</th><th>Bolus (U)</th><th>Basal (U)</th><th>Gesamt (U)</th></tr>"

for d in sorted(last_7_days, reverse=True):
    bolus = tdd_per_day[d]["bolus"] if d in tdd_per_day else 0
    basal = tdd_per_day[d]["basal"] if d in tdd_per_day else 0
    total = tdd_per_day[d]["total"] if d in tdd_per_day else 0
    html += f"<tr><td>{d}</td><td>{bolus:.1f}</td><td>{basal:.1f}</td><td>{total:.1f}</td></tr>"

html += "</table>"

# Durchschnitt berechnen
all_totals = [tdd_per_day[d]["total"] for d in tdd_per_day]
html += "<h3>Durchschnittliche TDD:</h3>"
if all_totals:
    html += f"<p>Alle Daten: {sum(all_totals)/len(all_totals):.1f} U</p>"
    for days in [2,3,4]:
        recent_totals = [tdd_per_day[d]["total"] for d in sorted(last_7_days[:days], reverse=True) if d in tdd_per_day]
        if recent_totals:
            html += f"<p>Letzte {days} Tage: {sum(recent_totals)/len(recent_totals):.1f} U</p>"
else:
    html += "<p>Keine Daten verfügbar</p>"

html += "</body></html>"

# HTML-Datei schreiben
with open("index.html","w") as f:
    f.write(html)

print("HTML-Tabelle erstellt: index.html")
