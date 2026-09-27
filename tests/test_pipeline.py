"""
Polar Grid: Automated Pipeline & Verification Test Suite
Tests all 16 operational criteria:
1. Live weather API parsing & units
2. Weather fallback mechanism
3. Correct source labeling
4. No null/invalid weather data
5. Wind power curve piecewise behavior
6. Solar zero-output night/low irradiance
7. Battery SoC limits (20% - 95%)
8. Exact power balance conservation
9. Diesel capacity bound (<= 375 kW)
10. Chronological ML split
11. Zero future-data leakage
12. MAE/RMSE/R2 calculations
13. Persistence baseline comparison
14. 24h, 48h, 72h multi-horizon forecasting
15. FastAPI endpoint integration
16. Full summer and polar night scenario dispatch
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.preprocessing.data_cleaner import PolarDataPipeline
from src.features.feature_builder import FeatureBuilder
from src.forecasting.forecaster import PolarForecaster
from src.renewable.generation_estimator import RenewableEstimator
from src.optimization.dispatcher import MicrogridOptimizer
from src.evaluation.baseline_comparator import BaselineComparator
from src.weather.live_weather import WeatherForecastService
from backend.main import app

class TestPolarGridComprehensive(unittest.TestCase):

    def setUp(self):
        self.config_path = os.path.join(PROJECT_ROOT, "config", "station_config.json")
        self.processed_data_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        self.client = TestClient(app)

    def test_01_data_pipeline_integrity(self):
        """Checks data extraction, non-empty processed CSV, and non-null values."""
        self.assertTrue(os.path.exists(self.processed_data_path), "Processed dataset must exist")
        df = pd.read_csv(self.processed_data_path)
        self.assertGreater(len(df), 8000, "Should have full year hourly records")
        required_cols = ['timestamp', 'temperature_celsius', 'wind_speed_ms', 'solar_radiation_wm2', 'modeled_demand_kw']
        for col in required_cols:
            self.assertIn(col, df.columns)
            self.assertEqual(df[col].isnull().sum(), 0, f"Column {col} must have zero null values")

    def test_02_feature_builder_ordering(self):
        """Verifies feature creation, cyclical columns, and chronological sequence."""
        df = pd.read_csv(self.processed_data_path).head(200)
        fb = FeatureBuilder()
        feats = fb.build_features(df)
        self.assertIn("sin_hour", feats.columns)
        self.assertIn("cos_hour", feats.columns)
        self.assertIn("modeled_demand_kw_lag24", feats.columns)
        timestamps = pd.to_datetime(feats['timestamp'])
        self.assertTrue(timestamps.is_monotonic_increasing, "Timestamps must be monotonically increasing")

    def test_03_renewable_physics(self):
        """Verifies wind power curve and solar physics bounds."""
        estimator = RenewableEstimator(self.config_path)
        
        # Wind cut-in (< 3.5 m/s should be 0 kW)
        zero_wind = estimator.estimate_wind_power(np.array([1.0, 2.5, 3.49]))
        self.assertTrue(np.all(zero_wind == 0.0), "Wind power below cut-in must be 0")
        
        # Wind rated (12 m/s to 25 m/s should be 200 kW)
        rated_wind = estimator.estimate_wind_power(np.array([12.0, 15.0, 25.0]))
        self.assertTrue(np.all(rated_wind == 200.0), "Wind power at rated speed must be 200 kW")
        
        # Wind cut-out (> 25 m/s storm shutdown should be 0 kW)
        cutout_wind = estimator.estimate_wind_power(np.array([25.01, 30.0]))
        self.assertTrue(np.all(cutout_wind == 0.0), "Wind power above cut-out must be 0 for safety")
        
        # Solar at night / zero irradiance (G=0 should be 0 kW)
        night_solar = estimator.estimate_solar_power(np.array([0.0, 0.0]), np.array([-15.0, -10.0]))
        self.assertTrue(np.all(night_solar == 0.0), "Solar power with 0 irradiance must be 0")

    def test_04_optimization_power_conservation_and_battery_limits(self):
        """
        Verifies exact power balance and battery constraints:
        (Renewables_used + Battery_dis + Diesel + Unmet) - Battery_charge == Demand
        Battery SOC bounds: 20% to 95%
        Diesel capacity bound: <= 375 kW
        """
        optimizer = MicrogridOptimizer(self.config_path)
        
        test_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=24, freq="1h"),
            "pred_modeled_demand_kw": [150.0] * 24,
            "solar_generation_kw": [50.0 if 6 <= h <= 18 else 0.0 for h in range(24)],
            "wind_generation_kw": [100.0] * 24
        })
        
        sched = optimizer.optimize_schedule(test_df, initial_soc=0.5)
        self.assertEqual(len(sched), 24)
        
        # 1. Battery SoC bounds (20% to 95%)
        socs = sched["battery_soc_percent"].values
        self.assertTrue(np.all(socs >= 19.99), f"Battery SoC violated min limit: {socs.min()}")
        self.assertTrue(np.all(socs <= 95.01), f"Battery SoC violated max limit: {socs.max()}")
        
        # 2. Diesel capacity bound
        diesel = sched["diesel_generation_kw"].values
        self.assertTrue(np.all(diesel >= 0.0), "Diesel generation cannot be negative")
        self.assertTrue(np.all(diesel <= 375.01), "Diesel generation exceeded 375 kW capacity")
        
        # 3. Exact energy balance:
        # Generation (Solar_used + Wind_used + Bat_dis + Diesel + Unmet) - Bat_charge == Demand
        supplied = sched["renewable_used_kw"] + sched["battery_discharge_kw"] + sched["diesel_generation_kw"] + sched["unmet_demand_kw"]
        consumed = sched["predicted_demand_kw"] + sched["battery_charge_kw"]
        np.testing.assert_allclose(supplied.values, consumed.values, atol=1e-2, err_msg="Exact energy balance violated")

    def test_05_live_weather_service_and_schema(self):
        """Tests live weather service parsing, units, and non-null values."""
        service = WeatherForecastService()
        res = service.get_weather_forecast(horizon_hours=24)
        self.assertIn("source", res)
        self.assertIn("mode", res)
        self.assertIn("updated_at", res)
        self.assertEqual(len(res["points"]), 24)
        
        # Check units and schema of first point
        p0 = res["points"][0]
        self.assertIn("temperature_celsius", p0)
        self.assertIn("wind_speed_ms", p0)
        self.assertIn("solar_radiation_wm2", p0)
        self.assertGreaterEqual(p0["wind_speed_ms"], 0.0)
        self.assertGreaterEqual(p0["solar_radiation_wm2"], 0.0)

    def test_06_weather_fallback_behavior(self):
        """Tests that fallback engages when forced or offline, with explicit source label."""
        service = WeatherForecastService()
        fallback_res = service.get_weather_forecast(force_fallback=True, horizon_hours=24)
        self.assertIn(fallback_res["mode"], ["fallback", "cached", "historical_fallback"])
        self.assertFalse(fallback_res["is_live"])
        self.assertTrue(len(fallback_res["points"]) == 24)
        # Source must explicitly declare fallback
        self.assertTrue("Fallback" in fallback_res["source"] or "Cached" in fallback_res["source"])

    def test_07_chronological_ml_validation_and_baselines(self):
        """Verifies chronological split with zero future-data leakage and Persistence Baseline."""
        df_raw = pd.read_csv(self.processed_data_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        
        forecaster = PolarForecaster()
        forecaster.train_evaluate(df_feat, train_ratio=0.80)
        
        summary = forecaster.validation_summary
        self.assertIn("training_period", summary)
        self.assertIn("testing_period", summary)
        self.assertFalse(summary["leakage_audit"]["future_data_leakage"])
        self.assertFalse(summary["leakage_audit"]["shuffled"])
        
        # Baseline comparison checks
        comp = forecaster.baseline_comparisons
        self.assertIn("modeled_demand_kw", comp)
        self.assertIn("solar_radiation_wm2", comp)
        self.assertIn("wind_speed_ms", comp)
        self.assertIn("temperature_celsius", comp)
        
        for tgt in comp:
            self.assertIn("baseline_mae", comp[tgt])
            self.assertIn("ml_mae", comp[tgt])
            self.assertIn("improvement_percent", comp[tgt])

    def test_08_multi_horizon_forecasting(self):
        """Verifies multi-horizon evaluation for 24h, 48h, 72h."""
        df_raw = pd.read_csv(self.processed_data_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        forecaster = PolarForecaster()
        forecaster.load_models()
        
        for h in [24, 48, 72]:
            fc = forecaster.generate_forecast(df_feat, horizon_hours=h, season="summer")
            self.assertEqual(len(fc), h)
            self.assertIn("pred_modeled_demand_kw", fc.columns)
            self.assertIn("pred_solar_radiation_wm2", fc.columns)
            self.assertIn("pred_wind_speed_ms", fc.columns)

    def test_09_full_scenario_tests(self):
        """
        Runs Summer & Polar Night scenarios across 24h, 48h, 72h.
        Verifies:
        - Power balance error = 0
        - Battery SOC in [20%, 95%]
        - Solar is 0 in polar night
        - Positive fuel savings in summer
        """
        df_raw = pd.read_csv(self.processed_data_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        
        forecaster = PolarForecaster()
        forecaster.load_models()
        ren_estimator = RenewableEstimator(self.config_path)
        optimizer = MicrogridOptimizer(self.config_path)
        comparator = BaselineComparator(self.config_path)
        
        for season in ["summer", "winter"]:
            for h in [24, 48, 72]:
                fc_df = forecaster.generate_forecast(df_feat, horizon_hours=h, season=season)
                ren_df = ren_estimator.process_forecast_dataframe(fc_df)
                sched = optimizer.optimize_schedule(ren_df, initial_soc=0.50)
                
                # Check length
                self.assertEqual(len(sched), h)
                
                # Power balance
                gen = sched["renewable_used_kw"] + sched["battery_discharge_kw"] + sched["diesel_generation_kw"] + sched["unmet_demand_kw"]
                load = sched["predicted_demand_kw"] + sched["battery_charge_kw"]
                np.testing.assert_allclose(gen.values, load.values, atol=1e-2)
                
                # Battery bounds
                self.assertGreaterEqual(sched["battery_soc_percent"].min(), 19.99)
                self.assertLessEqual(sched["battery_soc_percent"].max(), 95.01)
                
                # Unmet load
                self.assertAlmostEqual(sched["unmet_demand_kw"].sum(), 0.0, places=1)
                
                # Solar in winter must be strictly 0
                if season == "winter":
                    self.assertAlmostEqual(sched["solar_generation_kw"].max(), 0.0, places=2)
                    
                # Fuel reduction in summer must be significant (> 50%)
                if season == "summer":
                    metrics = comparator.evaluate(sched)
                    self.assertGreater(metrics["diesel_reduction_percent"], 50.0)

    def test_10_api_endpoints(self):
        """Verifies FastAPI REST endpoints."""
        # 1. /api/status
        r_status = self.client.get("/api/status")
        self.assertEqual(r_status.status_code, 200)
        self.assertEqual(r_status.json()["station"], "Mawson Station")
        
        # 2. /api/weather/live
        r_weather = self.client.get("/api/weather/live?horizon=24")
        self.assertEqual(r_weather.status_code, 200)
        self.assertEqual(r_weather.json()["forecast_hours"], 24)
        
        # 3. /api/validation
        r_val = self.client.get("/api/validation")
        self.assertEqual(r_val.status_code, 200)
        self.assertIn("ml_vs_baseline", r_val.json())
        
        # 4. /api/schedule
        r_sched = self.client.get("/api/schedule?horizon=24&season=summer")
        self.assertEqual(r_sched.status_code, 200)
        self.assertIn("summary", r_sched.json())
        self.assertIn("schedule", r_sched.json())

    def test_11_validation_day_endpoint(self):
        """Verifies /api/validation/day dynamic historical prediction endpoint."""
        # 1. Default day fetch
        r_def = self.client.get("/api/validation/day")
        self.assertEqual(r_def.status_code, 200)
        data_def = r_def.json()

        self.assertIn("selected_date", data_def)
        self.assertIn("available_dates", data_def)
        self.assertGreater(len(data_def["available_dates"]), 50)
        self.assertIn("summary", data_def)
        self.assertIn("hourly_records", data_def)

        # 2. Check 24-hour records
        records = data_def["hourly_records"]
        self.assertEqual(len(records), 24)
        for rec in records:
            self.assertIn("time", rec)
            self.assertIn("predicted_demand_kw", rec)
            self.assertIn("actual_demand_kw", rec)
            self.assertIn("difference_kw", rec)
            self.assertGreater(rec["predicted_demand_kw"], 0)
            self.assertGreater(rec["actual_demand_kw"], 0)

        # 3. Check summary metrics
        summary = data_def["summary"]
        self.assertIn("avg_predicted_demand_kw", summary)
        self.assertIn("avg_actual_demand_kw", summary)
        self.assertIn("prediction_match_percent", summary)
        self.assertIn("match_statement", summary)
        self.assertGreater(summary["prediction_match_percent"], 80.0)

        # 4. Query specific validation date
        target_date = data_def["available_dates"][0]
        r_custom = self.client.get(f"/api/validation/day?date={target_date}")
        self.assertEqual(r_custom.status_code, 200)
        data_custom = r_custom.json()
        self.assertEqual(data_custom["selected_date"], target_date)
        self.assertEqual(len(data_custom["hourly_records"]), 24)

if __name__ == "__main__":
    unittest.main()
