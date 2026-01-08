import os
import requests
import pandas as pd
from datetime import datetime, timezone

# --------------------------------------------------
# FETCH DATA
# --------------------------------------------------
def fetch_data(ns_url, ns_secret):
    url = f"{ns_url}/api/v1/treatments.json?count=1000&token={ns_secret}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# --------------------------------------------------
# PROCESS DATA (Nightscout TDD Logic)
# --------------------------------------------------
def process_data(data):
    rows = []

    for d in data:
        if d.get("insulin") is None:
            continue  # Nightscout zählt nur echtes Insulin

        ts = datetime.fromisoformat(
            d["created_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)

        event = d.get("eventType", "")
        insulin = float(d["insulin"])

        bolus = 0.0
        basal = 0.0
        diverses = 0.0

        if event in ("Correction Bolus", "Meal Bolus"):
            bolus = insulin
        elif event == "SMB":
            bolus = insulin
        else:
            # alles andere mit insulin zählt Nightscout als Basal
            basal = insulin

        rows.append({
            "date": ts.date(),
            "basal": basal,
            "bolus": bolus,
            "diverses": diverses
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "basal", "bolus", "diverses", "total"])

    daily = df.groupby("date", as_index=False).sum(numeric_only=True)
    daily["total"] = daily["basal"] + daily["bolus"] + daily["diverses"]

    # nur letzte 7 Tage
    today = datetime.now(timezone.utc).date()
    daily = daily[daily["date"] >= today - pd.Timedelta(days=6)]

    return daily.sort_values("date")

# --------------------------------------------------
# HTML OUTPUT (BLEIBT WIE BEI DIR)
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
    text-align: left;
}}
.tdd-table td {{
    padding: 8px;
    border: 1px solid #ddd;
}}
.tdd-table tr:nth-child(even) {{
    background-color: #f2f2f2;
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

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    ns_url = os.getenv("NS_URL")
    ns_secret = os.getenv("NS_SECRET")

    if not ns_url or not ns_secret:
        raise RuntimeError("NS_URL oder NS_SECRET fehlt")

    data = fetch_data(ns_url, ns_secret)
    daily = process_data(data)
    write_html(daily)

if __name__ == "__main__":
    main()
