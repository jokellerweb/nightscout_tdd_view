import requests
import pandas as pd
from datetime import datetime, timedelta

# === CONFIG ===
NIGHTSCOUT_URL = "https://dein-nightscout-url.herokuapp.com/api/v1"  # <--- anpassen

# === HELPER ===
def fetch_entries(entry_type="entries"):
    url = f"{NIGHTSCOUT_URL}/{entry_type}.json"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def fetch_treatments():
    return fetch_entries("treatments")

def parse_date(datestr):
    return datetime.fromisoformat(datestr.replace("Z", "+00:00")).date()

# === DATEN SAMMELN ===
treatments = fetch_treatments()

data = []
for t in treatments:
    dt = parse_date(t['created_at'])
    bolus = t.get('bolus', 0) if 'bolus' in t else t.get('insulin', 0)
    basal = t.get('rate', 0) if t.get('eventType') == 'Temp Basal' else 0
    smb = t.get('insulin', 0) if t.get('eventType') == 'Bolus Wizard' else 0

    data.append({"date": dt, "bolus": bolus, "basal": basal, "smb": smb})

df = pd.DataFrame(data)
if df.empty:
    print("Keine Daten gefunden.")
    exit()

# Gruppieren nach Datum
daily = df.groupby("date").sum()
daily['total'] = daily['bolus'] + daily['basal'] + daily['smb']
daily = daily.sort_index(ascending=False)

# Durchschnittsberechnung
avg_all = daily['total'].mean()
avg_2 = daily['total'].head(2).mean()
avg_3 = daily['total'].head(3).mean()
avg_4 = daily['total'].head(4).mean()
avg_7 = daily['total'].head(7).mean()

# === TABLE PRINT ===
def print_table(df):
    print("\nTägliche TDD Übersicht (letzte 7 Tage)\n")
    print(f"{'Datum':<12}{'Bolus (U)':<12}{'Basal (U)':<12}{'SMB (U)':<12}{'Gesamt (U)':<12}")
    for i, (idx, row) in enumerate(df.head(7).iterrows()):
        shade = "\033[47m" if i % 2 else ""  # leichte Grauschattierung für jede 2. Zeile
        endshade = "\033[0m" if shade else ""
        print(f"{shade}{idx}  {row['bolus']:<12.2f}{row['basal']:<12.2f}{row['smb']:<12.2f}{row['total']:<12.2f}{endshade}")

print_table(daily)

print("\nDurchschnittliche TDD:")
print(f"Alle Daten: {avg_all:.2f} U")
print(f"Letzte 2 Tage: {avg_2:.2f} U")
print(f"Letzte 3 Tage: {avg_3:.2f} U")
print(f"Letzte 4 Tage: {avg_4:.2f} U")
print(f"Letzte 7 Tage: {avg_7:.2f} U")
