#!/usr/bin/env python3
# tdd.py

import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- Secrets aus der Umgebung lesen ---
NS_URL = os.environ.get("NS_URL")
NS_SECRET = os.environ.get("NS_SECRET")

if not NS_URL or not NS_SECRET:
    raise ValueError("NS_URL oder NS_SECRET nicht gesetzt!")

# --- Treatments vom Nightscout API abrufen ---
def fetch_treatments(count=10000):
    url = f"{NS_URL}/api/v1/treatments.json?count={count}&token={NS_SECRET}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

# --- Hilfsfunktion: Datum aus Timestamp ---
def date_from_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()

# --- Hauptfunktion ---
def main():
    treatments = fetch_treatments()

    # Listen für DataFrame
    rows = []

    for t in treatments:
        d = date_from_ts(t["created_at"])
        event = t.get("eventType", "")
        insulin = t.get("insulin", 0)

        basal_units = 0
        smb_units = 0
        bolus_units = 0

        # Basaltemp berechnen, falls vorhanden
        if event == "Temp Basal":
            rate = t.get("rate", 0)        # U/h
            duration = t.get("duration", 0) # min
            basal_units = rate * (duration / 60)
        
        # SMB
        elif event in ["SMB", "Microbolus"]:
            smb_units = insulin
        
        # Bolus
        elif event in ["Meal Bolus", "Correction Bolus", "Bolus", "Extended Bolus"]:
            bolus_units = insulin

        # Gesamtinsulin pro Eintrag
        total_units = basal_units + smb_units + bolus_units

        rows.append({
            "date": d,
            "basal": basal_units,
            "smb": smb_units,
            "bolus": bolus_units,
            "total": total_units
        })

    # DataFrame erstellen
    df = pd.DataFrame(rows)

    # Summen pro Tag berechnen
    daily = df.groupby("date").sum().reset_index()

    # HTML-Tabelle erstellen
    html_table = daily.to_html(index=False, float_format="{:.2f}".format)

    # In index.html schreiben
    with open("index.html", "w") as f:
        f.write(f"<h2>Tägliche TDD Übersicht</h2>\n{html_table}")

    print("index.html erfolgreich erstellt!")

if __name__ == "__main__":
    main()
