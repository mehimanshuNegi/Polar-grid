import os
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

# Test the current formulation vs an improved formulation
def run_test():
    with open("config/station_config.json") as f:
        cfg = json.load(f)

    # Let's get live weather forecast
    import sys
    sys.path.insert(0, ".")
    from src.weather.forecast_service import WeatherForecastService
    from src.forecasting.forecaster import PolarForecaster
    from src.renewable.estimator import RenewableEstimator

    ws = WeatherForecastService()
    df_weather, _ = ws.get_forecast_dataframe(horizon_hours=24)
    fc = PolarForecaster()
    try:
        fc.load_models()
    except Exception:
        pass
    df_f = fc.predict_demand_for_weather(df_weather)
    df_f["pred_wind_speed_ms"] = df_f["wind_speed_ms"]
    df_f["pred_solar_radiation_wm2"] = df_f["solar_radiation_wm2"]
    df_f["pred_temperature_celsius"] = df_f["temperature_celsius"]
    re = RenewableEstimator()
    df_ren = re.process_forecast_dataframe(df_f)

    print("Hours demand:", df_ren["pred_modeled_demand_kw"].values[:6])
    print("Hours solar: ", df_ren["solar_generation_kw"].values[:6])
    print("Hours wind:  ", df_ren["wind_generation_kw"].values[:6])

if __name__ == "__main__":
    run_test()
