# DATASET REPORT: POLAR GRID

**Project**: Polar Grid - AI-Assisted Renewable Energy Forecasting & Microgrid Optimization  
**Target Station**: Mawson Station, Antarctica (67.6027° S, 62.8738° E)  
**Date**: September 2026  
**Status**: MVP Phase 1 Inspection Complete  

---

## 1. Summary of Available Datasets

| Dataset File / Source | File Type | Time Period | Native Resolution | Key Useful Columns | Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SOE_SFU.zip`** (`indicator_59.csv`) | CSV | 1986 – 2016 (30 years) | **Monthly** | `Date`, `Place='Mawson'`, `Parameter='Station electricity usage'`, `Value` (kWh) | Monthly aggregate only; no hourly station load data. |
| **`SOE_SFU.zip`** (`indicator_56.csv`) | CSV | 1993 – 2016 (23 years) | **Monthly** | `Date`, `Place='Mawson'`, `Parameter='Fuel usage'`, `Value` (Litres) | Monthly aggregate of diesel fuel consumed by generators & boilers. |
| **`SOE_SFU.zip`** (`indicator_58.csv`) | CSV | 1993 – 2016 | **Monthly** | `Date`, `Place`, `Value` (Litres) | Vehicle fuel only (not stationary power generation). |
| **`SOE_SFU.zip`** (`indicator_57.csv`) | CSV | 1995 – 2016 | **Monthly** | `Date`, `Place`, `Value` (Litres) | Incinerator fuel only. |
| **`3491775ab61d2e083fb4ef37e09ee91a.grib`** | Binary GRIB1 (5.5 KB) | Year 2010 | **Monthly** (12 monthly slices) | `param_165` (10m U wind), `param_166` (10m V wind), `param_167` (2m temperature), `param_169` (surface solar radiation downwards) | Single point for Mawson, only 1 snapshot per month. Insufficient by itself for 24–72h dynamic operational dispatch. |
| **`climate_temps.zip`** | TXT files | Historical | **Monthly** | Mean air temperatures for sub-Antarctic islands | Excludes hourly Antarctic continental station data. |
| **`feart-10-961799.pdf`** | PDF | 1986 – 2020 | Publication | Solar radiation reconstruction and ERA5 comparison literature | Background reference paper. |
| **ERA5 Hourly Reanalysis** *(ECMWF via Open-Meteo Archive)* | Reanalysis API / CSV | Continuous | **Hourly** | `temperature_2m`, `wind_speed_10m`, `wind_direction_10m`, `shortwave_radiation`, `direct_normal_irradiance`, `diffuse_radiation` | Open reanalysis model data; required to enable genuine 24–72 hour operational forecasting. |

---

## 2. Detailed Dataset Inspections

### 2.1 Station Electricity Usage (`indicator_59.csv`)
- **Source**: Australian Antarctic Data Centre (AADC), Commonwealth of Australia.
- **Total Records for Mawson**: 360 monthly records (Jan 1986 – Feb 2016).
- **Missing Values**: 8 missing months out of 360 (97.8% data completeness).
- **Typical Range for Mawson**:
  - Monthly usage: **110,000 to 175,000 kWh/month**.
  - Equivalent continuous average electrical load: **~150 kW to ~240 kW**, peaking during Antarctic winter (June–August) due to increased heating, lighting, and indoor activity.

### 2.2 Station Generator Fuel Usage (`indicator_56.csv`)
- **Source**: AADC, Commonwealth of Australia.
- **Total Records for Mawson**: 278 monthly records (Jan 1993 – Feb 2016).
- **Missing Values**: 0 missing records in the recorded range.
- **Typical Range for Mawson**:
  - Monthly diesel fuel usage: **44,000 to 75,000 litres/month**.
  - Specific fuel consumption empirical ratio: **~0.30 to ~0.38 litres/kWh**, perfectly consistent with heavy-duty polar diesel generator operations.

### 2.3 ERA5 Weather Data (`3491775ab61d2e083fb4ef37e09ee91a.grib` & Hourly ERA5)
- **Coordinates**: Mawson Station (-67.6027° S, 62.8738° E).
- **Variables**:
  - `t2m` (2m Temperature): -25°C to +2°C.
  - `wind_speed_10m`: 5 m/s to >30 m/s (Mawson is renowned as one of the windiest coastal stations in Antarctica).
  - `solar_radiation`: 0 W/m² during polar night (May–July), reaching up to 600–800 W/m² during polar day (December–January).

---

## 3. Transparency & Data Integrity Classifications

As mandated by the project integrity guidelines:
- **REAL HISTORICAL DATA**:
  - Mawson monthly electricity consumption (1986–2016).
  - Mawson monthly generator diesel fuel consumption (1993–2016).
  - Monthly ERA5 reanalysis single-level data (2010).
- **REANALYSIS DATA**:
  - Hourly ECMWF ERA5 weather parameters (wind speed, solar irradiance, ambient temperature) for Mawson Station coordinates.
- **MODELED DATA**:
  - Hourly load profile synthesized using physical thermal degree-hour formulas and diurnal human activity profiles, **strictly calibrated** so that the monthly integral matches the actual historical monthly consumption in `indicator_59.csv`.
  - Solar PV generation modeled from solar irradiance, ambient temperature, and panel efficiency.
  - Wind generation modeled from wind speed and turbine power curves.
- **FORECASTED DATA**:
  - Machine learning multi-step predictions for temperature, wind, solar irradiance, and demand using chronological splits.
- **OPTIMIZED DISPATCH**:
  - Recommended hourly schedule computed via Linear Programming (LP/MILP) minimizing diesel fuel while respecting battery SoC and power balance constraints.

---

## 4. Preprocessing Pipeline Design

1. **Extraction & Isolation**:
   - Extract CSVs from `SOE_SFU.zip` into `data/raw/` without altering the originals in `DataSet/`.
2. **Cleaning & Standardization**:
   - Filter `Place == 'Mawson'`.
   - Parse `Date` (e.g. `'Jan-86'`) into standardized datetime format.
   - Clean numerical values, handle NaNs via forward/linear interpolation.
   - Rename to canonical column names: `timestamp`, `electricity_kwh`, `fuel_litres`.
3. **Hourly Alignment**:
   - Combine with hourly ERA5 meteorological time series.
   - Synthesize and calibrate the hourly demand profile to real monthly aggregates.
   - Save the unified, clean dataset to `data/processed/mawson_hourly_energy_weather.csv`.
