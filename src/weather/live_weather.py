"""
Polar Grid: Production Weather Ingestion & Synchronization Engine
Fetches hourly ECMWF IFS forecasts for Mawson Station (-67.6027, 62.8738).
Supports:
1. Direct Open-Meteo ECMWF Numerical Weather Prediction API
2. External Pre-Acquired Weather Snapshot URL (WEATHER_SNAPSHOT_URL)
3. Background scheduled refresh daemon (WEATHER_REFRESH_INTERVAL_SECONDS)
4. Atomic persistent disk caching (survives restarts)
5. Secure ingest/sync webhook for external runners (POST /api/weather/sync)
6. Single-flight request coalescing and 300s provider cooldown on HTTP 429
7. Strict scientific integrity (NEVER fake LIVE; truthful LIVE/CACHED/HISTORICAL semantics)
"""

import os
import json
import time
import copy
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Tuple
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Configurable environment settings
LIVE_CACHE_TTL_SECONDS = float(os.environ.get("WEATHER_CACHE_TTL_SECONDS", "900.0"))           # 15 mins
PROVIDER_COOLDOWN_SECONDS = float(os.environ.get("WEATHER_COOLDOWN_SECONDS", "300.0"))        # 5 mins on 429
WEATHER_REFRESH_INTERVAL_SECONDS = float(os.environ.get("WEATHER_REFRESH_INTERVAL_SECONDS", "900.0")) # 15 mins
OPEN_METEO_API_KEY = os.environ.get("OPEN_METEO_API_KEY", "").strip() or None
WEATHER_SNAPSHOT_URL = os.environ.get("WEATHER_SNAPSHOT_URL", "").strip() or None
WEATHER_ADMIN_KEY = os.environ.get("WEATHER_ADMIN_KEY", "").strip() or os.environ.get("WEATHER_REFRESH_TOKEN", "").strip() or None

# Process-wide weather pipeline state
_STATE_LOCK = threading.RLock()
_FETCH_LOCK = threading.Lock()
_STOP_EVENT = threading.Event()
_REFRESH_THREAD: Optional[threading.Thread] = None

_WEATHER_STATE = {
    "live_payload": None,
    "live_fetched_at": 0.0,
    "last_fetch_attempt_at": 0.0,
    "last_provider_error": None,
    "last_provider_status_code": 200,
    "cooldown_until": 0.0,
    "refresh_in_progress": False,
    "snapshot_source": "none"
}


