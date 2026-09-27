"""
Polar Grid: External Weather Acquisition Runner
Acquires genuine ECMWF IFS numerical weather forecasts directly from Open-Meteo
for Mawson Station (-67.6027, 62.8738).

Can be executed:
1. Locally on developer machine
2. In GitHub Actions (on scheduled cron or workflow_dispatch)
3. On an external server or cron worker

Can save locally and/or push directly to a deployed Polar Grid instance:
  python src/weather/acquire_weather.py --push-to https://polar-grid.onrender.com --token <SECRET>
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_LAT = -67.6027
DEFAULT_LON = 62.8738
DEFAULT_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "latest_ecmwf_forecast.json")


def fetch_ecmwf_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, forecast_days: int = 4, api_key: str = None) -> dict:
    """Queries Open-Meteo ECMWF Numerical Weather Prediction API."""
    url = (
        f"https://api.open-meteo.com/v1/ecmwf?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=temperature_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_normal_irradiance,diffuse_radiation&"
        f"wind_speed_unit=ms&forecast_days={forecast_days}"
    )
    if api_key:
        url += f"&apikey={api_key}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PolarGrid-ExternalAcquisitionRunner/2.0 (Mawson Station Microgrid Research)"}
    )
    print(f"[Acquisition] Fetching ECMWF forecast from {url[:60]}...")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    h = data.get("hourly", {})
    times = h.get("time", [])
    if not times:
        raise ValueError("Empty hourly payload received from Open-Meteo.")

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
        "latitude": lat,
        "longitude": lon,
        "forecast_hours": len(points),
        "points": points,
        "fallback_reason": None
    }
    return payload


def save_snapshot(payload: dict, output_path: str):
    """Saves snapshot atomically to disk."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, output_path)
    print(f"[Acquisition] Snapshot saved successfully to {output_path} ({len(payload['points'])} hours)")


def push_to_remote(payload: dict, target_url: str, token: str = None):
    """Pushes the acquired snapshot to a deployed Polar Grid API endpoint."""
    sync_url = target_url.rstrip("/") + "/api/weather/sync"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PolarGrid-ExternalAcquisitionRunner/2.0"
    }
    if token:
        headers["X-Admin-Key"] = token

    req = urllib.request.Request(sync_url, data=body, headers=headers, method="POST")
    print(f"[Acquisition] Pushing snapshot to {sync_url}...")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_body = json.loads(resp.read().decode())
            print(f"[Acquisition] Push successful! Response: {resp_body}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()[:200]
        print(f"[Acquisition] Push failed: HTTP {e.code}: {err_msg}")
        return False
    except Exception as e:
        print(f"[Acquisition] Push failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Acquire ECMWF weather forecast for Polar Grid")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to save output JSON")
    parser.add_argument("--push-to", default=None, help="Base URL of deployed Polar Grid instance (e.g. https://polar-grid.onrender.com)")
    parser.add_argument("--token", default=os.environ.get("WEATHER_ADMIN_KEY"), help="Admin token for remote sync")
    parser.add_argument("--api-key", default=os.environ.get("OPEN_METEO_API_KEY"), help="Optional Open-Meteo API key")
    args = parser.parse_args()

    try:
        payload = fetch_ecmwf_forecast(api_key=args.api_key)
        save_snapshot(payload, args.output)

        if args.push_to:
            push_to_remote(payload, args.push_to, token=args.token)

    except Exception as e:
        print(f"[Acquisition] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
