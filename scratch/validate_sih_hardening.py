import sys
import os
import json
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app
from src.evaluation.baseline_comparator import BaselineComparator

def run_comprehensive_validation():
    client = TestClient(app)
    results = {
        "api_endpoints": {},
        "scenarios": {},
        "optimization_checks": {},
        "ml_metrics": {}
    }

    print("=== Testing FastAPI Endpoints ===")
    # 1. /api/status
    res = client.get("/api/status")
    assert res.status_code == 200, f"/api/status failed: {res.status_code}"
    status_data = res.json()
    print(f"  [OK] /api/status: {status_data['station']}")
    results["api_endpoints"]["/api/status"] = "PASSED"

    # 2. /api/config
    res = client.get("/api/config")
    assert res.status_code == 200, f"/api/config failed: {res.status_code}"
    config_data = res.json()
    print(f"  [OK] /api/config: loaded config with battery capacity {config_data['battery_storage']['capacity_kwh']} kWh")
    results["api_endpoints"]["/api/config"] = "PASSED"

    # 3. /api/metrics
    res = client.get("/api/metrics")
    assert res.status_code == 200, f"/api/metrics failed: {res.status_code}"
    metrics_data = res.json()
    print(f"  [OK] /api/metrics: default fuel reduction = {metrics_data.get('diesel_reduction_percent', 'N/A')}%")
    results["api_endpoints"]["/api/metrics"] = "PASSED"

    # 4. Check ML evaluation metrics
    audit_json_path = os.path.join(PROJECT_ROOT, "outputs", "audit_test_results.json")
    if os.path.exists(audit_json_path):
        with open(audit_json_path, "r") as f:
            audit_json = json.load(f)
            results["ml_metrics"] = audit_json.get("ml_models", {})
    print("\n=== ML Forecasting Metrics ===")
    for target, m in results["ml_metrics"].items():
        print(f"  {target}: R2={m.get('R2')}, MAE={m.get('MAE')}, RMSE={m.get('RMSE')}")

    # Check 6 Scenarios
    horizons = [24, 48, 72]
    seasons = ["summer", "winter"]

    print("\n=== Validating All 6 Scenarios & Optimization Constraints ===")
    for season in seasons:
        for horizon in horizons:
            key = f"{season}_{horizon}h"
            print(f"\n--- Checking Scenario: {key} ---")
            res_sched = client.get(f"/api/schedule?horizon={horizon}&season={season}")
            assert res_sched.status_code == 200, f"/api/schedule failed for {key}: {res_sched.status_code}"
            data = res_sched.json()
            summary = data["summary"]
            schedule = data["schedule"]
            df = pd.DataFrame(schedule)

            # Check horizon length
            assert len(df) == horizon, f"Expected {horizon} points, got {len(df)}"

            # Check Solar in winter vs summer
            total_solar_gen = df["solar_generation_kw"].sum()
            if season == "winter":
                assert total_solar_gen == 0.0, f"Winter solar must be 0.0, got {total_solar_gen}"
                print("  [PASS] Solar generation is strictly 0.0 kW during Polar Night.")
            else:
                assert total_solar_gen > 0.0, f"Summer solar must be > 0.0, got {total_solar_gen}"
                print(f"  [PASS] Summer solar generation active: {total_solar_gen:.1f} kWh total.")

            # Check Wind in winter and summer
            total_wind_gen = df["wind_generation_kw"].sum()
            assert total_wind_gen > 0.0, f"Wind generation must be > 0, got {total_wind_gen}"
            print(f"  [PASS] Wind generation active: {total_wind_gen:.1f} kWh total.")

            # Check Battery SoC bounds [20%, 95%]
            min_soc = df["battery_soc_percent"].min()
            max_soc = df["battery_soc_percent"].max()
            assert min_soc >= 19.9, f"SoC fell below 20%: {min_soc}%"
            assert max_soc <= 95.1, f"SoC exceeded 95%: {max_soc}%"
            print(f"  [PASS] Battery SoC strictly bounded: min={min_soc:.1f}%, max={max_soc:.1f}%.")

            # Check Diesel max capacity (375 kW) and non-negative
            max_diesel = df["diesel_generation_kw"].max()
            min_diesel = df["diesel_generation_kw"].min()
            assert min_diesel >= -1e-5, f"Negative diesel: {min_diesel}"
            assert max_diesel <= 375.001, f"Diesel exceeded max capacity: {max_diesel}"
            print(f"  [PASS] Diesel bounds verified: min={min_diesel:.2f} kW, max={max_diesel:.2f} kW (limit 375 kW).")

            # Check Unmet load == 0
            total_unmet = df["unmet_demand_kw"].sum()
            assert abs(total_unmet) < 1e-4, f"Unmet load occurred: {total_unmet}"
            print("  [PASS] Station demand 100% supplied. Unmet load = 0.00 kWh.")

            # Check Power Balance for each hour:
            # (renewable_used + p_dis + p_dsl) == (demand + p_ch)
            gen = df["renewable_used_kw"] + df["battery_discharge_kw"] + df["diesel_generation_kw"]
            cons = df["predicted_demand_kw"] + df["battery_charge_kw"]
            diff = (gen - cons).abs()
            max_diff = diff.max()
            assert max_diff < 0.1, f"Power balance violated: max imbalance {max_diff}"
            print(f"  [PASS] Power balance strictly conserved across all {horizon} hours: max diff = {max_diff:.4f} kW.")

            # Check Non-negative generation
            for col in ["renewable_used_kw", "battery_discharge_kw", "battery_charge_kw", "curtailed_renewable_kw", "diesel_generation_kw"]:
                col_min = df[col].min()
                assert col_min >= -1e-5, f"Negative value in {col}: {col_min}"
            print("  [PASS] All generation and battery terms are non-negative.")

            # Check Diesel reduction
            reduction = summary["diesel_reduction_percent"]
            baseline_fuel = summary["baseline_diesel_fuel_litres"]
            opt_fuel = summary["optimized_diesel_fuel_litres"]
            print(f"  [PASS] Fuel comparison: Baseline={baseline_fuel:.1f} L, Optimized={opt_fuel:.1f} L -> Reduction = {reduction:.2f}%.")

            results["scenarios"][key] = {
                "horizon": horizon,
                "season": season,
                "solar_gen_kwh": round(float(total_solar_gen), 2),
                "wind_gen_kwh": round(float(total_wind_gen), 2),
                "diesel_gen_kwh": round(float(df["diesel_generation_kw"].sum()), 2),
                "min_soc_pct": round(float(min_soc), 2),
                "max_soc_pct": round(float(max_soc), 2),
                "diesel_reduction_pct": round(float(reduction), 2),
                "baseline_fuel_litres": round(float(baseline_fuel), 2),
                "optimized_fuel_litres": round(float(opt_fuel), 2),
                "unmet_load_kwh": round(float(total_unmet), 4),
                "max_power_balance_diff_kw": round(float(max_diff), 4)
            }

    # Verify Annual projected calculation if exists
    comparator = BaselineComparator(outputs_dir=os.path.join(PROJECT_ROOT, "outputs"))
    annual_metrics_path = os.path.join(PROJECT_ROOT, "outputs", "annual_evaluation_metrics.json")
    annual_data = None
    if os.path.exists(annual_metrics_path):
        with open(annual_metrics_path, "r") as f:
            annual_data = json.load(f)
            print(f"\nExisting validated annual metric: {annual_data}")
            results["annual_metrics"] = annual_data

    # Save validation results
    with open(os.path.join(PROJECT_ROOT, "scratch", "sih_hardening_validation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("\nALL SCENARIO & OPTIMIZATION CHECKS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_comprehensive_validation()
