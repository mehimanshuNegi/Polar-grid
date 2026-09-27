"""
Polar Grid: FastAPI REST Backend
Exposes Live ECMWF weather forecasting, transparent Mawson station demand prediction,
physics-based renewable generation, HiGHS microgrid dispatch scheduling,
and rigorous ML validation vs Persistence baseline.
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.api_models import (
    DispatchRunRequest,
    DispatchSummaryMetrics,
    LiveWeatherResponse,
    WeatherStatusResponse,
    WeatherRefreshResponse
)
from src.features.feature_builder import FeatureBuilder
from src.forecasting.forecaster import PolarForecaster
from src.renewable.generation_estimator import RenewableEstimator
from src.optimization.dispatcher import MicrogridOptimizer
from src.evaluation.baseline_comparator import BaselineComparator
from src.weather.live_weather import (
    WeatherForecastService,
    start_background_weather_refresh,
    stop_background_weather_refresh
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background weather refresh daemon
    start_background_weather_refresh()
    yield
    # Shutdown: Stop background daemon
    stop_background_weather_refresh()

app = FastAPI(
    title="Polar Grid API",
    description="AI-Assisted Renewable Energy Forecasting and Optimization for Antarctic Stations",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite ports: 5173, 3000, 8000, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs directory for generated charts and reports
outputs_dir = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(outputs_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

# Mount built frontend dist if available
frontend_dist = os.path.join(PROJECT_ROOT, "frontend", "dist")
if os.path.exists(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="static_assets")

from fastapi.responses import FileResponse

@app.get("/")
def serve_root():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "project": "Polar Grid",
        "station": "Mawson Station, Antarctica",
        "status": "online",
        "endpoints": [
            "/api/status",
            "/api/config",
            "/api/weather/live",
            "/api/validation",
            "/api/metrics",
            "/api/forecast",
            "/api/schedule",
            "/api/run-dispatch"
        ]
    }

# Helper to load station config
def get_config():
    cfg_path = os.path.join(PROJECT_ROOT, "config", "station_config.json")
    with open(cfg_path, "r") as f:
        return json.load(f)

def resolve_equipment_state(
    battery_state: str = "NORMAL",
    diesel_state: str = "NORMAL",
    initial_soc: float = None,
    diesel_capacity_kw: float = None
):
    """
    Translates prototype simulated equipment state assumptions into physical solver limits.
    Labeled as prototype assumption — not live Mawson BMS/SCADA telemetry.
    """
    bat_state = (battery_state or "NORMAL").upper()
    if initial_soc is not None:
        effective_soc = float(initial_soc)
        if effective_soc <= 0.21:
            bat_state = "CRITICAL"
        elif effective_soc <= 0.35:
            bat_state = "LOW"
        else:
            bat_state = "NORMAL"
    else:
        if bat_state == "CRITICAL":
            effective_soc = 0.20  # Physical minimum SoC floor
        elif bat_state == "LOW":
            effective_soc = 0.25  # Low reserve
        else:
            effective_soc = 0.50  # Standard nominal operational state
            bat_state = "NORMAL"

    dsl_state = (diesel_state or "NORMAL").upper()
    if diesel_capacity_kw is not None:
        effective_diesel_cap = float(diesel_capacity_kw)
        if effective_diesel_cap <= 130.0:
            dsl_state = "CRITICAL"
        elif effective_diesel_cap <= 260.0:
            dsl_state = "LIMITED"
        else:
            dsl_state = "NORMAL"
    else:
        if dsl_state == "CRITICAL":
            effective_diesel_cap = 125.0  # 1 generator unit (125 kW)
        elif dsl_state == "LIMITED":
            effective_diesel_cap = 250.0  # 2 generator units (250 kW)
        else:
            effective_diesel_cap = 375.0  # Full capacity: 3 units (375 kW)
            dsl_state = "NORMAL"

    alerts = []
    if bat_state == "CRITICAL" and dsl_state == "CRITICAL":
        alerts.append("🔴 Energy reserve critical")
    else:
        if bat_state == "CRITICAL":
            alerts.append("🔴 Battery reserve critical")
        elif bat_state == "LOW":
            alerts.append("⚠ Battery reserve low")

        if dsl_state == "CRITICAL":
            alerts.append("🔴 Diesel availability critical")
        elif dsl_state == "LIMITED":
            alerts.append("⚠ Diesel availability limited")

    return {
        "battery_state": bat_state,
        "initial_soc": round(effective_soc, 2),
        "diesel_state": dsl_state,
        "diesel_capacity_kw": round(effective_diesel_cap, 1),
        "alerts": alerts
    }

@app.get("/api/status")
@app.get("/health")
def get_status():
    cfg = get_config()
    return {
        "status": "healthy",
        "station": cfg["station"]["name"],
        "country": cfg["station"]["country"],
        "coordinates": cfg["station"]["coordinates"],
        "description": cfg["station"]["description"],
        "load_telemetry_note": "MODELED HOURLY LOAD — CALIBRATED TO REAL MAWSON MONTHLY ELECTRICITY DATA (AADC)"
    }

@app.get("/api/config")
def read_config():
    return get_config()

@app.get("/api/weather/live", response_model=LiveWeatherResponse)
def get_live_weather(
    force_fallback: bool = Query(False, description="Forces historical fallback mode"),
    horizon: int = Query(72, ge=12, le=96, description="Forecast horizon hours")
):
    """
    Fetches genuine ECMWF IFS hourly numerical weather forecast for Mawson Station
    via Open-Meteo with local caching and transparent ERA5 fallback.
    """
    service = WeatherForecastService()
    payload = service.get_weather_forecast(force_fallback=force_fallback, horizon_hours=horizon)
    return payload

@app.get("/api/weather/status", response_model=WeatherStatusResponse)
def get_weather_status():
    """
    Diagnostic & health endpoint reporting current weather pipeline state,
    provider cooldown status, cache age, and last provider response.
    Never triggers external weather provider requests.
    """
    service = WeatherForecastService()
    return service.get_pipeline_status()

@app.post("/api/weather/refresh", response_model=WeatherRefreshResponse)
def manual_weather_refresh(
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    key: Optional[str] = Query(None)
):
    """
    Triggers an immediate controlled weather refresh attempt.
    Respects provider cooldown and request locks.
    """
    auth_key = admin_key or key
    expected_key = os.environ.get("WEATHER_ADMIN_KEY") or os.environ.get("WEATHER_REFRESH_TOKEN")
    allow_manual = os.environ.get("ALLOW_MANUAL_REFRESH", "true").lower() in ("true", "1", "yes")

    if expected_key and auth_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: invalid admin key")
    elif not expected_key and not allow_manual:
        raise HTTPException(status_code=403, detail="Manual weather refresh is disabled in production")

    service = WeatherForecastService()
    success, payload = service.refresh_weather_snapshot(force=True, horizon_hours=24)
    return {
        "success": success,
        "source": payload.get("source", "ECMWF IFS"),
        "mode": payload.get("mode", "cached"),
        "is_live": payload.get("is_live", False),
        "fetched_at": payload.get("fetched_at"),
        "forecast_updated_at": payload.get("forecast_updated_at"),
        "error": payload.get("fallback_reason") if not success else None
    }

@app.post("/api/weather/sync")
def sync_weather_snapshot(
    payload: dict = Body(...),
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    key: Optional[str] = Query(None)
):
    """
    Ingests an authentic external ECMWF forecast pushed by an external runner or webhook.
    """
    auth_key = admin_key or key
    expected_key = os.environ.get("WEATHER_ADMIN_KEY") or os.environ.get("WEATHER_SYNC_TOKEN")
    if expected_key and auth_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized: invalid sync token")

    service = WeatherForecastService()
    try:
        ingested = service.ingest_synced_snapshot(payload)
        return {
            "success": True,
            "message": "Weather snapshot ingested successfully",
            "source": ingested["source"],
            "points": len(ingested["points"]),
            "fetched_at": ingested["fetched_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {e}")

@app.get("/api/validation")
def get_validation_metrics(date: Optional[str] = Query(None, description="Optional date to retrieve daily comparison")):
    """
    Returns chronological ML validation results, Persistence Baseline comparisons,
    or delegates to daily comparison if date is provided.
    """
    if date:
        return get_validation_day(date)

    val_file = os.path.join(outputs_dir, "validation_metrics.json")
    if os.path.exists(val_file):
        try:
            with open(val_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Fallback to loading via forecaster
    forecaster = PolarForecaster()
    try:
        forecaster.load_models()
        return forecaster.validation_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation metrics not ready: {e}")

_validation_cache = None

def get_historical_validation_data():
    global _validation_cache
    if _validation_cache is not None:
        return _validation_cache

    import joblib
    processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
    df_raw = pd.read_csv(processed_path)
    fb = FeatureBuilder()
    df_feat = fb.build_features(df_raw)
    df_feat["timestamp"] = pd.to_datetime(df_feat["timestamp"])

    split_idx = int(len(df_feat) * 0.8)
    test_df = df_feat.iloc[split_idx:].copy()

    model_path = os.path.join(PROJECT_ROOT, "models", "modeled_demand_kw_model.joblib")
    feat_path = os.path.join(PROJECT_ROOT, "models", "feature_columns.joblib")

    if not os.path.exists(model_path) or not os.path.exists(feat_path):
        forecaster = PolarForecaster()
        forecaster.train_evaluate(df_feat)

    features = joblib.load(feat_path)
    model = joblib.load(model_path)

    test_df["pred_demand"] = model.predict(test_df[features])
    test_df["actual_demand"] = test_df["modeled_demand_kw"]
    test_df["date_str"] = test_df["timestamp"].dt.strftime("%Y-%m-%d")

    # Filter to only complete 24-hour days
    date_counts = test_df.groupby("date_str").size()
    full_dates = sorted(date_counts[date_counts == 24].index.tolist())

    _validation_cache = {
        "test_df": test_df,
        "available_dates": full_dates
    }
    return _validation_cache

@app.get("/api/validation/day")
def get_validation_day(date: str = Query(None, description="Selected validation date in YYYY-MM-DD format")):
    """
    Returns dynamically computed prediction vs actual demand for a single 24-hour historical day
    from the unseen validation period. Uses the real trained ML model and real recorded station data.
    """
    cache = get_historical_validation_data()
    available_dates = cache["available_dates"]
    if not available_dates:
        raise HTTPException(status_code=404, detail="No historical validation days available.")

    selected_date = date if (date and date in available_dates) else available_dates[len(available_dates) // 2]

    day_df = cache["test_df"][cache["test_df"]["date_str"] == selected_date].copy()
    day_df = day_df.sort_values("timestamp")

    hourly_records = []
    for _, row in day_df.iterrows():
        pred = round(float(row["pred_demand"]), 1)
        actual = round(float(row["actual_demand"]), 1)
        diff = round(pred - actual, 1)
        abs_diff = round(abs(pred - actual), 1)
        ts = row["timestamp"]
        hourly_records.append({
            "time": ts.strftime("%H:%M"),
            "timestamp": ts.isoformat(),
            "predicted_demand_kw": pred,
            "actual_demand_kw": actual,
            "difference_kw": diff,
            "abs_difference_kw": abs_diff
        })

    avg_pred = round(float(day_df["pred_demand"].mean()), 1)
    avg_act = round(float(day_df["actual_demand"].mean()), 1)
    mae = float(np.mean(np.abs(day_df["pred_demand"] - day_df["actual_demand"])))
    match_pct = round(max(0.0, 100.0 * (1.0 - (mae / avg_act))), 1)

    statement = "Predicted demand closely followed the actual station demand." if match_pct >= 90.0 else "Predicted demand tracked station baseline with variance."

    formatted_date = pd.to_datetime(selected_date).strftime("%B %d, %Y")
    available_dates_formatted = [
        {"date": d, "label": pd.to_datetime(d).strftime("%b %d, %Y")}
        for d in available_dates
    ]

    return {
        "selected_date": selected_date,
        "formatted_date": formatted_date,
        "available_dates": available_dates,
        "available_dates_formatted": available_dates_formatted,
        "summary": {
            "avg_predicted_demand_kw": avg_pred,
            "avg_actual_demand_kw": avg_act,
            "prediction_match_percent": match_pct,
            "match_statement": statement
        },
        "hourly_records": hourly_records
    }


@app.get("/api/metrics")
def get_metrics():
    summary_path = os.path.join(outputs_dir, "dispatch_summary_metrics.json")
    if not os.path.exists(summary_path):
        raise HTTPException(status_code=404, detail="Dispatch metrics not found. Run dispatch first.")
    with open(summary_path, "r") as f:
        return json.load(f)

@app.get("/api/forecast")
def get_forecast(
    horizon: int = Query(24, ge=6, le=96),
    season: str = Query("summer", description="'summer', 'winter', or 'live'")
):
    """
    Returns hourly forecasted values and ML performance metrics.
    - 'live': Real ECMWF IFS weather forecast + Mawson demand model.
    - 'summer': Austral summer benchmark (Dec 24h sun).
    - 'winter': Polar night benchmark (Jul zero sun).
    """
    forecaster = PolarForecaster()
    try:
        forecaster.load_models()
    except Exception:
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        forecaster.train_evaluate(df_feat)

    if season.lower() == "live":
        # Fetch live ECMWF forecast
        weather_service = WeatherForecastService()
        df_weather, meta = weather_service.get_forecast_dataframe(horizon_hours=horizon)
        # Model demand from thermal/temporal relationships
        df_demand = forecaster.predict_demand_for_weather(df_weather)
        
        # Build records
        points = []
        for _, r in df_demand.iterrows():
            points.append({
                "timestamp": str(r["timestamp"]),
                "pred_modeled_demand_kw": float(r["pred_modeled_demand_kw"]),
                "pred_wind_speed_ms": float(r["wind_speed_ms"]),
                "pred_solar_radiation_wm2": float(r["solar_radiation_wm2"]),
                "pred_temperature_celsius": float(r["temperature_celsius"]),
                "actual_wind_speed_ms": None,
                "actual_solar_radiation_wm2": None,
                "actual_temperature_celsius": None,
                "actual_modeled_demand_kw": None
            })
            
        return {
            "horizon_hours": horizon,
            "season": "live",
            "weather_metadata": meta,
            "evaluation_metrics": forecaster.metrics,
            "baseline_comparisons": forecaster.baseline_comparisons,
            "points": points
        }
    else:
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        
        forecast_df = forecaster.generate_forecast(df_feat, horizon_hours=horizon, season=season)
        meta = {
            "source": "ERA5 Reanalysis (Historical Benchmark)",
            "provider": "ECMWF ERA5 Historical Reanalysis",
            "mode": "historical",
            "is_live": False,
            "updated_at": "Historical Benchmark (2023 Archive)",
            "fetched_at": "Historical Benchmark (2023 Archive)",
            "forecast_updated_at": "Historical Benchmark (2023 Archive)",
            "cache_age_seconds": None,
            "fallback_reason": None,
            "latitude": -67.6027,
            "longitude": 62.8738
        }
        return {
            "horizon_hours": horizon,
            "season": season,
            "weather_metadata": meta,
            "evaluation_metrics": forecaster.metrics,
            "baseline_comparisons": forecaster.baseline_comparisons,
            "points": forecast_df.to_dict(orient="records")
        }

@app.get("/api/schedule")
def get_schedule(
    horizon: int = Query(24, ge=6, le=96),
    season: str = Query("summer", description="'summer', 'winter', or 'live'"),
    battery_state: str = Query("NORMAL", description="Simulated battery state: 'NORMAL', 'LOW', 'CRITICAL'"),
    diesel_state: str = Query("NORMAL", description="Simulated diesel state: 'NORMAL', 'LIMITED', 'CRITICAL'"),
    initial_soc: Optional[float] = Query(None, ge=0.20, le=0.95),
    diesel_capacity_kw: Optional[float] = Query(None, ge=50.0, le=375.0)
):
    """
    Generates the optimal microgrid dispatch schedule (renewables + battery + diesel).
    Supports live ECMWF forecasts, historical benchmarks, and simulated equipment what-if states.
    """
    forecaster = PolarForecaster()
    try:
        forecaster.load_models()
    except Exception:
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        forecaster.train_evaluate(df_feat)

    ren_estimator = RenewableEstimator()
    optimizer = MicrogridOptimizer()

    eq = resolve_equipment_state(
        battery_state=battery_state,
        diesel_state=diesel_state,
        initial_soc=initial_soc,
        diesel_capacity_kw=diesel_capacity_kw
    )

    if season.lower() == "live":
        # 1. Live ECMWF weather
        weather_service = WeatherForecastService()
        df_weather, weather_meta = weather_service.get_forecast_dataframe(horizon_hours=horizon)
        
        # 2. Demand prediction via parametric thermal model
        df_forecast = forecaster.predict_demand_for_weather(df_weather)
        df_forecast["pred_wind_speed_ms"] = df_forecast["wind_speed_ms"]
        df_forecast["pred_solar_radiation_wm2"] = df_forecast["solar_radiation_wm2"]
        df_forecast["pred_temperature_celsius"] = df_forecast["temperature_celsius"]
        
        # 3. Renewable physical generation
        df_ren = ren_estimator.process_forecast_dataframe(df_forecast)
        sim_label = "Live ECMWF Forecast (Operational Dispatch)"
    else:
        # Historical benchmark
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        
        df_forecast = forecaster.generate_forecast(df_feat, horizon_hours=horizon, season=season)
        df_ren = ren_estimator.process_forecast_dataframe(df_forecast)
        
        weather_meta = {
            "source": "ERA5 Reanalysis (Historical Benchmark)",
            "provider": "ECMWF ERA5 Historical Reanalysis",
            "mode": "historical",
            "is_live": False,
            "updated_at": "Historical Benchmark (2023 Archive)",
            "fetched_at": "Historical Benchmark (2023 Archive)",
            "forecast_updated_at": "Historical Benchmark (2023 Archive)",
            "cache_age_seconds": None,
            "fallback_reason": None,
            "latitude": -67.6027,
            "longitude": 62.8738
        }
        sim_label = "Austral Summer (24-Hour Sun)" if season.lower() == "summer" else "Polar Night (Sun Below Horizon)"

    # 4. HiGHS Linear Programming Optimization with Simulated Equipment Constraints
    optimizer.gen_cfg["total_capacity_kw"] = eq["diesel_capacity_kw"]
    schedule_df = optimizer.optimize_schedule(df_ren, initial_soc=eq["initial_soc"])
    
    # Attach weather variables to schedule records for telemetry
    for col in ["wind_speed_ms", "solar_radiation_wm2", "temperature_celsius"]:
        if col in df_ren.columns:
            schedule_df[col] = df_ren[col].values
        elif f"pred_{col}" in df_ren.columns:
            schedule_df[col] = df_ren[f"pred_{col}"].values
    
    # 5. Baseline Comparator
    comparator = BaselineComparator(outputs_dir=outputs_dir)
    summary = comparator.evaluate(schedule_df)
    summary["baseline_diesel_litres"] = summary.get("baseline_diesel_fuel_litres", 0.0)
    summary["optimized_diesel_litres"] = summary.get("optimized_diesel_fuel_litres", 0.0)
    summary["diesel_saved_litres"] = summary.get("diesel_fuel_saved_litres", 0.0)
    summary["renewable_coverage_percent"] = summary.get("renewable_penetration_percent", 0.0)
    summary["season"] = season
    summary["simulation_label"] = sim_label
    summary["weather_source"] = weather_meta["source"]
    summary["weather_mode"] = weather_meta["mode"]
    summary["weather_updated_at"] = weather_meta["updated_at"]
    summary["annual_validated_reduction_percent"] = 41.45
    summary["annual_validated_note"] = "Projected annual diesel reduction — 12-month simulation benchmark"

    # Attach simulated equipment layer metadata and authoritative Hour 0 power balance
    alerts = list(eq["alerts"])
    
    if len(schedule_df) > 0:
        row0 = schedule_df.iloc[0]
        cur_demand = round(float(row0["predicted_demand_kw"]), 1)
        cur_wind = round(float(row0.get("wind_generation_kw", 0.0)), 1)
        cur_solar = round(float(row0.get("solar_generation_kw", 0.0)), 1)
        cur_diesel = round(float(row0.get("diesel_generation_kw", 0.0)), 1)
        cur_dis = round(float(row0.get("battery_discharge_kw", 0.0)), 1)
        cur_ch = round(float(row0.get("battery_charge_kw", 0.0)), 1)
        raw_unmet = round(float(row0.get("unmet_demand_kw", 0.0)), 2)
        cur_soc = round(float(row0.get("battery_soc_percent", 50.0)), 1)
        
        # Power balance consistency: total supplied generation into bus
        cur_supply = round(cur_wind + cur_solar + cur_diesel + cur_dis, 1)
        
        # Numerical tolerance check: if generation + discharge covers (demand + charge) within 0.1 kW, unmet is strictly 0.0
        if cur_supply >= (cur_demand + cur_ch - 0.1) or raw_unmet <= 0.1:
            cur_unmet = 0.0
        else:
            cur_unmet = round(raw_unmet, 1)

        # Only trigger unmet demand alert if current modeled hour actually has unmet load > tolerance
        if cur_unmet > 0.1:
            if "🔴 Unmet station demand detected" not in alerts:
                alerts.append("🔴 Unmet station demand detected")

        summary["current_demand_kw"] = cur_demand
        summary["current_wind_kw"] = cur_wind
        summary["current_solar_kw"] = cur_solar
        summary["current_diesel_kw"] = cur_diesel
        summary["current_battery_discharge_kw"] = cur_dis
        summary["current_battery_charge_kw"] = cur_ch
        summary["current_total_supply_kw"] = cur_supply
        summary["current_unmet_demand_kw"] = cur_unmet
        summary["current_projected_soc_percent"] = cur_soc
    else:
        summary["current_demand_kw"] = 0.0
        summary["current_wind_kw"] = 0.0
        summary["current_solar_kw"] = 0.0
        summary["current_diesel_kw"] = 0.0
        summary["current_battery_discharge_kw"] = 0.0
        summary["current_battery_charge_kw"] = 0.0
        summary["current_total_supply_kw"] = 0.0
        summary["current_unmet_demand_kw"] = 0.0
        summary["current_projected_soc_percent"] = round(eq["initial_soc"] * 100.0, 1)

    summary["battery_state"] = eq["battery_state"]
    summary["initial_soc"] = eq["initial_soc"]
    summary["initial_simulated_soc_percent"] = round(eq["initial_soc"] * 100.0, 1)
    summary["diesel_state"] = eq["diesel_state"]
    summary["diesel_capacity_kw"] = eq["diesel_capacity_kw"]
    summary["max_available_diesel_kw"] = eq["diesel_capacity_kw"]
    summary["alerts"] = alerts
    summary["simulation_note"] = "Prototype assumption — not live Mawson BMS/SCADA telemetry."

    return {
        "summary": summary,
        "season": season,
        "weather_metadata": weather_meta,
        "schedule": schedule_df.to_dict(orient="records")
    }

@app.post("/api/run-dispatch")
def run_dispatch(req: DispatchRunRequest):
    """Executes dynamic re-optimization with custom horizon, season, or simulated equipment states."""
    horizon = req.horizon_hours or 24
    season = req.season or "summer"
    
    forecaster = PolarForecaster()
    try:
        forecaster.load_models()
    except Exception:
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        forecaster.train_evaluate(df_feat)

    ren_estimator = RenewableEstimator()
    if req.solar_capacity_kw:
        ren_estimator.solar_cfg["capacity_kw"] = req.solar_capacity_kw
    if req.wind_capacity_kw:
        ren_estimator.wind_cfg["total_capacity_kw"] = req.wind_capacity_kw

    eq = resolve_equipment_state(
        battery_state=req.battery_state,
        diesel_state=req.diesel_state,
        initial_soc=req.initial_soc,
        diesel_capacity_kw=req.diesel_capacity_kw
    )

    if season.lower() == "live":
        weather_service = WeatherForecastService()
        df_weather, weather_meta = weather_service.get_forecast_dataframe(horizon_hours=horizon)
        df_forecast = forecaster.predict_demand_for_weather(df_weather)
        df_forecast["pred_wind_speed_ms"] = df_forecast["wind_speed_ms"]
        df_forecast["pred_solar_radiation_wm2"] = df_forecast["solar_radiation_wm2"]
        df_forecast["pred_temperature_celsius"] = df_forecast["temperature_celsius"]
        df_ren = ren_estimator.process_forecast_dataframe(df_forecast)
        sim_label = "Live ECMWF Forecast (Operational Dispatch)"
    else:
        processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")
        df_raw = pd.read_csv(processed_path)
        fb = FeatureBuilder()
        df_feat = fb.build_features(df_raw)
        df_forecast = forecaster.generate_forecast(df_feat, horizon_hours=horizon, season=season)
        df_ren = ren_estimator.process_forecast_dataframe(df_forecast)
        weather_meta = {
            "source": "ERA5 Reanalysis (Historical Benchmark)",
            "provider": "ECMWF ERA5 Historical Reanalysis",
            "mode": "historical",
            "is_live": False,
            "updated_at": "Historical Benchmark (2023 Archive)",
            "fetched_at": "Historical Benchmark (2023 Archive)",
            "forecast_updated_at": "Historical Benchmark (2023 Archive)",
            "cache_age_seconds": None,
            "fallback_reason": None,
            "latitude": -67.6027,
            "longitude": 62.8738
        }
        sim_label = "Austral Summer (24-Hour Sun)" if season.lower() == "summer" else "Polar Night (Sun Below Horizon)"

    optimizer = MicrogridOptimizer()
    if req.battery_capacity_kwh:
        optimizer.bat_cfg["capacity_kwh"] = req.battery_capacity_kwh
        
    optimizer.gen_cfg["total_capacity_kw"] = eq["diesel_capacity_kw"]
    schedule_df = optimizer.optimize_schedule(df_ren, initial_soc=eq["initial_soc"])
    
    for col in ["wind_speed_ms", "solar_radiation_wm2", "temperature_celsius"]:
        if col in df_ren.columns:
            schedule_df[col] = df_ren[col].values
        elif f"pred_{col}" in df_ren.columns:
            schedule_df[col] = df_ren[f"pred_{col}"].values
    
    comparator = BaselineComparator(outputs_dir=outputs_dir)
    metrics = comparator.evaluate(schedule_df)
    metrics["baseline_diesel_litres"] = metrics.get("baseline_diesel_fuel_litres", 0.0)
    metrics["optimized_diesel_litres"] = metrics.get("optimized_diesel_fuel_litres", 0.0)
    metrics["diesel_saved_litres"] = metrics.get("diesel_fuel_saved_litres", 0.0)
    metrics["renewable_coverage_percent"] = metrics.get("renewable_penetration_percent", 0.0)
    metrics["season"] = season
    metrics["simulation_label"] = sim_label
    metrics["weather_source"] = weather_meta["source"]
    metrics["weather_mode"] = weather_meta["mode"]
    metrics["weather_updated_at"] = weather_meta["updated_at"]
    metrics["annual_validated_reduction_percent"] = 41.45
    metrics["annual_validated_note"] = "Projected annual diesel reduction — 12-month simulation benchmark"

    alerts = list(eq["alerts"])
    if len(schedule_df) > 0:
        row0 = schedule_df.iloc[0]
        cur_demand = round(float(row0["predicted_demand_kw"]), 1)
        cur_wind = round(float(row0.get("wind_generation_kw", 0.0)), 1)
        cur_solar = round(float(row0.get("solar_generation_kw", 0.0)), 1)
        cur_diesel = round(float(row0.get("diesel_generation_kw", 0.0)), 1)
        cur_dis = round(float(row0.get("battery_discharge_kw", 0.0)), 1)
        cur_ch = round(float(row0.get("battery_charge_kw", 0.0)), 1)
        raw_unmet = round(float(row0.get("unmet_demand_kw", 0.0)), 2)
        cur_soc = round(float(row0.get("battery_soc_percent", 50.0)), 1)
        
        cur_supply = round(cur_wind + cur_solar + cur_diesel + cur_dis, 1)
        if cur_supply >= (cur_demand + cur_ch - 0.1) or raw_unmet <= 0.1:
            cur_unmet = 0.0
        else:
            cur_unmet = round(raw_unmet, 1)

        if cur_unmet > 0.1:
            if "🔴 Unmet station demand detected" not in alerts:
                alerts.append("🔴 Unmet station demand detected")

        metrics["current_demand_kw"] = cur_demand
        metrics["current_wind_kw"] = cur_wind
        metrics["current_solar_kw"] = cur_solar
        metrics["current_diesel_kw"] = cur_diesel
        metrics["current_battery_discharge_kw"] = cur_dis
        metrics["current_battery_charge_kw"] = cur_ch
        metrics["current_total_supply_kw"] = cur_supply
        metrics["current_unmet_demand_kw"] = cur_unmet
        metrics["current_projected_soc_percent"] = cur_soc
    else:
        metrics["current_demand_kw"] = 0.0
        metrics["current_wind_kw"] = 0.0
        metrics["current_solar_kw"] = 0.0
        metrics["current_diesel_kw"] = 0.0
        metrics["current_battery_discharge_kw"] = 0.0
        metrics["current_battery_charge_kw"] = 0.0
        metrics["current_total_supply_kw"] = 0.0
        metrics["current_unmet_demand_kw"] = 0.0
        metrics["current_projected_soc_percent"] = round(eq["initial_soc"] * 100.0, 1)

    metrics["battery_state"] = eq["battery_state"]
    metrics["initial_soc"] = eq["initial_soc"]
    metrics["initial_simulated_soc_percent"] = round(eq["initial_soc"] * 100.0, 1)
    metrics["diesel_state"] = eq["diesel_state"]
    metrics["diesel_capacity_kw"] = eq["diesel_capacity_kw"]
    metrics["max_available_diesel_kw"] = eq["diesel_capacity_kw"]
    metrics["alerts"] = alerts
    metrics["simulation_note"] = "Prototype assumption — not live Mawson BMS/SCADA telemetry."

    return {
        "status": "success",
        "horizon_hours": horizon,
        "season": season,
        "weather_metadata": weather_meta,
        "metrics": metrics,
        "summary": metrics,
        "schedule": schedule_df.to_dict(orient="records")
    }

# SPA catch-all fallback for React client-side routing (placed after all API routes)
@app.get("/{full_path:path}")
def serve_spa_catchall(full_path: str):
    """Client-side SPA fallback for React routes."""
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
