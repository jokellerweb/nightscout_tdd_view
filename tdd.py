import os
import requests
import pandas as pd
from datetime import datetime

# 🔹 Secrets aus Environment Variables
NS_URL = os.getenv("NS_URL")
NS_SECRET = os.getenv("NS_SECRET")

if not NS_URL or not NS_SECRET:
    raise ValueError("NS_URL oder NS_SECRET nicht gesetzt!")

# 🔹 Endpoints für Bolus, Basal, SMB
endpoints = {
    "bolus": f"{NS_URL}/api/v1/entries.json?count=1000&find[device]=Pump&token={NS_SECRET}",
    "basal": f"{NS_URL}/api/v1/basal.json?count=1000&token={NS_SECRET}",
    "smb":   f"{NS_URL}/api/v1/smb.json?count=1000&token={NS_SECRET}",
}

# 🔹 Funktion zum Abrufen der Daten
def fetch_data(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

# 🔹 Daten abrufen
bolus_data = fetch_data(endpoints["bolus"])
basal_data = fetch_data(endpoints["basal"])
smb_data   = fetch_data(endpoints["smb"])

# 🔹 Funktion zum Umwandeln in DataFrame
def to_df(data, value_field="amount", time_field="date"):
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])
    # Unix timestamp oder ISO string
    if time_field in df.columns:
        df["date"] = pd.to_datetime(df[time_field], unit='ms', errors='coerce', utc=True)
    else:
        df["date"] = pd.to_datetime(df["created_at"], errors='coerce', utc=True)
    df["value"] = pd.to_numeric(df[value_field], errors='coerce')
    df = df.dropna(subset=["date", "value"])
    df["day"] = df["date"].dt.date
    return df[["day", "value"]]

# 🔹 DataFrames erstellen
df_bolus = to_df(bolus_data, value_field="amount", time_field="created_at")
df_basal = to_df(basal_data, value_field="amount", time_field="created_at")
df_smb   = to_df(smb_data, value_field="amount", time_field="created_at")

# 🔹 Summen pro Tag berechnen
daily = pd.DataFrame()
daily["bolus"] = df_bolus.groupby("day")["value"].sum()
daily["basal"] = df_basal.groupby("day")["value"].sum()
daily["smb"]   = df_smb.groupby("day")["value"].sum()
daily = daily.fillna(0)
daily["total"] = daily.sum(axis=1)

# 🔹 HTML erstellen
html_table = daily.to_html(classes="tdd-table", float_format="%.2f")
with open("index.html", "w", encoding="utf-8") as f:
    f.write("<html><head><style>")
    f.write(".tdd-table { border-collapse: collapse; width: 100%; }")
    f.write(".tdd-table th, .tdd-table td { border: 1px solid #ccc; padding: 5px; text-align: center; }")
    f.write("</style></head><body>")
    f.write("<h2>TDD Übersicht</h2>")
    f.write(html_table)
    f.write("</body></html>")

print("✅ TDD HTML erfolgreich erstellt: index.html")
