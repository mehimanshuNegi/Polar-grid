"""
Polar Grid: Live Weather Forecast & Fallback Engine
Fetches hourly ECMWF IFS forecasts for Mawson Station (-67.6027, 62.8738) via Open-Meteo.
Provides robust server-side caching (15-min TTL), single-flight request deduplication,
and transparent fallback to cached ECMWF / historical ERA5 data on HTTP 429 or network failures.
"""

import os
import json
import time
import copy
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Shared in-memory cache across all service instances and API endpoints
_GLOBAL_WEATHER_CACHE = {
    "payload": None,
    "fetched_at": 0.0,
}
_CACHE_TTL_SECONDS = 900.0  # 15 minutes cache lifetime (approx 10-15 minutes)
_FETCH_LOCK = threading.Lock()


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

    @classmethod
    def clear_in_memory_cache(cls):
        """Clears server in-memory cache (for testing/diagnostics)."""
        with _FETCH_LOCK:
            _GLOBAL_WEATHER_CACHE["payload"] = None
            _GLOBAL_WEATHER_CACHE["fetched_at"] = 0.0

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
        
        # Save to local persistent disk cache
        try:
            with open(self.cache_file, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to cache live forecast to disk: {e}")
            
        return payload

    def get_weather_forecast(self, force_fallback: bool = False, horizon_hours: int = 72) -> dict:
        """
        Primary entry point.
        Checks shared in-memory server cache (15-min TTL).
        If cache is empty/expired, coalesces simultaneous calls with a lock so only
        ONE network request is sent to Open-Meteo.
        If Open-Meteo returns HTTP 429 or fails, automatically falls back to:
        1. Cached ECMWF forecast (mode: 'cached', is_live: False)
        2. Historical ERA5 reanalysis (mode: 'historical_fallback', is_live: False)
        """
        now = time.time()

        # 1. Fast read path from in-memory cache
        if not force_fallback:
            cached_live = _GLOBAL_WEATHER_CACHE.get("payload")
            fetched_at = _GLOBAL_WEATHER_CACHE.get("fetched_at", 0.0)
            if cached_live is not None and (now - fetched_at) < _CACHE_TTL_SECONDS:
                res = copy.deepcopy(cached_live)
                res["points"] = res["points"][:horizon_hours]
                res["forecast_hours"] = len(res["points"])
                return res

        # 2. Synchronized fetch path: only ONE thread fetches while others wait
        with _FETCH_LOCK:
            now = time.time()
            # Double-check if another thread just populated the cache while we waited for the lock
            if not force_fallback:
                cached_live = _GLOBAL_WEATHER_CACHE.get("payload")
                fetched_at = _GLOBAL_WEATHER_CACHE.get("fetched_at", 0.0)
                if cached_live is not None and (now - fetched_at) < _CACHE_TTL_SECONDS:
                    res = copy.deepcopy(cached_live)
                    res["points"] = res["points"][:horizon_hours]
                    res["forecast_hours"] = len(res["points"])
                    return res

                # Call Open-Meteo live endpoint
                try:
                    live_payload = self.fetch_live_ecmwf()
                    _GLOBAL_WEATHER_CACHE["payload"] = live_payload
                    _GLOBAL_WEATHER_CACHE["fetched_at"] = time.time()
                    
                    res = copy.deepcopy(live_payload)
                    res["points"] = res["points"][:horizon_hours]
                    res["forecast_hours"] = len(res["points"])
                    return res
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 429:
                        print(f"[RateLimit] Open-Meteo returned HTTP 429 Too Many Requests. Engaging cached forecast fallback.")
                    else:
                        print(f"[HTTPError] Open-Meteo returned HTTP {http_err.code}: {http_err}. Engaging cached forecast fallback.")
                except Exception as ex:
                    print(f"[Network] Live ECMWF forecast unavailable ({ex}). Engaging fallback mechanism...")

            # 3. Fallback path (HTTP 429, network failure, or force_fallback=True)
            # Try disk cache first
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, "r") as f:
                        cached = json.load(f)
                    if cached.get("points") and len(cached["points"]) >= 24:
                        cached["mode"] = "cached"
                        cached["is_live"] = False
                        cached["source"] = "ECMWF IFS (Cached)"
                        cached["fallback_reason"] = "Live API rate-limited (HTTP 429) or offline; using latest cached ECMWF forecast"
                        cached["points"] = cached["points"][:horizon_hours]
                        cached["forecast_hours"] = len(cached["points"])
                        
                        # Populate in-memory cache with fallback data for 5 minutes to prevent immediate retry storms
                        if not force_fallback:
                            _GLOBAL_WEATHER_CACHE["payload"] = copy.deepcopy(cached)
                            _GLOBAL_WEATHER_CACHE["fetched_at"] = time.time() - (_CACHE_TTL_SECONDS - 300.0)

                        return cached
                except Exception as e:
                    print(f"Cached forecast read failed: {e}")

            # 4. Historical ERA5 fallback if no cached ECMWF forecast exists
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
            "mode": "historical_fallback",
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

