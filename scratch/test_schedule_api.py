import urllib.request
import json

def test():
    for h in [24, 48, 72]:
        url = f"http://127.0.0.1:8000/api/schedule?horizon={h}&season=live"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            s = data["summary"]
            print(f"=== HORIZON {h} HOURS ===")
            print("Summary keys:", list(s.keys()))
            print(f"  baseline_diesel_fuel_litres: {s.get('baseline_diesel_fuel_litres')}")
            print(f"  optimized_diesel_fuel_litres: {s.get('optimized_diesel_fuel_litres')}")
            print(f"  diesel_fuel_saved_litres: {s.get('diesel_fuel_saved_litres')}")
            print(f"  diesel_reduction_percent: {s.get('diesel_reduction_percent')}")
            print(f"  renewable_penetration_percent: {s.get('renewable_penetration_percent')}")
            print(f"  baseline_diesel_litres: {s.get('baseline_diesel_litres')}")
            print(f"  Separate Annual Benchmark: {s.get('annual_validated_reduction_percent')}% ({s.get('annual_validated_note')})")

    # Also test simulated equipment re-dispatch
    for b_state in ["NORMAL", "LOW", "CRITICAL"]:
        url = f"http://127.0.0.1:8000/api/schedule?horizon=24&season=live&battery_state={b_state}"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            s = data["summary"]
            print(f"=== BATTERY {b_state} (24H) ===")
            print(f"  Opt: {s.get('optimized_diesel_litres')} L | Avoided: {s.get('diesel_saved_litres')} L | Red: {s.get('diesel_reduction_percent')}%")

if __name__ == "__main__":
    test()
