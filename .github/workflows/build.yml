import requests
import pandas as pd
from datetime import datetime, timedelta

# === CONFIG ===
NIGHTSCOUT_URL = "https://dein-nightscout-url.herokuapp.com/api/v1"  # z.B. https://mybg.ns.io/api/v1
API_KEY = "DEIN_API_KEY"  # falls notwendig

# Zeitraum: letzte 7 Tage
END_DATE = datetime.utcnow()
START_DATE = END_DATE - timedelta(days=7)

# === FUNKTIONEN ===
def fetch_entries(entry_type):
    """Ruft Einträge vom Typ 'bolus' oder 'basal' aus Nightscout ab."""
    url = f"{NIGHTSCOUT_URL}/{entry_type}.json"
    params = {
        "find[date][$gte]": int(START_DATE.timestamp() * 1000),
        "find[date][$lte]": int(END_DATE.timestamp() * 1000),
        "count": 1000
    }
    headers = {"API-SECRET": API_KEY} if API_KEY else {}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()

def process_bolus(entries):
    """Summiert normale Bolus- und SMB-Mengen pro Tag."""
    data = {}
    for e in entries:
        date = datetime.fromtimestamp(e['date']/1000).date()
        if date not in data:
            data[date] = {"bolus": 0, "smb": 0}
        if e.get("bolus_type") == "SMB" or e.get("type") == "SMB":
            data[date]["smb"] += e.get("amount", 0)
        else:
            data[date]["bolus"] += e.get("amount", 0)
    return data

def process_basal(entries):
    """Summiert Basal pro Tag: rate * duration (in h)."""
    data = {}
    for e in entries:
        date = datetime.fromtimestamp(e['time']/1000).date() if 'time' in e else datetime.fromtimestamp(e['date']/1000).date()
        duration_min = e.get("duration", 0) / 60000  # ms → min
        basal_units = e.get("rate", 0) * (duration_min / 60)
        if date not in data:
            data[date] = 0
        data[date] += basal_units
    return data

# === DATEN LADEN ===
bolus_entries = fetch_entries("bolus")
basal_entries = fetch_entries("basal")

bolus_data = process_bolus(bolus_entries)
basal_data = process_basal(basal_entries)

# === TABELLE ERSTELLEN ===
dates = [START_DATE.date() + timedelta(days=i) for i in range(8)]
rows = []
for d in dates:
    bolus = bolus_data.get(d, {}).get("bolus", 0)
    smb = bolus_data.get(d, {}).get("smb", 0)
    basal = basal_data.get(d, 0)
    total = bolus + smb + basal
    rows.append({
        "Datum": d.strftime("%Y-%m-%d"),
        "Bolus (U)": round(bolus, 2),
        "Basal (U)": round(basal, 2),
        "SMB (U)": round(smb, 2),
        "Gesamt (U)": round(total, 2)
    })

df = pd.DataFrame(rows)

# === Tabelle ausgeben mit leicht grauen Zeilen ===
def style_table(df):
    return df.style \
        .set_table_styles([
            {"selector": "th", "props": [("background-color", "#4CAF50"), ("color", "white"), ("font-weight", "bold")]}  # Kopfzeile
        ]) \
        .apply(lambda x: ['background-color: #f2f2f2' if i%2 else '' for i in range(len(x))], axis=1) \
        .format("{:.2f}", subset=["Bolus (U)", "Basal (U)", "SMB (U)", "Gesamt (U)"])

styled = style_table(df)
styled.to_html("tdd_uebersicht.html")  # optional als HTML speichern
styled
