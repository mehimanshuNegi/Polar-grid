import urllib.request
import json

def test():
    cases = [
        ("NORMAL", "NORMAL"),
        ("NORMAL", "LIMITED"),
        ("NORMAL", "CRITICAL"),
        ("LOW", "NORMAL"),
        ("LOW", "LIMITED"),
        ("LOW", "CRITICAL"),
        ("CRITICAL", "NORMAL"),
        ("CRITICAL", "LIMITED"),
        ("CRITICAL", "CRITICAL"),
    ]
    for b, d in cases:
        url = f"http://127.0.0.1:8000/api/schedule?horizon=24&season=live&battery_state={b}&diesel_state={d}"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            s = data["summary"]
            rec0 = data["schedule"][0]
            num_alerts = len(s.get('alerts', []))
            print(f"B={b:8} | D={d:8} -> init_soc={s.get('initial_soc')} | dsl_cap={s.get('diesel_capacity_kw')}kW | alerts_count={num_alerts} | H0_bat_soc={rec0.get('battery_soc_percent')}% | H0_dsl_kw={rec0.get('diesel_generation_kw')}kW | total_dsl_kwh={s.get('diesel_energy_used_kwh')} | opt_dsl_L={s.get('optimized_diesel_litres')}")

if __name__ == "__main__":
    test()
