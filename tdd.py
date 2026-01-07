import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# -------------------
# Hilfsfunktionen
# -------------------
def round_u(v):
    return round(v, 2)

def fetch_treatments():
    NS_URL = os.environ.get("NS_URL")
    NS_SECRET = os.environ.get("NS_SECRET")
    if not NS_URL or not NS_SECRET:
        raise ValueError("NS_URL oder NS_SECRET nicht gesetzt")
    
    url = f"{NS_URL}/api/v1/treatments.json?count=10000&api_secret={NS_SECRET}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

# -------------------
# TDD Berechnung
# -------------------
def calculate_tdd(data):
    days = defaultdict(lambda: {"basal": 0.0, "bolus": 0.0, "smb": 0.0})

    for t in data:
        ts = t.get("timestamp")
        if not ts:
            continue
        day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        et = t.get("eventType", "")

        # ---------- BOLUS ----------
        bolus_events = ["Bolus", "Correction Bolus", "Meal Bolus", "Snack Bolus", "Extended Bolus", "SMB", "Microbolus"]
        if et in bolus_events:
            insulin = float(t.get("insulin", 0) or 0)
            if insulin > 0:
                if "SMB" in et or "Microbolus" in et:
                    days[day]["smb"] += insulin
                else:
                    days[day]["bolus"] += insulin

        # ---------- BASAL ----------
        if et == "Temp Basal":
            rate = float(t.get("rate", 0) or 0)          # U/h
            duration = float(t.get("duration", 0) or 0)  # minutes
            amount = t.get("amount")                      # manchmal als absolutes Amount
            if amount:
                basal_units = float(amount)
            elif rate > 0 and duration > 0:
                basal_units = rate * (duration / 60.0)
            else:
                basal_units = 0
            days[day]["basal"] += basal_units

    return days

# -------------------
# HTML erzeugen
# -------------------
def generate_html(days):
    sorted_days = sorted(days.keys(), reverse=True)
    html = "<html><head><meta charset='utf-8'><title>TDD Übersicht</title>"
    html += "<style>table{border-collapse:collapse;}th,td{border:1px solid #444;padding:5px;text-align:center;}th{background:#eee;}</style></head><body>"
    html += "<h2>Tägliche TDD Übersicht</h2>"
    html += "<table><tr><th>Datum</th><th>Bolus (U)</th><th>Basal (U)</th><th>SMB (U)</th><th>Gesamt (U)</th></tr>"

    tdd_values = []

    for d in sorted_days:
        basal = round_u(days[d]["basal"])
        bolus = round_u(days[d]["bolus"])
        smb = round_u(days[d]["smb"])
        total = round_u(basal + bolus + smb)
        tdd_values.append((d, total))
        html += f"<tr><td>{d}</td><td>{bolus}</td><td>{basal}</td><td>{smb}</td><td>{total}</td></tr>"

    html += "</table>"

    # Durchschnittswerte
    if tdd_values:
        avg_all = sum(v for _, v in tdd_values) / len(tdd_values)

        today = sorted_days[0]
        last2 = [v for d, v in tdd_values if d >= today - timedelta(days=1)]
        last3 = [v for d, v in tdd_values if d >= today - timedelta(days=2)]
        last4 = [v for d, v in tdd_values if d >= today - timedelta(days=3)]
        last7 = [v for d, v in tdd_values if d >= today - timedelta(days=6)]

        html += "<h3>Durchschnittliche TDD:</h3>"
        html += f"<p>Alle Daten: {round_u(avg_all)} U</p>"
        html += f"<p>Letzte 2 Tage: {round_u(sum(last2)/len(last2)) if last2 else 0:.2f} U</p>"
        html += f"<p>Letzte 3 Tage: {round_u(sum(last3)/len(last3)) if last3 else 0:.2f} U</p>"
        html += f"<p>Letzte 4 Tage: {round_u(sum(last4)/len(last4)) if last4 else 0:.2f} U</p>"
        html += f"<p>Letzte 7 Tage: {round_u(sum(last7)/len(last7)) if last7 else 0:.2f} U</p>"

    html += "</body></html>"
    return html

# -------------------
# Main
# -------------------
def main():
    data = fetch_treatments()
    days = calculate_tdd(data)
    html = generate_html(days)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html erstellt ✅")

if __name__ == "__main__":
    main()
