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
    from datetime import datetime, timedelta
    import pandas as pd

    # ---------- 1️⃣ Bolus sammeln ----------
    records = []

    for d in data:
        dt = datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")
        ).date()

        bolus = float(d.get("insulin", 0) or 0)

        records.append({
            "date": dt,
            "bolus": bolus,
            "diverses": 0.0,
            "basal": 0.0
        })

    df = pd.DataFrame(records)

    # ---------- 2️⃣ Basal aus Temp Basal berechnen ----------
    temp = [e for e in data if e.get("eventType") == "Temp Basal"]

    if temp:
        temp.sort(key=lambda x: x["created_at"])
        basal_rows = []

        for i in range(len(temp)):
            current = temp[i]

            start = datetime.fromisoformat(
                current["created_at"].replace("Z", "+00:00")
            )
            rate = float(current.get("rate", 0) or 0)   # U/h

            # Ende = nächstes Temp Basal oder Tagesende
            if i + 1 < len(temp):
                end = datetime.fromisoformat(
                    temp[i+1]["created_at"].replace("Z", "+00:00")
                )
            else:
                end = start.replace(hour=23, minute=59, second=59)

            if end <= start:
                continue

            # Über mehrere Tage splitten
            d = start
            remaining = end

            while d.date() < remaining.date():
                day_end = datetime.combine(d.date(), datetime.max.time())
                dh = (day_end - d).total_seconds() / 3600.0
                basal_rows.append({"date": d.date(),
                                   "basal": rate * dh})
                d = day_end + timedelta(seconds=1)

            # Rest bis Endzeit
            dh = (remaining - d).total_seconds() / 3600.0
            if dh > 0:
                basal_rows.append({"date": d.date(),
                                   "basal": rate * dh})

        basal_df = pd.DataFrame(basal_rows)

        if not basal_df.empty:
            basal_daily = basal_df.groupby("date", as_index=False)["basal"].sum()
            df = df.groupby("date", as_index=False).sum(numeric_only=True)
            df = df.merge(basal_daily, on="date", how="outer").fillna(0)

    # ---------- 3️⃣ Gesamtsumme ----------
    if df.empty:
        return pd.DataFrame(columns=["date", "basal", "diverses", "bolus", "total"])

    df["total"] = df["basal"] + df["diverses"] + df["bolus"]

    return df.sort_values("date")


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
