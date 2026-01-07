import os
import requests
import pandas as pd
from datetime import datetime

def fetch_data(ns_url, ns_secret):
    """Alle Insulin-Daten aus treatments.json holen"""
    url = f"{ns_url}/api/v1/treatments.json?count=1000&token={ns_secret}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def process_data(data):
    """Daten in DataFrame umwandeln und nach Typ summieren"""
    records = []
    for d in data:
        # Datum extrahieren
        dt = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00")).date()
        record = {"date": dt, "bolus": 0, "smb": 0, "basal": 0}
        if d.get("insulin"):
            if d.get("insulinType") == "Bolus":
                record["bolus"] = d["insulin"]
            elif d.get("insulinType") == "SMB":
                record["smb"] = d["insulin"]
        if d.get("basal"):
            record["basal"] = d["basal"]
        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["date", "basal", "smb", "bolus", "total"])
    
    # Summen pro Tag berechnen
    daily = df.groupby("date").sum()
    daily["total"] = daily["basal"] + daily["smb"] + daily["bolus"]
    daily = daily.reset_index()
    return daily

def write_html(df):
    """HTML-Tabelle erstellen"""
    html_table = df.to_html(index=False, float_format="{:.2f}".format)
    with open("index.html", "w") as f:
        f.write(f"<h2>Tägliche TDD Übersicht</h2>\n{html_table}")
    print("index.html erfolgreich erstellt!")

def main():
    ns_url = os.environ.get("NS_URL")
    ns_secret = os.environ.get("NS_SECRET")
    if not ns_url or not ns_secret:
        raise ValueError("NS_URL oder NS_SECRET fehlt in den Environment-Variablen!")

    data = fetch_data(ns_url, ns_secret)
    daily = process_data(data)
    write_html(daily)

if __name__ == "__main__":
    main()
