# POLAR GRID
### AI-Assisted Renewable Energy Forecasting & Microgrid Dispatch Optimization for Antarctic Stations
**Case Study: Mawson Station, Mac. Robertson Land, Antarctica (67.6027° S, 62.8738° E)**

> **Project Type**: College SIH Prototype / Operational Decision-Support System  
> **Core Value**: Minimizes expensive, high-emission diesel fuel consumption by converting upcoming numerical weather forecasts into renewable generation estimates, buffering with battery storage (BESS), and computing optimal hourly dispatch schedules using Linear Programming.

---

## 1. TECHNICAL ARCHITECTURE (HONEST DATA DECOUPLING)

The system strictly does **NOT** claim that an AI model predicts the atmospheric weather. The decoupled operational pipeline is:

```
HISTORICAL MAWSON ELECTRICITY (AADC)
            ↓
   Station Demand Model
            ↓
Predicted Station Demand
                                   ↘
LIVE ECMWF WEATHER FORECAST (IFS)   →   MICROGRID OPTIMIZER (HiGHS LP)   →   RECOMMENDED DISPATCH
            ↓                      ↗     (Renewables + Battery + Diesel)
Renewable Generation Model (Physics)
            ↓
Predicted Wind + Solar Power
```

1. **ECMWF provides the numerical weather forecast** (temperature, wind velocity, solar radiation).
2. **Polar Grid converts the weather forecast into renewable generation estimates** using physical equipment equations.
3. **ML models predict station electrical demand** based on historical Mawson consumption patterns and heating deficit.
4. **The optimizer selects the lowest-fuel dispatch schedule** while maintaining reliability and equipment bounds.

---

## 2. AUTHENTIC DATA SOURCES & SCIENTIFIC TRANSPARENCY

| Component | Source | Frequency | What Is Real vs Modeled |
| :--- | :--- | :---: | :--- |
| **Historical Station Load** | Australian Antarctic Data Centre (AADC `indicator_59.csv`) | Monthly (1986–2016) | **Real historical monthly data (360 records)**. Hourly profile is modeled from thermal heating degree equations and diurnal occupancy, **strictly calibrated** to Mawson's real historical monthly electricity consumption (~185 kW continuous average). |
| **Historical Diesel Usage** | Australian Antarctic Data Centre (AADC `indicator_56.csv`) | Monthly (1993–2016) | **Real historical monthly records (278 records)** used for generator calibration. |
| **Atmospheric Weather Archive** | ECMWF ERA5 Reanalysis | Hourly (2023 Full Year) | **Genuine ERA5 hourly atmospheric reanalysis (8,760 records)** used for model training and historical backtesting. |
| **Operational Weather Forecast** | ECMWF IFS via Open-Meteo API | Hourly (72–96h forward) | **Continuous live forecast** with automated local caching and transparent ERA5 fallback. |

---

## 3. RIGOROUS ML VALIDATION (ZERO FUTURE LOOKAHEAD)

Predictions are evaluated on an unseen chronological holdout window:
- **Training Period**: Jan 02, 2023 00:00 to Oct 20, 2023 03:00 (6,988 hourly records • 80% split).
- **Test Period**: Oct 20, 2023 04:00 to Dec 31, 2023 23:00 (1,748 hourly records • 20% unseen holdout).
- **Leakage Prevention**: Strictly chronological. No shuffling. Lags ($t-1, t-2, t-24$) look backward only.

### Machine Learning vs Persistence Baseline ($\hat{y}(t) = y(t-1)$)

| Target Variable | Persistence Baseline MAE | Polar Grid ML MAE | Improvement % | Result |
| :--- | :---: | :---: | :---: | :---: |
| **Station Demand (kW)** | **1.60 kW** | **1.25 kW** | **+22.1%** | ✅ Beats Baseline |
| **Solar Radiation (W/m²)** | **63.90 W/m²** | **17.31 W/m²** | **+72.9%** | ✅ Beats Baseline |
| **Wind Speed (m/s)** | **0.62 m/s** | **0.60 m/s** | **+2.7%** | ✅ Beats Baseline |
| **Temperature (°C)** | **0.47 °C** | **0.38 °C** | **+18.9%** | ✅ Beats Baseline |

