# Polar Grid — Data Provenance & Methodology

This directory documents the scientific data sources, preprocessing methodology, and telemetry calibration used by Polar Grid for Antarctic microgrid simulation and optimization at Mawson Station (-67.6027° S, 62.8738° E).

---

## Data Provenance Architecture

```
Raw Official Sources (Offline)
├── AADC Monthly Electricity (Indicator 59) ──┐
├── AADC Monthly Fuel Usage (Indicator 56)   ──┼──> Calibrated Physical Load Model
└── ERA5 Atmospheric Reanalysis (ECMWF)      ──┘          │
                                                          ▼
                                            data/processed/mawson_hourly_energy_weather.csv
                                                          │
                                                          ├──> HistGradientBoosting Forecaster
                                                          └──> HiGHS Dynamic Dispatch Engine
```

---

## 1. Australian Antarctic Data Centre (AADC)
- **Source**: Official Australian Antarctic Division (AAD) State of the Environment indicators:
  - **Indicator 59**: Monthly electrical energy consumption (kWh) recorded at Mawson Station.
  - **Indicator 56**: Monthly station generator diesel fuel consumption (litres) recorded at Mawson Station.
- **Role in Polar Grid**: Establishes the authoritative ground-truth Antarctic baseline for station load magnitude, seasonal winter/summer demand variations, and generator fuel consumption curves.

## 2. ECMWF ERA5 Atmospheric Reanalysis
- **Source**: European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5 atmospheric reanalysis for Mawson Station coordinates (-67.6027, 62.8738).
- **Parameters**: Surface solar radiation downwards (`ssrd`, W/m²), 10m wind speed (`si10`, m/s), 2m air temperature (`t2m`, °C), and surface pressure (`sp`, Pa).
- **Role in Polar Grid**: Provides full-year hourly meteorological conditions across Austral winter (polar night) and Austral summer (continuous daylight) for machine learning training, multi-horizon cross-validation, and renewable resource modelling.

## 3. Processed Hourly Demand Dataset
- **File**: `data/processed/mawson_hourly_energy_weather.csv`
- **Scientific Clarification**: In accordance with Antarctic station operational telemetry realities, this dataset contains **modeled and calibrated hourly load data** derived from official AADC monthly station totals and temperature/occupancy profiles. It is **not** raw real-time SCADA/BMS meter telemetry.
- **Verification**: Evaluated with strict chronological train/test splits (80/20, test period Oct 20 – Dec 31, 2023) yielding a 22.1% MAE improvement over persistence baselines and 99.5% day-tracking accuracy.

## 4. Live Numerical Weather Prediction (ECMWF IFS)
- **Engine**: ECMWF Integrated Forecasting System (IFS) 0.25° operational forecast fetched via Open-Meteo API over HTTPS.
- **Parameters**: Hourly surface solar radiation, direct normal irradiance, diffuse irradiance, 10m wind speed, wind direction, and 2m ambient temperature for up to 96 forecast hours.
- **Offline / Cached Fallback**: `data/processed/latest_ecmwf_forecast.json` caches the latest valid operational forecast to ensure seamless microgrid dispatch execution even during network outages.

---

*Note: Raw source archives and offline extraction scripts are kept outside the production Git repository to maintain a lean, reproducible deployment bundle.*
