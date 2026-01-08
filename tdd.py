import os
import requests
from datetime import datetime, timedelta, time, timezone
import pandas as pd

def fetch_data(ns_url, ns_secret):
    """Alle Insulin-Daten aus treatments.json holen"""
    url = f"{ns_url}/api/v1/treatments.json?count=1000&token={ns_secret}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

from datetime import datetime, timedelta, time, timezone
import pandas as pd

def process_data(data):
    """
    Daten aus Nightscout verarbeiten:
    - Basal korrekt aus Temp Basal Events berechnen (Nightscout-Logik)
    - Bolus summieren
    - Tagesweise aggregieren
    """

    basal_rows = []
    insulin_rows = []

    # --------------------------------------------------
    # 1️⃣ TEMP BASAL EVENTS
    # Nightscout liefert NEUSTE zuerst → wir brauchen ALT → NEU
    # --------------------------------------------------
    temp_basal_events = [
        d for d in data
        if d.get("eventType") == "Temp Basal" and d.get("rate") is not None
    ]

    temp_basal_events.sort(key=lambda x: x["created_at"])  # ALT → NEU  ### FIX

    for i, d in enumerate(temp_basal_events):
        start = datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")
        )
        rate = float(d["rate"])

        # Ende = nächstes Temp Basal ODER Tagesende  ### FIX
        if i + 1 < len(temp_basal_events):
            end = datetime.fromisoformat(
                temp_basal_events[i + 1]["created_at"].replace("Z", "+00:00")
            )
        else:
            end = start.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        current = start

        # --------------------------------------------------
        # 2️⃣ Zeitraum sauber über Tagesgrenzen splitten
        # --------------------------------------------------
        while current < end:
            day_end = current.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            period_end = min(day_end, end)

            hours = (period_end - current).total_seconds() / 3600.0
            basal_amount = rate * hours

            if basal_amount > 0:
                basal_rows.append({
                    "date": current.date(),
                    "basal": basal_amount
                })

            # DEBUG (kannst du später löschen)
            print(
                f"Start: {current}, End: {period_end}, "
                f"Rate: {rate}, Hours: {hours:.5f}, Basal: {basal_amount:.5f}"
            )

            current = period_end + timedelta(seconds=1)

    # --------------------------------------------------
    # 3️⃣ BOLUS / INSULIN
    # --------------------------------------------------
    for d in data:
        dt = datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")
        ).date()

        bolus = float(d["insulin"]) if d.get("insulin") else 0.0
        diverses = 0.0

        insulin_rows.append({
            "date": dt,
            "bolus": bolus,
            "diverses": diverses
        })

    # --------------------------------------------------
    # 4️⃣ DATAFRAMES
    # --------------------------------------------------
    df_basal = pd.DataFrame(basal_rows)
    df_insulin = pd.DataFrame(insulin_rows)

    if df_basal.empty:
        df_basal = pd.DataFrame(columns=["date", "basal"])
    if df_insulin.empty:
        df_insulin = pd.DataFrame(columns=["date", "bolus", "diverses"])

    daily_basal = df_basal.groupby("date", as_index=False).sum(numeric_only=True)
    daily_insulin = df_insulin.groupby("date", as_index=False).sum(numeric_only=True)

    daily = pd.merge(
        daily_basal, daily_insulin,
        on="date", how="outer"
    ).fillna(0)

    daily["total"] = (
        daily["basal"] + daily["bolus"] + daily["diverses"]
    )

    # --------------------------------------------------
    # 5️⃣ „MORGEN“-ZEILE VERMEIDEN
    # --------------------------------------------------
    today = datetime.now(timezone.utc).date()
    daily = daily[daily["date"] < today]

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
