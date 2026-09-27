"""
Polar Grid: Live Weather Forecast & Fallback Engine
Fetches hourly ECMWF IFS forecasts for Mawson Station (-67.6027, 62.8738) via Open-Meteo.
Provides robust local caching and transparent fallback to historical ERA5 data.
"""

import os
import json
import urllib.request
from datetime import datetime, timezone
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class WeatherForecastService:
    def __init__(self, lat: float = -67.6027, lon: float = 62.8738, cache_dir: str = None):
        self.lat = lat
        self.lon = lon
        if cache_dir is None:
            self.cache_dir = os.path.join(PROJECT_ROOT, "data", "processed")
        else:
            self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "latest_ecmwf_forecast.json")
        self.era5_file = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")

    def fetch_live_ecmwf(self, forecast_days: int = 4, timeout_sec: int = 8) -> dict:
        """
        Queries Open-Meteo's ECMWF endpoint for Mawson Station.
        Requests 6 parameters in standard scientific units:
        - temperature_2m (°C)
        - wind_speed_10m (m/s with &wind_speed_unit=ms)
        - wind_direction_10m (°)
        - shortwave_radiation (W/m²)
        - direct_normal_irradiance (W/m²)
        - diffuse_radiation (W/m²)
        """
        url = (
            f"https://api.open-meteo.com/v1/ecmwf?"
            f"latitude={self.lat}&longitude={self.lon}&"
            f"hourly=temperature_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_normal_irradiance,diffuse_radiation&"
            f"wind_speed_unit=ms&forecast_days={forecast_days}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PolarGrid-AntarcticMicrogrid/2.0 (Scientific SIH Prototype)"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode())
            
        h = data.get("hourly", {})
        times = h.get("time", [])
        if not times:
            raise ValueError("Empty hourly payload received from ECMWF endpoint.")
            
        # Standardize records
        points = []
        for i in range(len(times)):
            points.append({
                "timestamp": times[i],
                "temperature_celsius": round(float(h["temperature_2m"][i]), 2) if h["temperature_2m"][i] is not None else -10.0,
                "wind_speed_ms": max(0.0, round(float(h["wind_speed_10m"][i]), 2)) if h["wind_speed_10m"][i] is not None else 8.0,
                "wind_direction_deg": round(float(h["wind_direction_10m"][i]), 1) if h["wind_direction_10m"][i] is not None else 0.0,
                "solar_radiation_wm2": max(0.0, round(float(h["shortwave_radiation"][i]), 2)) if h["shortwave_radiation"][i] is not None else 0.0,
                "direct_radiation_wm2": max(0.0, round(float(h["direct_normal_irradiance"][i]), 2)) if h["direct_normal_irradiance"][i] is not None else 0.0,
                "diffuse_radiation_wm2": max(0.0, round(float(h["diffuse_radiation"][i]), 2)) if h["diffuse_radiation"][i] is not None else 0.0
            })
            
        now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
        payload = {
            "source": "ECMWF IFS",
            "provider": "Open-Meteo ECMWF Numerical Weather Prediction",
            "mode": "live",
            "is_live": True,
            "updated_at": now_str,
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(points),
            "points": points
        }
        
        # Save to local cache
        try:
            with open(self.cache_file, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to cache live forecast: {e}")
            
        return payload

    def get_weather_forecast(self, force_fallback: bool = False, horizon_hours: int = 72) -> dict:
        """
        Primary entry point.
        Attempts to fetch live ECMWF forecast.
        If network fails or force_fallback is True, gracefully falls back to:
        1. Cached successful ECMWF forecast, or
        2. Clean historical ERA5 reanalysis slice.
        """
        if not force_fallback:
            try:
                live_payload = self.fetch_live_ecmwf()
                live_payload["points"] = live_payload["points"][:horizon_hours]
                live_payload["forecast_hours"] = len(live_payload["points"])
                return live_payload
            except Exception as ex:
                print(f"Live ECMWF forecast unavailable ({ex}). Engaging fallback mechanism...")

        # 1. Attempt cached forecast
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cached = json.load(f)
                if cached.get("points") and len(cached["points"]) >= 24:
                    cached["mode"] = "fallback"
                    cached["is_live"] = False
                    cached["source"] = "ECMWF IFS (Cached)"
                    cached["fallback_reason"] = "Live API temporarily unavailable; using latest cached ECMWF forecast"
                    cached["points"] = cached["points"][:horizon_hours]
                    cached["forecast_hours"] = len(cached["points"])
                    return cached
            except Exception as e:
                print(f"Cached forecast read failed: {e}")

        # 2. Historical ERA5 fallback
        return self._build_era5_fallback(horizon_hours)

    def _build_era5_fallback(self, horizon_hours: int = 72) -> dict:
        """Builds fallback payload from stored ERA5 historical reanalysis."""
        if not os.path.exists(self.era5_file):
            raise FileNotFoundError(f"ERA5 reanalysis file missing at {self.era5_file}")
            
        df = pd.read_csv(self.era5_file)
        # Choose a representative summer slice (late December)
        slice_df = df.tail(horizon_hours).copy().reset_index(drop=True)
        
        points = []
        for _, row in slice_df.iterrows():
            points.append({
                "timestamp": str(row["timestamp"]),
                "temperature_celsius": round(float(row["temperature_celsius"]), 2),
                "wind_speed_ms": round(float(row["wind_speed_ms"]), 2),
                "wind_direction_deg": round(float(row.get("wind_direction_deg", 0.0)), 1),
                "solar_radiation_wm2": round(float(row["solar_radiation_wm2"]), 2),
                "direct_radiation_wm2": round(float(row.get("direct_radiation_wm2", 0.0)), 2),
                "diffuse_radiation_wm2": round(float(row.get("diffuse_radiation_wm2", 0.0)), 2)
            })
            
        return {
            "source": "ERA5 Reanalysis (Fallback)",
            "provider": "ECMWF ERA5 Historical Reanalysis",
            "mode": "fallback",
            "is_live": False,
            "updated_at": "Historical Benchmark (2023 Archive)",
            "fallback_reason": "Live weather endpoint offline; running verified ERA5 historical scenario",
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(points),
            "points": points
        }

    def get_forecast_dataframe(self, horizon_hours: int = 72, force_fallback: bool = False) -> tuple[pd.DataFrame, dict]:
        """
        Returns a DataFrame ready for the renewable generation model, along with metadata.
        """
        payload = self.get_weather_forecast(force_fallback=force_fallback, horizon_hours=horizon_hours)
        df = pd.DataFrame(payload["points"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df, {
            "source": payload["source"],
            "mode": payload["mode"],
            "is_live": payload["is_live"],
            "updated_at": payload["updated_at"],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"]
        }

if __name__ == "__main__":
    service = WeatherForecastService()
    print("Testing live fetch...")
    res = service.get_weather_forecast(horizon_hours=24)
    print(f"Source: {res['source']}, Mode: {res['mode']}, Updated: {res['updated_at']}, Points: {len(res['points'])}")
    print("First point:", res['points'][0])
