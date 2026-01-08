import os
import requests
import pandas as pd
from datetime import datetime, timedelta, time, timezone


# --------------------------------------------------
# Nightscout API
# --------------------------------------------------
def fetch_data(ns_url, ns_secret):
    url = f"{ns_url}/api/v1/treatments.json?count=2000&token={ns_secret}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------
# Datenverarbeitung
# --------------------------------------------------
def process_data(data):
    """
    Nightscout-konforme Berechnung:
    - Temp Basal + Profile Basal
    - Dauer = Zeit bis nächstes Basal-Event
    - korrekt über Tagesgrenzen
    """

    basal_rows = []
    insulin_rows = []

    # ------------------------------
    # BASAL EVENTS (Temp + Profile)
    # ------------------------------
    basal_events = [
        d for d in data
        if d.get("eventType") in ("Temp Basal", "Profile Switch")
        and d.get("rate") is not None
    ]

    # Nightscout liefert NEU → ALT → wir brauchen ALT → NEU
    basal_events.sort(key=lambda x: x["created_at"])

    for i, event in enumerate(basal_events):
        start = datetime.fromisoformat(
            event["created_at"].replace("Z", "+00:00")
        )
        rate = float(event["rate"])

        # Ende = nächstes Basal-Event oder Tagesende
        if i + 1 < len(basal_events):
            end = datetime.fromisoformat(
                basal_events[i + 1]["created_at"].replace("Z", "+00:00")
            )
        else:
            end = start.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        current = start

        # über Tagesgrenzen splitten
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

            # DEBUG
            print(
                f"Start: {current}, End: {period_end}, "
                f"Rate: {rate}, Hours: {hours:.5f}, Basal: {basal_amount:.5f}"
            )

            current = period_end + timedelta(seconds=1)

    # ------------------------------
    # BOLUS / SMB
    # ------------------------------
    for d in data:
        dt = datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")
        ).date()

        bolus = float(d["insulin"]) if d.get("insulin") else 0.0

        insulin_rows.append({
            "date": dt,
            "bolus": bolus,
            "diverses": 0.0
        })

    # ------------------------------
    # DATAFRAMES
    # ------------------------------
    df_basal = pd.DataFrame(basal_rows)
    df_insulin = pd.DataFrame(insulin_rows)

    if df_basal.empty:
        df_basal = pd.DataFrame(columns=["date", "basal"])
    if df_insulin.empty:
        df_insulin = pd.DataFrame(columns=["date", "bolus", "diverses"])

    daily_basal = df_basal.groupby("date", as_index=False).sum(numeric_only=True)
    daily_insulin = df_insulin.groupby("date", as_index=False).sum(numeric_only=True)

    daily = pd.merge(
        daily_basal,
        daily_insulin,
        on="date",
        how="outer"
    ).fillna(0)

    daily["total"] = (
        daily["basal"] + daily["bolus"] + daily["diverses"]
    )

    # kein "Morgen"
    today = datetime.now(timezone.utc).date()
    daily = daily[daily["date"] <= today]

    return daily


# --------------------------------------------------
# HTML OUTPUT (unverändert)
# --------------------------------------------------
def write_html(df):
    table_html = df.to_html(
        index=False,
        float_format="{:.2f}".format,
        classes="tdd-table"
    )

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


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    ns_url = os.environ.get("NS_URL")
    ns_secret = os.environ.get("NS_SECRET")

    if not ns_url or not ns_secret:
        raise ValueError("NS_URL oder NS_SECRET fehlt!")

    data = fetch_data(ns_url, ns_secret)
    daily = process_data(data)
    write_html(daily)


if __name__ == "__main__":
    main()
