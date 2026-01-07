#!/usr/bin/env python3

import os
import requests
import pandas as pd
from datetime import datetime

# --- Umgebungsvariablen lesen ---
NS_URL = os.getenv("NS_URL")
NS_SECRET = os.getenv("NS_SECRET")

if not NS_URL or not NS_SECRET:
    raise ValueError("NS_URL oder NS_SECRET ist nicht gesetzt!")

# --- Treatments abrufen ---
def fetch_treatments(count=10000):
    url = f"{NS_URL}/api/v1/treatments.json?count={count}&api_secret={NS_SECRET}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

# --- Datum extrahieren ---
def parse_date(ts):
    # nimmt created_at als Zeitpunkt
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()

def main():
    data = fetch_treatments()

    # Rohdatenliste
    rows = []

    for t in data:
        d = parse_date(t["created_at"])
        et = t.get("eventType", "")
        insulin = float(t.get("insulin", 0) or 0)

        basal_units = 0.0
        smb_units = 0.0
        bolus_units = 0.0

        # Temp Basal
        if et == "Temp Basal":
            rate = float(t.get("rate", 0) or 0)          # U/h
            duration = float(t.get("duration", 0) or 0)  # Minuten
            if rate > 0 and duration > 0:
                basal_units = rate * (duration / 60)

        # SMB / Microbolus
        elif "SMB" in et or "Microbolus" in et:
            smb_units = insulin

        # Bolus‑Arten (inkl. Correction/Meal/Extended)
        elif et in ["Bolus", "Correction Bolus", "Meal Bolus", "Extended Bolus"]:
            bolus_units = insulin

        # Eintrag speichern
        rows.append({
            "date": d,
            "basal": basal_units,
            "smb": smb_units,
            "bolus": bolus_units,
            "total": basal_units + smb_units + bolus_units
        })

    # DataFrame
    df = pd.DataFrame(rows)

    # Summen pro Tag berechnen
    daily = df.groupby("date")[["basal", "smb", "bolus", "total"]].sum().reset_index()

    # HTML‑Tabelle (Datum raus)
    html_table = daily[["basal", "smb", "bolus", "total"]].to_html(
        index=False,
        float_format="{:.2f}".format,
        classes="tdd-table"
    )

    # HTML‑Seite schreiben
    with open("index.html", "w", encoding="utf-8") as f:
        f.write("""
        <html><head><meta charset="utf-8">
        <style>
          table.tdd-table {border-collapse: collapse; width: 100%;}
          table.tdd-table th, table.tdd-table td {border: 1px solid #888; padding: 6px; text-align: center;}
          table.tdd-table th {background:#444; color:#fff; font-weight:bold;}
          table.tdd-table tr:nth-child(even) {background:#f2f2f2;}
        </style>
        </head><body>
        <h2>Tägliche TDD Übersicht</h2>
        """ + html_table + "</body></html>")

    print("✅ index.html erfolgreich erstellt!")

if __name__ == "__main__":
    main()
