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
    days = defaultdict(lambda: {"basal": 0.0, "bolus": 0.0, "smb": 0.0, "prod_dates": []})

    for t in data:
        ts = t.get("timestamp")
        if not ts:
            continue
        day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        et = t.get("eventType", "")

        # Produktionsdatum speichern
        prod_date = t.get("created_at", "")
        if prod_date:
            days[day]["prod_dates"].append(prod_date)

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
            duration = float(t.get("duration", 0) or 0)  # Minuten
            amount = t.get("amount")                      # manchmal als absolutes Amount
            if amount is not None:
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
    html += """
    <style>
      table {border-collapse: collapse; width: 100%;}
      th, td {border: 1px solid #444; padding: 8px; text-align: center;}
      th {background-color: #555; color: #fff;}
      tr:nth-child(even) {background-color: #eee;}
    </style>
    </head><body>
    """
    html += "<h2>Tägliche TDD Übersicht</h2>"
    html += "<table><tr><th>Datum</th><th>Bolus (U)</th><th>Basal (U)</th><th>SMB (U)</th><th>Gesamt (U)</th><th>Produktionsdatum</th></tr>"

    tdd_values = []

    for d in sorted_days[:7]:  # letzte 7 Tage
        basal = round_u(days[d]["basal"])
        bolus = round_u(days[d]["bolus"])
        smb = round_u(days[d]["smb"])
        total = round_u(basal + bolus + smb)
        tdd_values.append((d, total))
        prod_dates = ", ".join(days[d]["prod_dates"]) if days[d]["prod_dates"] else ""
        html += f"<tr><td>{d}</td><td>{bolus}</td><td>{basal}</td><td>{smb}</td><td>{total}</td><td>{prod_dates}</td></tr>"

    html += "</table>"

    # Durchschnittswerte
    all_values = [v for _, v in tdd_values]
    avg_all = round_u(sum(all_values)/len(all_values)) if all_values else 0
    avg_last2 = round_u(sum(all_values[:2])/len(all_values[:2])) if len(all_values)>=2 else 0
    avg_last3 = round_u(sum(all_values[:3])/len(all_values[:3])) if len(all_values)>=3 else 0
    avg_last4 = round_u(sum(all_values[:4])/len(all_values[:4])) if len(all_values)>=4 else 0
    avg_last7 = round_u(sum(all_values[:7])/len(all_values[:7])) if len(all_values)>=1 else 0

    html += "<h3>Durchschnittliche TDD:</h3>"
    html += f"<p>Alle Daten: {avg_all} U</p>"
    html += f"<p>Letzte 2 Tage: {avg_last2} U</p>"
    html += f"<p>Letzte 3 Tage: {avg_last3} U</p>"
    html += f"<p>Letzte 4 Tage: {avg_last4} U</p>"
    html += f"<p>Letzte 7 Tage: {avg_last7} U</p>"

    html += "</body></html>"
    return html

# -------------------
# Main
# -------------------
def main():
    try:
        data = fetch_treatments()
        if not data:
            print("⚠️ Keine Treatments gefunden")
            return
        days = calculate_tdd(data)
        html = generate_html(days)

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("✅ index.html erstellt")
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    main()
