import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import pytz

NS_INTERVAL_MIN = 5  # Nightscout rechnet intern in 5-Minuten-Slots

# --------------------------------------------------
# API Fetcher
# --------------------------------------------------
def fetch_json(url, secret):
    headers = {"api-secret": secret}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

# --------------------------------------------------
# Profile laden
# --------------------------------------------------
def load_profiles(ns_url, secret):
    data = fetch_json(f"{ns_url}/api/v1/profile.json", secret)
    return data

# --------------------------------------------------
# Treatments laden
# --------------------------------------------------
def load_treatments(ns_url, secret, days=7):
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    url = f"{ns_url}/api/v1/treatments.json?find[created_at][$gte]={since}&count=10000"
    return fetch_json(url, secret)

# --------------------------------------------------
# Aktives Profil zum Zeitpunkt bestimmen
# --------------------------------------------------
def active_profile_at(profiles, ts):
    valid = [
        p for p in profiles
        if datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) <= ts
    ]
    return sorted(valid, key=lambda x: x["created_at"])[-1]

# --------------------------------------------------
# Basalrate aus Profil für Uhrzeit holen
# --------------------------------------------------
def basal_from_profile(profile, local_time):
    schedule = profile["store"][profile["defaultProfile"]]["basal"]
    minutes = local_time.hour * 60 + local_time.minute

    current = schedule[0]
    for entry in schedule:
        if minutes >= int(entry["time"]):
            current = entry
        else:
            break
    return float(current["value"])

# --------------------------------------------------
# Temp Basal prüfen
# --------------------------------------------------
def temp_basal_at(treatments, ts):
    for t in treatments:
        if t.get("eventType") == "Temp Basal" and t.get("rate") is not None:
            start = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            duration = t.get("duration", 0) * 60
            end = start + timedelta(seconds=duration)
            if start <= ts < end:
                return float(t["rate"])
    return None

# --------------------------------------------------
# Basal vollständig berechnen
# --------------------------------------------------
def calculate_basal(ns_url, secret, days=7):
    profiles = load_profiles(ns_url, secret)
    treatments = load_treatments(ns_url, secret, days)

    tz = pytz.timezone(profiles[-1]["timezone"])
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    rows = []

    t = start
    while t < now:
        profile = active_profile_at(profiles, t)
        local = t.astimezone(tz)

        rate = temp_basal_at(treatments, t)
        if rate is None:
            rate = basal_from_profile(profile, local)

        basal = rate * (NS_INTERVAL_MIN / 60)

        rows.append({
            "date": local.date(),
            "basal": basal
        })

        t += timedelta(minutes=NS_INTERVAL_MIN)

    df = pd.DataFrame(rows)
    return df.groupby("date", as_index=False).sum()

# --------------------------------------------------
# Bolus / SMB
# --------------------------------------------------
def calculate_bolus(treatments):
    rows = []
    for t in treatments:
        if t.get("insulin"):
            dt = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).date()
            rows.append({"date": dt, "bolus": float(t["insulin"])})
    return pd.DataFrame(rows).groupby("date", as_index=False).sum()

# --------------------------------------------------
# HTML (unverändert)
# --------------------------------------------------
def write_html(df):
    table_html = df.to_html(index=False, float_format="{:.2f}".format, classes="tdd-table")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>TDD Übersicht</title>
<style>
body {{ font-family: Arial; margin: 40px; }}
table {{ border-collapse: collapse; width: 100%; max-width: 800px; }}
th {{ background: #444; color: #fff; padding: 10px; }}
td {{ padding: 8px; border: 1px solid #ddd; }}
tr:nth-child(even) {{ background: #f2f2f2; }}
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
    ns_url = os.environ["NS_URL"]
    ns_secret = os.environ["NS_SECRET"]

    treatments = load_treatments(ns_url, ns_secret)
    basal = calculate_basal(ns_url, ns_secret)
    bolus = calculate_bolus(treatments)

    df = pd.merge(basal, bolus, on="date", how="left").fillna(0)
    df["diverses"] = 0.0
    df["total"] = df["basal"] + df["bolus"]

    write_html(df)

if __name__ == "__main__":
    main()