*Multi-Horizon Forecast Accuracy (24h / 48h / 72h):*
- **24-Hour**: Demand MAE 1.32 kW (+88.7%), Wind MAE 0.44 m/s (+68.6%), Solar MAE 8.71 W/m² (+96.4%).
- **48-Hour**: Demand MAE 1.10 kW (+92.4%), Wind MAE 0.48 m/s (+69.6%), Solar MAE 6.81 W/m² (+97.2%).
- **72-Hour**: Demand MAE 0.97 kW (+92.6%), Wind MAE 0.55 m/s (+84.4%), Solar MAE 8.34 W/m² (+96.6%).

---

## 4. HARDWARE CONFIGURATION & PHYSICAL BOUNDS

- **Wind Turbines**: 2 × 100 kW Antarctic-grade turbines = 200 kW total (Cut-in: 3.5 m/s, Rated: 12.0 m/s, Cut-out: 25.0 m/s).
- **Solar Photovoltaics**: 100 kW nameplate with sub-zero cold air boost ($P = 0$ when $G < 5\text{ W/m}^2$).
- **Battery Storage (BESS)**: 300 kWh capacity, 100 kW max charge/discharge, 90% round-trip efficiency, strictly bounded between **20.0% and 95.0% SoC**.
- **Diesel Backup**: 3 × 125 kW generators = 375 kW continuous ceiling.
- **Power Balance Constraint**: $\text{Generation} - \text{Battery Charge} = \text{Demand}$ enforced with **0.0 kW imbalance**.

---

## 5. QUICK START & RUNNING LOCALLY

### Run Automated Unit Tests (10 Verification Checks)
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Run Master Pipeline (Ingestion → ML → HiGHS → Artifacts)
```powershell
python run_pipeline.py
```

### Launch Interactive Application
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in any browser.

---

## 6. 2-MINUTE JUDGE DEMONSTRATION SCRIPT

1. **Step 1 — Context**: "This is Mawson Station, Mac. Robertson Land, Antarctica."
2. **Step 2 — Live Weather**: "We ingest the latest hourly ECMWF numerical weather forecast for the station."
3. **Step 3 — Demand Modeling**: "Our model predicts station demand calibrated against 30 years of official AADC records."
4. **Step 4 — Generation Physics**: "We convert forecasted wind velocity and solar radiation into renewable power using physical equipment curves."
5. **Step 5 — Linear Programming**: "The SciPy HiGHS optimizer schedules renewables, battery storage, and diesel to minimize fuel while guaranteeing 100% station supply."
6. **Step 6 — Fuel Savings**: "In Austral Summer, diesel reduction reaches 100% (24h) / 78.6% (48h). Our validated annual simulation projects a 41.45% average reduction across all 12 months."
7. **Step 7 — Validation**: "Predictions are verified on unseen test data and demonstrably beat the Persistence Baseline across all horizons."

---

## 7. DOCUMENTATION INDEX
- [Operational Architecture](file:///c:/Users/Acer/Desktop/PolarGrid/docs/OPERATIONAL_ARCHITECTURE.md)
- [ML Validation & Baseline Report](file:///c:/Users/Acer/Desktop/PolarGrid/docs/ML_VALIDATION.md)
- [Live Weather Service Specification](file:///c:/Users/Acer/Desktop/PolarGrid/docs/LIVE_WEATHER.md)
- [Dataset Report](file:///c:/Users/Acer/Desktop/PolarGrid/docs/DATASET_REPORT.md)
- [Final SIH Validation Report](file:///c:/Users/Acer/Desktop/PolarGrid/FINAL_SIH_VALIDATION_REPORT.md)
