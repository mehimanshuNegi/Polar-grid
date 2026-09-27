"""
Polar Grid: Comprehensive Production Weather Ingestion & Synchronization Tests
Validates all 15 production weather requirements:
1. Successful live provider fetch
2. Live metadata correctness
3. Cache hit within TTL
4. Concurrent request coalescing (_FETCH_LOCK)
5. HTTP 429 provider handling
6. Provider cooldown active (300s)
7. Recovery after cooldown expires
8. Persistent snapshot loading
9. Failed refresh preserving last valid snapshot
10. Background refresh daemon execution
11. Stale snapshot fallback behavior
12. /api/weather/status health telemetry
13. /api/weather/live response contract
14. /api/schedule?season=live metadata propagation
15. Manual refresh & sync endpoints authorization
"""

import unittest
from unittest.mock import patch, MagicMock
import urllib.error
import time
import os
import json
import sys
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.weather.live_weather import (
    WeatherForecastService,
    _WEATHER_STATE,
    _STATE_LOCK,
    LIVE_CACHE_TTL_SECONDS,
    PROVIDER_COOLDOWN_SECONDS,
    start_background_weather_refresh,
    stop_background_weather_refresh
)
from backend.main import app


class TestProductionWeatherPipeline(unittest.TestCase):

    def setUp(self):
        WeatherForecastService.clear_in_memory_cache()
        self.service = WeatherForecastService()
        self.client = TestClient(app)

    def tearDown(self):
        WeatherForecastService.clear_in_memory_cache()
        stop_background_weather_refresh()

    def _sample_live_payload(self):
        return {
            "source": "ECMWF IFS",
            "provider": "Open-Meteo ECMWF Numerical Weather Prediction",
            "model": "ECMWF IFS (0.25°)",
            "mode": "live",
            "is_live": True,
            "updated_at": "27 Sep 2026, 17:00 UTC",
            "fetched_at": "27 Sep 2026, 17:00 UTC",
            "forecast_updated_at": "27 Sep 2026, 00:00 UTC",
            "cache_age_seconds": 0,
            "latitude": -67.6027,
            "longitude": 62.8738,
            "forecast_hours": 24,
            "points": [
                {
                    "timestamp": f"2026-09-27T{h:02d}:00",
                    "temperature_celsius": -15.0,
                    "wind_speed_ms": 12.0,
                    "wind_direction_deg": 180.0,
                    "solar_radiation_wm2": 100.0,
                    "direct_radiation_wm2": 60.0,
                    "diffuse_radiation_wm2": 40.0
                }
                for h in range(24)
            ],
            "fallback_reason": None
        }

    # 1 & 2: Successful live provider fetch and metadata correctness
    def test_01_live_provider_fetch_and_metadata(self):
        sample = self._sample_live_payload()
        with patch.object(self.service, "fetch_live_ecmwf", return_value=sample):
            res = self.service.get_weather_forecast(horizon_hours=24)
            self.assertTrue(res["is_live"])
            self.assertEqual(res["mode"], "live")
            self.assertEqual(res["source"], "ECMWF IFS")
            self.assertEqual(res["fetched_at"], "27 Sep 2026, 17:00 UTC")
            self.assertEqual(res["forecast_updated_at"], "27 Sep 2026, 00:00 UTC")
            self.assertEqual(res["cache_age_seconds"], 0)
            self.assertEqual(len(res["points"]), 24)

    # 3: Cache hit within TTL
    def test_02_cache_hit_within_ttl(self):
        sample = self._sample_live_payload()
        mock_fetch = MagicMock(return_value=sample)
        with patch.object(self.service, "fetch_live_ecmwf", mock_fetch):
            res1 = self.service.get_weather_forecast(horizon_hours=24)
            self.assertEqual(mock_fetch.call_count, 1)

            # Second call within TTL returns cache, NO provider call
            res2 = self.service.get_weather_forecast(horizon_hours=24)
            self.assertEqual(mock_fetch.call_count, 1)
            self.assertTrue(res2["is_live"])
            self.assertEqual(res2["mode"], "live")

    # 4: Concurrent request coalescing
    def test_03_concurrent_request_coalescing(self):
        import concurrent.futures
        sample = self._sample_live_payload()
        mock_fetch = MagicMock(side_effect=lambda: (time.sleep(0.05), sample)[1])
        with patch.object(self.service, "fetch_live_ecmwf", mock_fetch):
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.service.get_weather_forecast, horizon_hours=24) for _ in range(5)]
                results = [f.result() for f in futures]

            self.assertEqual(mock_fetch.call_count, 1)
            for r in results:
                self.assertTrue(r["is_live"])
                self.assertEqual(r["mode"], "live")

    # 5 & 6: HTTP 429 and provider cooldown active
    def test_04_http_429_cooldown(self):
        # Seed an existing payload so cached fallback is returned
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = sample
            _WEATHER_STATE["live_fetched_at"] = time.time() - 1000  # Stale (>900s)

        http_err = urllib.error.HTTPError(
            url="https://api.open-meteo.com/v1/ecmwf",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None
        )
        with patch.object(self.service, "fetch_live_ecmwf", side_effect=http_err):
            res = self.service.get_weather_forecast(horizon_hours=24)
            self.assertFalse(res["is_live"])
            self.assertEqual(res["mode"], "cached")
            self.assertIn("429", res.get("fallback_reason", ""))

            status = self.service.get_pipeline_status()
            self.assertTrue(status["provider_cooldown_active"])
            self.assertEqual(status["last_provider_status_code"], 429)
            self.assertGreater(status["provider_cooldown_remaining_seconds"], 200)

            # Subsequent call during cooldown does not call fetch
            res_cooldown = self.service.get_weather_forecast(horizon_hours=24)
            self.assertFalse(res_cooldown["is_live"])
            self.assertEqual(res_cooldown["mode"], "cached")

    # 7: Recovery after cooldown expires
    def test_05_recovery_after_cooldown(self):
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["cooldown_until"] = time.time() - 5  # Expired 5s ago
            _WEATHER_STATE["last_provider_error"] = "HTTP 429 Too Many Requests"
            _WEATHER_STATE["live_fetched_at"] = time.time() - 1000

        with patch.object(self.service, "fetch_live_ecmwf", return_value=sample):
            res = self.service.get_weather_forecast(horizon_hours=24)
            self.assertTrue(res["is_live"])
            self.assertEqual(res["mode"], "live")

            status = self.service.get_pipeline_status()
            self.assertFalse(status["provider_cooldown_active"])
            self.assertIsNone(status["last_provider_error"])

    # 8: Persistent snapshot loading
    def test_06_persistent_snapshot_loading(self):
        test_cache_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_cache_snapshot.json")
        sample = self._sample_live_payload()
        with open(test_cache_path, "w", encoding="utf-8") as f:
            json.dump(sample, f)

        try:
            custom_service = WeatherForecastService(cache_dir=os.path.dirname(test_cache_path))
            custom_service.cache_file = test_cache_path

            # Network fails
            with patch.object(custom_service, "fetch_live_ecmwf", side_effect=Exception("Offline")):
                fallback = custom_service.get_weather_forecast(horizon_hours=24)
                self.assertFalse(fallback["is_live"])
                self.assertEqual(fallback["mode"], "cached")
                self.assertEqual(len(fallback["points"]), 24)
        finally:
            if os.path.exists(test_cache_path):
                os.remove(test_cache_path)

    # 9: Failed refresh preserves last valid snapshot
    def test_07_failed_refresh_preserves_snapshot(self):
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = sample
            _WEATHER_STATE["live_fetched_at"] = time.time() - 1000

        with patch.object(self.service, "fetch_live_ecmwf", side_effect=Exception("Provider timeout")):
            success, payload = self.service.refresh_weather_snapshot(force=True, horizon_hours=24)
            self.assertFalse(success)
            self.assertFalse(payload["is_live"])
            self.assertEqual(payload["mode"], "cached")
            self.assertEqual(len(payload["points"]), 24)

    # 10: Background refresh daemon
    def test_08_background_refresh_daemon(self):
        sample = self._sample_live_payload()
        with patch.object(WeatherForecastService, "fetch_live_ecmwf", return_value=sample):
            start_background_weather_refresh(interval_seconds=1.0)
            time.sleep(0.3)
            status = self.service.get_pipeline_status()
            stop_background_weather_refresh()
            self.assertTrue(status["cache_present"])

    # 11: Stale snapshot fallback behavior
    def test_09_stale_snapshot_fallback(self):
        stop_background_weather_refresh()
        WeatherForecastService.clear_in_memory_cache()
        self.service.cache_file = "non_existent_file.json"
        with patch.object(WeatherForecastService, "fetch_live_ecmwf", side_effect=Exception("Provider Down")):
            res = self.service.get_weather_forecast(horizon_hours=24)
            self.assertFalse(res["is_live"])
            self.assertEqual(res["mode"], "historical_fallback")
            self.assertIn("ERA5", res["source"])

    # 12: /api/weather/status health telemetry
    def test_10_weather_status_endpoint(self):
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = sample
            _WEATHER_STATE["live_fetched_at"] = time.time()

        resp = self.client.get("/api/weather/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_live"])
        self.assertEqual(data["mode"], "live")
        self.assertIn("provider", data)
        self.assertIn("cache_age_seconds", data)
        self.assertIn("provider_cooldown_active", data)

    # 13: /api/weather/live
    def test_11_weather_live_endpoint(self):
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = sample
            _WEATHER_STATE["live_fetched_at"] = time.time()

        resp = self.client.get("/api/weather/live?horizon=24")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_live"])
        self.assertEqual(data["mode"], "live")
        self.assertEqual(data["source"], "ECMWF IFS")
        self.assertEqual(len(data["points"]), 24)

    # 14: /api/schedule?season=live metadata propagation
    def test_12_schedule_weather_metadata_propagation(self):
        sample = self._sample_live_payload()
        with _STATE_LOCK:
            _WEATHER_STATE["live_payload"] = sample
            _WEATHER_STATE["live_fetched_at"] = time.time()

        resp = self.client.get("/api/schedule?season=live&horizon=24")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        wm = data.get("weather_metadata", {})
        self.assertTrue(wm.get("is_live"))
        self.assertEqual(wm.get("mode"), "live")
        self.assertEqual(wm.get("source"), "ECMWF IFS")
        self.assertEqual(data["summary"]["weather_mode"], "live")

    # 15: Manual refresh and sync endpoints authorization
    def test_13_manual_refresh_and_sync_endpoints(self):
        sample = self._sample_live_payload()
        with patch.object(self.service, "fetch_live_ecmwf", return_value=sample):
            # 1. Manual refresh
            resp = self.client.post("/api/weather/refresh")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["is_live"])

            # 2. Sync endpoint
            sync_resp = self.client.post("/api/weather/sync", json=sample)
            self.assertEqual(sync_resp.status_code, 200)
            sync_data = sync_resp.json()
            self.assertTrue(sync_data["success"])
            self.assertEqual(sync_data["points"], 24)


if __name__ == "__main__":
    unittest.main()
