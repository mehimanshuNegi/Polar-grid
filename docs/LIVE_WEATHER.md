# POLAR GRID: LIVE ECMWF WEATHER SERVICE & FALLBACK SPECIFICATION

## 1. Primary Live Weather Endpoint

Polar Grid integrates continuous live Numerical Weather Prediction (NWP) from the European Centre for Medium-Range Weather Forecasts (ECMWF) via Open-Meteo's dedicated ECMWF endpoint.

### Endpoint URL & Query Format
```
https://api.open-meteo.com/v1/ecmwf?
latitude=-67.6027&
longitude=62.8738&
hourly=temperature_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_normal_irradiance,diffuse_radiation&
wind_speed_unit=ms&
forecast_days=4
```

### Station Coordinates & Metadata
- **Station**: Mawson Station, Mac. Robertson Land, Antarctica
- **Latitude**: `-67.6027° S`
- **Longitude**: `62.8738° E`
- **Elevation**: 16 meters above sea level
- **Forecast Horizon**: 72 to 96 forward hourly timesteps

---

## 2. Variables & Standardized Scientific Units

| Variable | API Parameter | Unit | Physical Range at Mawson | Purpose in Polar Grid |
| :--- | :--- | :---: | :---: | :--- |
| **Air Temperature** | `temperature_2m` | °C | -45.0°C to +5.0°C | Station heating load + solar PV cold-efficiency boost |
| **Wind Speed** | `wind_speed_10m` | m/s | 0.0 to 45.0 m/s | 2 × 100 kW wind turbine generation model |
| **Wind Direction** | `wind_direction_10m` | ° (0–360) | 0° to 360° | Station orientation & turbulence logging |
| **Shortwave Radiation** | `shortwave_radiation` | W/m² | 0 to 1,150 W/m² | Global horizontal irradiance for solar PV |
| **Direct Normal Irradiance**| `direct_normal_irradiance` | W/m² | 0 to 1,050 W/m² | Direct solar beam potential |
| **Diffuse Radiation** | `diffuse_radiation` | W/m² | 0 to 450 W/m² | Cloud/snow albedo scattered irradiance |

*Note: The parameter `&wind_speed_unit=ms` ensures wind speed is delivered directly in meters per second without unit conversion artifacts.*

---

## 3. Fallback Hierarchy & Graceful Degradation

The system remains 100% operational offline or during satellite communication dropouts common in Antarctica:

```
[Level 1: Live ECMWF Endpoint]
            ↓ (Network Error or Timeout > 8s)
[Level 2: Cached ECMWF Forecast] (data/processed/latest_ecmwf_forecast.json)
            ↓ (Cache Missing or < 24 Hours)
[Level 3: Historical ERA5 Reanalysis] (data/processed/mawson_hourly_energy_weather.csv)
```

### Explicit UI Status Labeling
The system never presents historical data as live weather:
- **Live Mode**: `● LIVE FORECAST — ECMWF IFS` (Green pill, pulsing indicator, updated timestamp).
- **Fallback Mode**: `● FALLBACK FORECAST — ERA5 / CACHED DATA` (Amber pill, fallback reason declared).
- **Historical Benchmark Mode**: `● HISTORICAL BENCHMARK — ERA5 REANALYSIS` (Blue/Purple pill).
