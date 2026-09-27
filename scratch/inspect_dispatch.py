import urllib.request
import json
import pandas as pd

def inspect_dispatch():
    for d_state in ["NORMAL", "LIMITED", "CRITICAL"]:
        url = f"http://127.0.0.1:8000/api/schedule?horizon=24&season=live&battery_state=NORMAL&diesel_state={d_state}"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            df = pd.DataFrame(data["schedule"])
            print(f"\n================ DIESEL {d_state} ================")
            print(f"Total demand: {df['predicted_demand_kw'].sum():.1f} kWh")
            print(f"Total solar:  {df['solar_generation_kw'].sum():.1f} kWh")
            print(f"Total wind:   {df['wind_generation_kw'].sum():.1f} kWh")
            print(f"Total ren used: {df['renewable_used_kw'].sum():.1f} kWh")
            print(f"Total dsl gen:  {df['diesel_generation_kw'].sum():.1f} kWh")
            print(f"Total bat chg:  {df['battery_charge_kw'].sum():.1f} kWh")
            print(f"Total bat dis:  {df['battery_discharge_kw'].sum():.1f} kWh")
            print(f"Total unmet:    {df['unmet_demand_kw'].sum():.1f} kWh")
            print("First 6 hours dispatch:")
            cols = ["predicted_demand_kw", "solar_generation_kw", "wind_generation_kw", "battery_discharge_kw", "battery_charge_kw", "diesel_generation_kw", "battery_soc_percent", "unmet_demand_kw"]
            print(df[cols].head(6).to_string())

if __name__ == "__main__":
    inspect_dispatch()
