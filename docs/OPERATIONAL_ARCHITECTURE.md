# POLAR GRID: OPERATIONAL ARCHITECTURE
### End-to-End Technical Workflow for Antarctic Microgrid Decision Support

## 1. Executive Architecture Overview

Polar Grid does not claim that an AI model predicts the atmospheric weather. Instead, the operational system decouples weather forecasting, electrical load modeling, physics-based generation, and linear programming dispatch:

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

---

## 2. Core Functional Components

### Component 1: Historical Station Electricity Demand Model
- **Data Source**: Australian Antarctic Data Centre (AADC) - `indicator_59.csv` (30 years of official monthly Mawson electricity consumption, 1986–2016).
- **Transparency Affirmation**: Public Mawson electricity telemetry is recorded monthly (~135,000 kWh/month). Hourly demand is modeled using thermodynamic heating degree-hours plus diurnal station occupancy, strictly calibrated to real monthly totals (continuous average ~185 kW).
- **Prediction Equation**:
  $$P_{\text{demand}}(t) = P_{\text{base}} + \beta \cdot \max(0, T_{\text{setpoint}} - T_{\text{amb}}(t)) + A_{\text{diurnal}} \cdot \sin\left(\frac{(h - 6)\pi}{12}\right)$$
  - Base life-support load: $120.0\text{ kW}$
  - Heating sensitivity coefficient: $\beta = 3.2\text{ kW/}^\circ\text{C}$
  - Indoor setpoint: $18.0^\circ\text{C}$

### Component 2: Live ECMWF Weather Forecast Engine
- **Service**: Numerical Weather Prediction via ECMWF IFS (Integrated Forecasting System) accessed through Open-Meteo's ECMWF endpoint.
- **Coordinates**: Mawson Station, Antarctica (`-67.6027°S, 62.8738°E`).
- **Variables**: 2m Temperature (°C), 10m Wind Speed (m/s), 10m Wind Direction (°), Shortwave Solar Radiation (W/m²), Direct Normal Irradiance (W/m²), Diffuse Radiation (W/m²).
- **Fallback Hierarchy**:
  1. Live ECMWF forecast (72–96h forward).
  2. Locally cached ECMWF forecast (`data/processed/latest_ecmwf_forecast.json`).
  3. Clean ERA5 historical reanalysis slice (`mawson_hourly_energy_weather.csv`).

### Component 3: Physics-Based Renewable Generation Estimator
- **Solar Photovoltaics (100 kW nameplate)**:
  $$P_{\text{solar}}(t) = P_{\text{cap}} \cdot \left(\frac{G(t)}{G_{\text{STC}}}\right) \cdot \left[1 + \gamma \cdot (T_{\text{cell}}(t) - 25^\circ\text{C})\right] \cdot \eta_{\text{inv}}$$
  - Inverter cutoff: Standby tare threshold at $5\text{ W/m}^2$ ($P=0$ when $G < 5\text{ W/m}^2$).
  - Temperature coefficient: $\gamma = -0.0038/\text{K}$ (Antarctic cold air efficiency boost).
  - Inverter efficiency: $\eta_{\text{inv}} = 95\%$.
- **Wind Turbines ($2 \times 100\text{ kW} = 200\text{ kW}$ total)**:
  $$P_{\text{wind}}(v) = \begin{cases} 
  0 & v < 3.5\text{ m/s (Cut-in)} \\
  P_{\text{rated}} \cdot \frac{v^3 - v_{\text{in}}^3}{v_{\text{rated}}^3 - v_{\text{in}}^3} & 3.5 \le v < 12.0\text{ m/s (Cubic Ramp)} \\
  200\text{ kW} & 12.0 \le v \le 25.0\text{ m/s (Rated)} \\
  0 & v > 25.0\text{ m/s (Storm Cut-out Shutdown)}
  \end{cases}$$

### Component 4: SciPy HiGHS Linear Programming Dispatch Engine
- **Solver**: `scipy.optimize.linprog(method='highs')`.
- **Decision Variables**: Solar used ($P_{\text{sol}}$), Wind used ($P_{\text{wnd}}$), Battery charge ($P_{\text{ch}}$), Battery discharge ($P_{\text{dis}}$), Diesel output ($P_{\text{dsl}}$), Curtailment ($P_{\text{cur}}$), Unmet demand ($P_{\text{unm}}$), Battery stored energy ($E_{\text{bat}}$).
- **Power Conservation Equality**:
  $$P_{\text{sol}}(t) + P_{\text{wnd}}(t) + P_{\text{dis}}(t) + P_{\text{dsl}}(t) + P_{\text{unm}}(t) - P_{\text{ch}}(t) = P_{\text{demand}}(t)$$
  $$\text{Power Imbalance} = 0.0\text{ kW at all time steps.}$$
- **Battery Constraints**:
  - Capacity: $300\text{ kWh}$, Max power: $100\text{ kW}$ charge/discharge.
  - State of Charge (SoC): Strictly $20.0\% \le \text{SoC}(t) \le 95.0\%$.
  - Continuity: $E_{\text{bat}}(t) = E_{\text{bat}}(t-1) + \left(\eta_{\text{ch}} P_{\text{ch}}(t) - \frac{P_{\text{dis}}(t)}{\eta_{\text{dis}}}\right) \Delta t$ with round-trip efficiency $90\%$.
- **Diesel Constraints**:
  - Capacity limit: $0 \le P_{\text{dsl}}(t) \le 375\text{ kW}$ ($3 \times 125\text{ kW}$).
  - Fuel curve: $F(t) = (0.24 \cdot P_{\text{dsl}}(t) + 0.04 \cdot P_{\text{rated}}) \Delta t$.
