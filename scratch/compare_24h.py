import urllib.request
import json

def print_24h(state):
    url = f"http://127.0.0.1:8000/api/schedule?horizon=24&season=live&battery_state=NORMAL&diesel_state={state}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode())
    print(f"\n=================== DIESEL {state} ===================")
    for i, r in enumerate(data['schedule']):
        print(f"H{i:02d}: Demand={r['predicted_demand_kw']:6.1f} | Solar={r['solar_generation_kw']:5.1f} | Wind={r['wind_generation_kw']:4.1f} | Dsl={r['diesel_generation_kw']:5.1f} | BatDis={r['battery_discharge_kw']:5.1f} | BatChg={r['battery_charge_kw']:5.1f} | SoC={r['battery_soc_percent']:4.1f}% | Unmet={r['unmet_demand_kw']:4.1f}")

if __name__ == "__main__":
    print_24h("NORMAL")
    print_24h("LIMITED")
