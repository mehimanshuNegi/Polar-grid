"""
POLAR GRID: Master Pipeline Runner
Executes the complete end-to-end workflow:
1. Data Ingestion & Preprocessing (AADC + ERA5)
2. Feature Engineering & Chronological Split
3. ML Forecasting & Persistence Baseline Benchmarking
4. Live ECMWF Weather Service Verification
5. Physical Renewable Potential Conversion
6. SciPy HiGHS Microgrid Dispatch Optimization
7. Baseline Comparison, Metrics & Artifact Generation
"""

import os
import sys
import json
import pandas as pd

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.preprocessing.data_cleaner import PolarDataPipeline
from src.features.feature_builder import FeatureBuilder
from src.forecasting.forecaster import PolarForecaster
from src.renewable.generation_estimator import RenewableEstimator
from src.optimization.dispatcher import MicrogridOptimizer
from src.evaluation.baseline_comparator import BaselineComparator
from src.weather.live_weather import WeatherForecastService

def run_polar_grid_pipeline(horizon_hours: int = 24):
    print("=" * 75)
    print("      POLAR GRID: ANTARCTIC MICROGRID DISPATCH & FORECASTING      ")
    print("                  Mawson Station, Antarctica                      ")
    print("=" * 75)

    # 1. Data Ingestion & Preprocessing
    print("\n[STEP 1/8] Ingesting and Cleaning Datasets (AADC Monthly + ERA5 Hourly)...")
    pipeline = PolarDataPipeline(PROJECT_ROOT)
    df_hourly = pipeline.run()
    print(f"-> Ready with {len(df_hourly)} hourly rows of cleaned weather & calibrated demand data.")

    # 2. Feature Engineering
    print("\n[STEP 2/8] Constructing Temporal, Cyclical, & Lag Features...")
    fb = FeatureBuilder()
    df_features = fb.build_features(df_hourly)
    print(f"-> Engineered {df_features.shape[1]} features across {len(df_features)} samples.")

    # 3. Model Training & Evaluation (Strict Chronological Split)
    print("\n[STEP 3/8] Training & Evaluating ML Models vs Persistence Baseline (Chronological)...")
    forecaster = PolarForecaster()
    train_results = forecaster.train_evaluate(df_features, train_ratio=0.80)

    # 4. Live Weather Forecast Verification
    print("\n[STEP 4/8] Checking Live ECMWF IFS Weather Endpoint...")
    weather_service = WeatherForecastService()
    weather_payload = weather_service.get_weather_forecast(horizon_hours=horizon_hours)
    print(f"-> Live Weather Status: {weather_payload['source']} (Mode: {weather_payload['mode']}, Updated: {weather_payload['updated_at']})")

    # 5. Generate Operational Forecast
    print(f"\n[STEP 5/8] Generating {horizon_hours}-Hour Benchmark Forecast (Austral Summer)...")
    forecast_df = forecaster.generate_forecast(df_features, horizon_hours=horizon_hours, season="summer")

    # 6. Renewable Generation Estimation
    print("\n[STEP 6/8] Computing Renewable Generation Potential (Solar PV + Wind Turbines)...")
    ren_estimator = RenewableEstimator()
    forecast_ren_df = ren_estimator.process_forecast_dataframe(forecast_df)
    
    total_sol_kw = forecast_ren_df["solar_generation_kw"].sum()
    total_wnd_kw = forecast_ren_df["wind_generation_kw"].sum()
    print(f"-> Estimated {horizon_hours}h Potential: Solar={total_sol_kw:.1f} kWh, Wind={total_wnd_kw:.1f} kWh")

    # 7. Microgrid Optimization & Dispatch Scheduling
    print("\n[STEP 7/8] Optimizing Energy Dispatch (SciPy HiGHS Linear Programming)...")
    optimizer = MicrogridOptimizer()
    schedule_df = optimizer.optimize_schedule(forecast_ren_df, initial_soc=0.50)
    
    # Save schedule CSVs
    outputs_dir = os.path.join(PROJECT_ROOT, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    output_schedule_path = os.path.join(outputs_dir, f"optimized_schedule_{horizon_hours}h.csv")
    schedule_df.to_csv(output_schedule_path, index=False)
    print(f"-> Saved optimized schedule to {output_schedule_path}")

    # 8. Baseline Comparison & Visualizations
    print("\n[STEP 8/8] Evaluating Impact vs. 100% Diesel Baseline & Generating Plots...")
    comparator = BaselineComparator(outputs_dir=outputs_dir)
    metrics = comparator.evaluate(schedule_df)
    metrics["weather_source"] = weather_payload["source"]
    metrics["weather_mode"] = weather_payload["mode"]
    metrics["weather_updated_at"] = weather_payload["updated_at"]
    comparator.generate_visualizations(schedule_df, forecast_df)

    print("\n" + "=" * 75)
    print("                     DISPATCH SUMMARY RESULTS                     ")
    print("=" * 75)
    print(f"  Planning Horizon            : {metrics['time_horizon_hours']} Hours")
    print(f"  Total Station Demand        : {metrics['total_demand_kwh']:,.1f} kWh")
    print(f"  Renewable Energy Used       : {metrics['renewable_energy_used_kwh']:,.1f} kWh ({metrics['renewable_penetration_percent']:.1f}% penetration)")
    print(f"  Diesel Energy Used          : {metrics['diesel_energy_used_kwh']:,.1f} kWh")
    print(f"  Battery Throughput (Disch.) : {metrics['battery_discharge_kwh']:,.1f} kWh")
    print(f"  Unmet Load                  : {metrics['unmet_demand_kwh']:.2f} kWh")
    print("-" * 75)
    print(f"  Baseline Diesel Fuel        : {metrics['baseline_diesel_fuel_litres']:,.1f} Litres")
    print(f"  Polar Grid Diesel Fuel      : {metrics['optimized_diesel_fuel_litres']:,.1f} Litres")
    print(f"  Diesel Fuel Saved           : {metrics['diesel_fuel_saved_litres']:,.1f} Litres")
    print(f"  >>> DIESEL REDUCTION        : {metrics['diesel_reduction_percent']:.2f}% <<<")
    print("=" * 75)
    print("Pipeline completed successfully!\n")
    return metrics, schedule_df

if __name__ == "__main__":
    run_polar_grid_pipeline(horizon_hours=24)
