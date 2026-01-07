import os
import requests
import pandas as pd
from datetime import datetime

def fetch_data(endpoint, token):
    url = f"{endpoint}?count=1000&token={token}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def main():
    # Nightscout Secrets aus der Umgebung
    NS_URL = os.environ.get("NS_URL")
    NS_SECRET = os.environ.get("NS_SECRET")

    if not NS_URL or not NS_SECRET:
        raise ValueError("Bitte NS_URL und NS_SECRET als Umgebungsvariablen setzen!")

    # Endpunkte
    endpoints = {
        "basal": f"{NS_URL}/api/v1/basal.json",
        "bolus": f"{NS_URL}/api/v1/bolus.json",
        "smb":   f"{NS_URL}/api/v1/smb.json"
    }

    # Daten holen
    basal_data = fetch_data(endpoints["basal"], NS_SECRET)
    bolus_data = fetch_data(endpoints["bolus"], NS_SECRET)
    smb_data   = fetch_data(endpoints["smb"], NS_SECRET)

    # DataFrames erstellen
    df_basal = pd.DataFrame(basal_data)[["created_at", "amount"]].rename(columns={"amount": "basal"})
    df_bolus = pd.DataFrame(bolus_data)[["created_at", "amount"]].rename(columns={"amount": "bolus"})
    df_smb   = pd.DataFrame(smb_data)[["created_at", "amount"]].rename(columns={"amount": "smb"})

    # Alle Daten zusammenführen
    df = pd.concat([df_basal, df_bolus, df_smb], ignore_index=True)
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    df.fillna(0, inplace=True)
    df["total"] = df["basal"] + df["bolus"] + df["smb"]

    # Summen pro Tag berechnen, Datum rausnehmen
    daily = df.groupby("date").sum().reset_index()
    daily = daily[["basal", "smb", "bolus", "total"]]

    # HTML-Tabelle erstellen
    html_table = daily.to_html(index=False, float_format="{:.2f}".format)

    # In index.html schreiben
    with open("index.html", "w") as f:
        f.write(f"<h2>Tägliche TDD Übersicht</h2>\n{html_table}")

    print("index.html erfolgreich erstellt!")

if __name__ == "__main__":
    main()
