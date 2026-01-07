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
    records = []
    for d in data:
        dt = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00")).date()
        record = {"date": dt, "bolus": 0.0, "diverses": 0.0, "basal": 0.0}

        # Insulin nur berücksichtigen, wenn nicht None
        insulin = d.get("insulin")
        if insulin is not None:
            if d.get("eventType") == "Correction Bolus":
                record["bolus"] = float(insulin)
            else:
                record["diverses"] = float(insulin)

        # Basalrate nur, wenn Wert vorhanden
        if d.get("eventType") == "Temp Basal":
            rate = d.get("rate")
            if rate is not None:
                record["basal"] = float(rate)

        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["date", "basal", "diverses", "bolus", "total"])

    daily = df.groupby("date", as_index=False).sum(numeric_only=True)
    daily["total"] = daily["basal"] + daily["diverses"] + daily["bolus"]

    return daily


    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["date", "basal", "diverses", "bolus", "total"])
    
    # Summen pro Tag berechnen
    daily = df.groupby("date").sum()
    daily["total"] = daily["basal"] + daily["diverses"] + daily["bolus"]
    daily = daily.reset_index()
    return daily

def write_html(df):
    """Schöne HTML-Tabelle mit Zebra-Style erzeugen"""
    
    # HTML-Tabelle erzeugen (nur Inhalt)
    table_html = df.to_html(
        index=False,
        float_format="{:.2f}".format,
        classes="tdd-table"
    )

    # Gesamtseite + CSS drumherum
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>TDD Übersicht</title>

<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
}}

h2 {{
    font-size: 24px;
    margin-bottom: 20px;
}}

table.tdd-table {{
    border-collapse: collapse;
    width: 100%;
    max-width: 800px;
}}

.tdd-table th {{
    background-color: #444;
    color: white;
    padding: 10px;
    font-size: 14px;
    text-align: left;
}}

.tdd-table td {{
    padding: 8px;
    border: 1px solid #ddd;
}}

.tdd-table tr:nth-child(even) {{
    background-color: #f2f2f2;
}}

.tdd-table tr:hover {{
    background-color: #e6e6e6;
}}
</style>

</head>
<body>

<h2>Tägliche TDD Übersicht</h2>
{table_html}

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html schön erstellt 😎")


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
