import os
import requests
import pandas as pd

def fetch_data(endpoint):
    """Daten von Nightscout holen."""
    NS_URL = os.environ.get("NS_URL")
    NS_SECRET = os.environ.get("NS_SECRET")

    url = f"{NS_URL}/api/v1/{endpoint}.json?count=1000&token={NS_SECRET}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def main():
    # Endpunkte für Insulindaten
    endpoints = {
        "basal": "basal",   # Basalrate
        "smb": "smb",       # SMB (Smartbolus)
        "bolus": "bolus"    # Bolus
    }

    # Alle Daten abrufen
    all_data = []
    for key, endpoint in endpoints.items():
        data = fetch_data(endpoint)
        for entry in data:
            all_data.append({
                "created_at": entry.get("created_at"),
                "type": key,
                "value": entry.get("value", 0)
            })

    # In DataFrame umwandeln
    df = pd.DataFrame(all_data)

    # Spalten für Berechnung vorbereiten
    df["basal"] = df.apply(lambda x: x["value"] if x["type"]=="basal" else 0, axis=1)
    df["smb"] = df.apply(lambda x: x["value"] if x["type"]=="smb" else 0, axis=1)
    df["bolus"] = df.apply(lambda x: x["value"] if x["type"]=="bolus" else 0, axis=1)
    df["total"] = df["basal"] + df["smb"] + df["bolus"]

    # Datumsspalte erstellen
    df["date"] = pd.to_datetime(df["created_at"]).dt.date

    # Summen pro Tag berechnen
    daily = df.groupby("date")[["basal", "smb", "bolus", "total"]].sum().reset_index()

    # HTML-Tabelle erstellen
    html_table = daily.to_html(index=False, float_format="{:.2f}".format)

    # In index.html schreiben
    with open("index.html", "w") as f:
        f.write(f"<h2>Tägliche TDD Übersicht</h2>\n{html_table}")

    print("index.html erfolgreich erstellt!")

if __name__ == "__main__":
    main()
