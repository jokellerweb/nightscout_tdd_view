import json
import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

def round_u(v):
    return round(v, 2)

def main():
    NS_URL = os.environ.get("NS_URL")
    NS_SECRET = os.environ.get("NS_SECRET")
    r = requests.get(f"{NS_URL}/api/v1/treatments.json?count=10000&api_secret={NS_SECRET}")
    data = r.json()
    data = load_data("data.json")

    days = defaultdict(lambda: {"basal": 0.0, "bolus": 0.0, "smb": 0.0})

    for t in data:
        if "timestamp" not in t:
            continue

        day = datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00")).date()

        et = t.get("eventType", "")

        # ---------- BOLUS ----------
        if "Bolus" in et:
            insulin = float(t.get("insulin", 0) or 0)
            if insulin > 0:
                # SMB?
                if "SMB" in et or "Microbolus" in et:
                    days[day]["smb"] += insulin
                else:
                    days[day]["bolus"] += insulin

        # ---------- BASAL ----------
        if et == "Temp Basal":
            rate = float(t.get("rate", 0) or 0)          # U/hr
            duration = float(t.get("duration", 0) or 0)  # minutes

            if rate > 0 and duration > 0:
                units = rate * (duration / 60.0)
                days[day]["basal"] += units

    # ---------- AUSGABE ----------
    sorted_days = sorted(days.keys(), reverse=True)

    print("\nTägliche TDD")
    print("Datum        | Basal  | Bolus | SMB | Gesamt")
    print("----------------------------------------------")

    tdd_values = []

    for d in sorted_days:
        basal = round_u(days[d]["basal"])
        bolus = round_u(days[d]["bolus"])
        smb = round_u(days[d]["smb"])
        total = round_u(basal + bolus + smb)

        tdd_values.append((d, total))

        print(f"{d} | {basal:5} | {bolus:5} | {smb:4} | {total:6}")

    # ---------- DURCHSCHNITTE ----------
    if not tdd_values:
        return

    # gesamt Ø
    avg_all = sum(v for _, v in tdd_values) / len(tdd_values)

    # letzte 7 Tage
    today = sorted_days[0]
    last7 = [v for d, v in tdd_values if d >= today - timedelta(days=6)]
    avg7 = sum(last7) / len(last7) if last7 else 0

    print("\nDurchschnitt:")
    print(f"Alle Tage: {avg_all:.2f} U")
    print(f"Letzte 7 Tage: {avg7:.2f} U")


if __name__ == "__main__":
    main()