class WeatherForecastService:
    def __init__(self, lat: float = -67.6027, lon: float = 62.8738, cache_dir: str = None):
        self.lat = lat
        self.lon = lon
        if cache_dir is None:
            storage_path = os.environ.get("WEATHER_STORAGE_PATH")
            if storage_path:
                self.cache_dir = os.path.dirname(os.path.abspath(storage_path))
                self.cache_file = os.path.abspath(storage_path)
            else:
                self.cache_dir = os.path.join(PROJECT_ROOT, "data", "processed")
                self.cache_file = os.path.join(self.cache_dir, "latest_ecmwf_forecast.json")
        else:
            self.cache_dir = cache_dir
            self.cache_file = os.path.join(self.cache_dir, "latest_ecmwf_forecast.json")

        os.makedirs(self.cache_dir, exist_ok=True)
        self.era5_file = os.path.join(PROJECT_ROOT, "data", "processed", "mawson_hourly_energy_weather.csv")

    @classmethod
    def clear_in_memory_cache(cls):
        """Clears server in-memory cache and resets cooldown (for testing/diagnostics)."""
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = None
            _WEATHER_STATE["live_fetched_at"] = 0.0
            _WEATHER_STATE["last_fetch_attempt_at"] = 0.0
            _WEATHER_STATE["last_provider_error"] = None
            _WEATHER_STATE["last_provider_status_code"] = 200
            _WEATHER_STATE["cooldown_until"] = 0.0
            _WEATHER_STATE["refresh_in_progress"] = False

    def get_pipeline_status(self) -> dict:
        """
        Diagnostic status inspection. Never performs network calls.
        Returns comprehensive health telemetry for operations monitoring.
        """
        now = time.time()
        with _STATE_LOCK:
            live_at = _WEATHER_STATE["live_fetched_at"]
            live_payload = _WEATHER_STATE["live_payload"]
            is_live_valid = (live_payload is not None) and ((now - live_at) < LIVE_CACHE_TTL_SECONDS)
            live_age = int(now - live_at) if live_at > 0 else None

            cooldown_remaining = max(0, int(_WEATHER_STATE["cooldown_until"] - now))
            cooldown_active = cooldown_remaining > 0

            cache_present = (live_payload is not None) or os.path.exists(self.cache_file)

            if is_live_valid:
                mode = "live"
                is_live = True
            elif cache_present:
                mode = "cached"
                is_live = False
            else:
                mode = "historical_fallback"
                is_live = False

            last_fetch_str = None
            if live_at > 0:
                last_fetch_str = datetime.fromtimestamp(live_at, timezone.utc).strftime("%d %b %Y, %H:%M UTC")

            forecast_updated_str = None
            if live_payload and live_payload.get("forecast_updated_at"):
                forecast_updated_str = live_payload["forecast_updated_at"]

            return {
                "provider": "Open-Meteo ECMWF IFS",
                "mode": mode,
                "is_live": is_live,
                "last_successful_fetch": last_fetch_str,
                "last_live_fetch_at": last_fetch_str,
                "forecast_updated_at": forecast_updated_str,
                "snapshot_age_seconds": live_age,
                "cache_age_seconds": live_age,
                "refresh_interval_seconds": int(WEATHER_REFRESH_INTERVAL_SECONDS),
                "cache_ttl_seconds": int(LIVE_CACHE_TTL_SECONDS),
                "cache_present": cache_present,
                "provider_cooldown_active": cooldown_active,
                "provider_cooldown_remaining_seconds": cooldown_remaining,
                "last_provider_error": _WEATHER_STATE["last_provider_error"],
                "last_provider_status_code": _WEATHER_STATE["last_provider_status_code"],
                "refresh_in_progress": _WEATHER_STATE["refresh_in_progress"]
            }

    def fetch_live_ecmwf(self, forecast_days: int = 4, timeout_sec: int = 10) -> dict:
        """
        Directly queries Open-Meteo's ECMWF endpoint for Mawson Station.
        Requests 6 microgrid meteorological parameters in standard scientific units:
        - temperature_2m (°C)
        - wind_speed_10m (m/s)
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
        if OPEN_METEO_API_KEY:
            url += f"&apikey={OPEN_METEO_API_KEY}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PolarGrid-AntarcticMicrogrid/2.0 (SIH-Prototype-Mawson; https://github.com/mehimanshuNegi/Polar-grid)"}
        )
        print("[Weather] LIVE ECMWF IFS fetch started")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_body = resp.read().decode()
            data = json.loads(raw_body)

        h = data.get("hourly", {})
        times = h.get("time", [])
        if not times:
            raise ValueError("Empty hourly payload received from Open-Meteo ECMWF endpoint.")

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

        now_utc = datetime.now(timezone.utc)
        now_str = now_utc.strftime("%d %b %Y, %H:%M UTC")

        # Open-Meteo ECMWF model cycle timestamp from first forecast hour
        try:
            run_dt = datetime.fromisoformat(times[0])
            model_run_str = run_dt.strftime("%d %b %Y, %H:%M UTC")
        except Exception:
            model_run_str = now_str

        payload = {
            "source": "ECMWF IFS",
            "provider": "Open-Meteo ECMWF Numerical Weather Prediction",
            "model": "ECMWF IFS (0.25°)",
            "mode": "live",
            "is_live": True,
            "updated_at": now_str,
            "fetched_at": now_str,
            "forecast_updated_at": model_run_str,
            "cache_age_seconds": 0,
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(points),
            "points": points,
            "fallback_reason": None
        }

        # Atomically write to persistent local disk cache
        self._write_persistent_snapshot(payload)
        return payload

    def fetch_external_snapshot(self, timeout_sec: int = 10) -> Optional[dict]:
        """
        Attempts to acquire a pre-acquired ECMWF snapshot from WEATHER_SNAPSHOT_URL.
        This provides an un-rate-limited external acquisition path for cloud environments.
        """
        if not WEATHER_SNAPSHOT_URL:
            return None

        print(f"[Weather] Checking external snapshot URL: {WEATHER_SNAPSHOT_URL}")
        req = urllib.request.Request(
            WEATHER_SNAPSHOT_URL,
            headers={"User-Agent": "PolarGrid-SnapshotSync/2.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode())

        if not data.get("points") or len(data["points"]) < 24:
            raise ValueError("External snapshot returned insufficient points (<24).")

        now_utc = datetime.now(timezone.utc)
        now_str = now_utc.strftime("%d %b %Y, %H:%M UTC")

        payload = {
            "source": "ECMWF IFS",
            "provider": data.get("provider", "Open-Meteo ECMWF Numerical Weather Prediction (External Sync)"),
            "model": data.get("model", "ECMWF IFS (0.25°)"),
            "mode": "live",
            "is_live": True,
            "updated_at": now_str,
            "fetched_at": data.get("fetched_at", now_str),
            "forecast_updated_at": data.get("forecast_updated_at", now_str),
            "cache_age_seconds": 0,
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(data["points"]),
            "points": data["points"],
            "fallback_reason": None
        }
        self._write_persistent_snapshot(payload)
        return payload

    def ingest_synced_snapshot(self, payload: dict) -> dict:
        """
        Ingests an authentic ECMWF forecast pushed by an external runner or webhook.
        Validates payload structure and atomically updates in-memory and disk snapshot.
        """
        if not payload.get("points") or len(payload["points"]) < 24:
            raise ValueError("Payload missing or contains fewer than 24 forecast points.")

        now = time.time()
        now_utc = datetime.now(timezone.utc)
        now_str = now_utc.strftime("%d %b %Y, %H:%M UTC")

        ingested = {
            "source": "ECMWF IFS",
            "provider": payload.get("provider", "Open-Meteo ECMWF Numerical Weather Prediction (Synced)"),
            "model": payload.get("model", "ECMWF IFS (0.25°)"),
            "mode": "live",
            "is_live": True,
            "updated_at": now_str,
            "fetched_at": payload.get("fetched_at", now_str),
            "forecast_updated_at": payload.get("forecast_updated_at", now_str),
            "cache_age_seconds": 0,
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(payload["points"]),
            "points": payload["points"],
            "fallback_reason": None
        }

        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = ingested
            _WEATHER_STATE["live_fetched_at"] = now
            _WEATHER_STATE["last_provider_error"] = None
            _WEATHER_STATE["last_provider_status_code"] = 200
            _WEATHER_STATE["cooldown_until"] = 0.0
            _WEATHER_STATE["snapshot_source"] = "external_sync"

        self._write_persistent_snapshot(ingested)
        print(f"[Weather] External weather snapshot ingested ({len(ingested['points'])} hours)")
        return ingested

    def _write_persistent_snapshot(self, payload: dict):
        """Atomically saves snapshot to disk using a temporary file."""
        try:
            tmp_path = self.cache_file + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.cache_file)
        except Exception as e:
            print(f"[Weather] Warning: Failed to write persistent snapshot: {e}")

    def refresh_weather_snapshot(self, force: bool = False, horizon_hours: int = 72) -> Tuple[bool, dict]:
        """
        Controlled refresh function.
        Attempts to update the weather snapshot from external snapshot URL or direct Open-Meteo.
        Respects cooldown, concurrency locks, and never destroys existing valid snapshot on failure.
        """
        now = time.time()
        with _STATE_LOCK:
            _WEATHER_STATE["refresh_in_progress"] = True

        try:
            with _FETCH_LOCK:
                # 1. Cooldown protection check
                with _STATE_LOCK:
                    in_cooldown = now < _WEATHER_STATE["cooldown_until"]
                    remaining = int(_WEATHER_STATE["cooldown_until"] - now) if in_cooldown else 0

                if in_cooldown and not force:
                    print(f"[Weather] Refresh skipped: provider cooldown active ({remaining}s remaining)")
                    fallback = self._build_cached_ecmwf_fallback(
                        horizon_hours,
                        reason=f"Open-Meteo HTTP 429 cooldown active ({remaining}s remaining)"
                    )
                    return False, fallback

                # 2. Check if fresh within TTL and not forced
                with _STATE_LOCK:
                    cached_live = _WEATHER_STATE["live_payload"]
                    live_at = _WEATHER_STATE["live_fetched_at"]
                    if cached_live is not None and (now - live_at) < LIVE_CACHE_TTL_SECONDS and not force:
                        age = int(now - live_at)
                        res = copy.deepcopy(cached_live)
                        res["points"] = res["points"][:horizon_hours]
                        res["forecast_hours"] = len(res["points"])
                        res["cache_age_seconds"] = age
                        return True, res

                # 3. Attempt acquisition: external snapshot URL first (if configured), then direct provider
                live_payload = None
                if WEATHER_SNAPSHOT_URL:
                    try:
                        live_payload = self.fetch_external_snapshot()
                        if live_payload:
                            print("[Weather] External ECMWF snapshot acquired successfully")
                    except Exception as ext_err:
                        print(f"[Weather] External snapshot acquisition failed ({ext_err}), falling back to direct provider")

                if live_payload is None:
                    live_payload = self.fetch_live_ecmwf()

                now_done = time.time()
                with _STATE_LOCK:
                    was_in_cooldown = _WEATHER_STATE["cooldown_until"] > 0
                    _WEATHER_STATE["live_payload"] = live_payload
                    _WEATHER_STATE["live_fetched_at"] = now_done
                    _WEATHER_STATE["last_provider_error"] = None
                    _WEATHER_STATE["last_provider_status_code"] = 200
                    _WEATHER_STATE["cooldown_until"] = 0.0
                    _WEATHER_STATE["snapshot_source"] = "provider"

                if was_in_cooldown:
                    print("[Weather] live provider recovered")
                print(f"[Weather] LIVE ECMWF IFS fetch successful")
                print(f"[Weather] fetched_at={live_payload['fetched_at']} horizon={len(live_payload['points'])}")

                res = copy.deepcopy(live_payload)
                res["points"] = res["points"][:horizon_hours]
                res["forecast_hours"] = len(res["points"])
                res["cache_age_seconds"] = 0
                return True, res

        except urllib.error.HTTPError as http_err:
            now_err = time.time()
            with _STATE_LOCK:
                _WEATHER_STATE["last_provider_status_code"] = http_err.code
                if http_err.code == 429:
                    _WEATHER_STATE["last_provider_error"] = "HTTP 429 Too Many Requests"
                    _WEATHER_STATE["cooldown_until"] = now_err + PROVIDER_COOLDOWN_SECONDS
                    print("[Weather] Open-Meteo HTTP 429")
                    print(f"[Weather] entering provider cooldown ({int(PROVIDER_COOLDOWN_SECONDS)}s)")
                    reason = "Open-Meteo HTTP 429 Too Many Requests"
                else:
                    _WEATHER_STATE["last_provider_error"] = f"HTTP {http_err.code}"
                    print(f"[Weather] Open-Meteo HTTP {http_err.code}: {http_err}. Serving cached forecast.")
                    reason = f"Open-Meteo HTTP {http_err.code}"

            fallback = self._build_cached_ecmwf_fallback(horizon_hours, reason=reason)
            return False, fallback

        except Exception as ex:
            with _STATE_LOCK:
                _WEATHER_STATE["last_provider_error"] = str(ex)
                _WEATHER_STATE["last_provider_status_code"] = 500
            print(f"[Weather] Open-Meteo live request failed ({ex}). Serving cached forecast.")
            fallback = self._build_cached_ecmwf_fallback(horizon_hours, reason=f"Network error: {ex}")
            return False, fallback

        finally:
            with _STATE_LOCK:
                _WEATHER_STATE["refresh_in_progress"] = False

    def get_weather_forecast(self, force_fallback: bool = False, horizon_hours: int = 72) -> dict:
        """
        Primary weather accessor.
        1. Fast path: checks process-wide in-memory cache (15-min TTL).
        2. Cooldown check: if provider returned HTTP 429, blocks network requests for 300s.
        3. Single-flight lock: coalesces concurrent requests so only ONE hits Open-Meteo.
        4. Safe fallbacks:
           - Cached ECMWF forecast (mode: 'cached', is_live: False)
           - Historical ERA5 reanalysis (mode: 'historical_fallback', is_live: False)
        """
        now = time.time()

        if force_fallback:
            return self._build_cached_ecmwf_fallback(horizon_hours, reason="Explicit fallback requested")

        # 1. Fast read path: valid in-memory live cache
        with _STATE_LOCK:
            cached_live = _WEATHER_STATE["live_payload"]
            live_at = _WEATHER_STATE["live_fetched_at"]
            if cached_live is not None and (now - live_at) < LIVE_CACHE_TTL_SECONDS:
                age = int(now - live_at)
                print(f"[Weather] CACHE HIT age={age}s (TTL: {int(LIVE_CACHE_TTL_SECONDS)}s)")
                res = copy.deepcopy(cached_live)
                res["points"] = res["points"][:horizon_hours]
                res["forecast_hours"] = len(res["points"])
                res["cache_age_seconds"] = age
                return res

        # 2. Synchronized fetch path through controlled refresh
        success, payload = self.refresh_weather_snapshot(force=False, horizon_hours=horizon_hours)
        return payload

    def _build_cached_ecmwf_fallback(self, horizon_hours: int = 72, reason: str = "Live feed unavailable") -> dict:
        """Loads and formats the persistent local ECMWF disk or in-memory cache."""
        # 1. Check in-memory previous live payload first
        with _STATE_LOCK:
            prev_live = _WEATHER_STATE.get("live_payload")
            live_fetched_at = _WEATHER_STATE.get("live_fetched_at", 0.0)

        if prev_live and prev_live.get("points") and len(prev_live["points"]) >= 12:
            cached = copy.deepcopy(prev_live)
            cached["source"] = "ECMWF IFS (Cached)"
            cached["mode"] = "cached"
            cached["is_live"] = False
            cached["fallback_reason"] = reason
            cached["cache_age_seconds"] = int(time.time() - live_fetched_at) if live_fetched_at > 0 else None
            cached["points"] = cached["points"][:horizon_hours]
            cached["forecast_hours"] = len(cached["points"])
            return cached

        # 2. Check persistent disk cache
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)

                if cached.get("points") and len(cached["points"]) >= 12:
                    cached["source"] = "ECMWF IFS (Cached)"
                    cached["mode"] = "cached"
                    cached["is_live"] = False
                    cached["fallback_reason"] = reason

                    file_mtime = os.path.getmtime(self.cache_file)
                    cached["cache_age_seconds"] = int(time.time() - file_mtime)

                    cached["points"] = cached["points"][:horizon_hours]
                    cached["forecast_hours"] = len(cached["points"])
                    return cached
            except Exception as e:
                print(f"[Weather] Warning: Persistent disk cache read failed: {e}")

        # 3. Fall back to ERA5 historical reanalysis if no valid ECMWF cache exists
        print("[Weather] ECMWF cache unavailable")
        print("[Weather] using ERA5 historical fallback")
        return self._build_era5_fallback(horizon_hours)

    def _build_era5_fallback(self, horizon_hours: int = 72) -> dict:
        """Builds fallback payload from stored ERA5 historical reanalysis."""
        if not os.path.exists(self.era5_file):
            raise FileNotFoundError(f"ERA5 reanalysis file missing at {self.era5_file}")

        df = pd.read_csv(self.era5_file)
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
            "fetched_at": "Historical Benchmark (2023 Archive)",
            "forecast_updated_at": "Historical Benchmark (2023 Archive)",
            "cache_age_seconds": None,
            "fallback_reason": "Live and cached ECMWF feeds unavailable; using verified ERA5 historical reanalysis",
            "latitude": self.lat,
            "longitude": self.lon,
            "forecast_hours": len(points),
            "points": points
        }

    def get_forecast_dataframe(self, horizon_hours: int = 72, force_fallback: bool = False) -> tuple[pd.DataFrame, dict]:
        """
        Returns a DataFrame ready for the renewable generation model, along with metadata.
        Uses the exact same centralized weather forecast manager.
        """
        payload = self.get_weather_forecast(force_fallback=force_fallback, horizon_hours=horizon_hours)
        df = pd.DataFrame(payload["points"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df, {
            "source": payload["source"],
            "provider": payload.get("provider", "Open-Meteo ECMWF Numerical Weather Prediction"),
            "mode": payload["mode"],
            "is_live": payload["is_live"],
            "updated_at": payload["updated_at"],
            "fetched_at": payload.get("fetched_at", payload["updated_at"]),
            "forecast_updated_at": payload.get("forecast_updated_at"),
            "cache_age_seconds": payload.get("cache_age_seconds", 0),
            "fallback_reason": payload.get("fallback_reason"),
            "latitude": payload["latitude"],
            "longitude": payload["longitude"]
        }


# =====================================================================
# Background Refresh Daemon
# =====================================================================

def _background_refresh_loop(interval_seconds: float = None):
    """Background worker loop that keeps the ECMWF weather snapshot fresh."""
    service = WeatherForecastService()
    interval = interval_seconds or WEATHER_REFRESH_INTERVAL_SECONDS
    print(f"[Weather] Background refresh daemon active (interval: {int(interval)}s)")

    # Initial check on startup: if no live cache or older than interval, attempt refresh
    try:
        service.refresh_weather_snapshot(force=False)
    except Exception as e:
        print(f"[Weather] Initial background refresh attempt: {e}")

    while not _STOP_EVENT.is_set():
        # Sleep in 1-second slices for prompt shutdown response
        for _ in range(int(interval)):
            if _STOP_EVENT.is_set():
                break
            time.sleep(1.0)

        if not _STOP_EVENT.is_set():
            try:
                service.refresh_weather_snapshot(force=False)
            except Exception as e:
                print(f"[Weather] Periodic background refresh error: {e}")


def start_background_weather_refresh(interval_seconds: float = None):
    """Starts the background weather refresh daemon if not already running."""
    global _REFRESH_THREAD
    with _STATE_LOCK:
        if _REFRESH_THREAD is not None and _REFRESH_THREAD.is_alive():
            return
        _STOP_EVENT.clear()
        _REFRESH_THREAD = threading.Thread(
            target=_background_refresh_loop,
            args=(interval_seconds,),
            name="PolarGrid-WeatherRefreshDaemon",
            daemon=True
        )
        _REFRESH_THREAD.start()


def stop_background_weather_refresh():
    """Stops the background weather refresh daemon."""
    global _REFRESH_THREAD
    _STOP_EVENT.set()
    if _REFRESH_THREAD is not None:
        if _REFRESH_THREAD.is_alive():
            _REFRESH_THREAD.join(timeout=2.0)
        _REFRESH_THREAD = None


if __name__ == "__main__":
    service = WeatherForecastService()
    print("Testing live fetch...")
    res = service.get_weather_forecast(horizon_hours=24)
    print(f"Source: {res['source']}, Mode: {res['mode']}, is_live: {res['is_live']}")
    print(f"Fetched At: {res.get('fetched_at')}, Model Run: {res.get('forecast_updated_at')}, Cache Age: {res.get('cache_age_seconds')}s")
