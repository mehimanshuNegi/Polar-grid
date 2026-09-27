# POLAR GRID: SIH JURY DEFENSE & Q&A GUIDE

**Project**: Polar Grid – AI-Assisted Renewable Energy Forecasting & Microgrid Dispatch Optimization  
**Purpose**: 25 direct, mathematically sound, honest answers to tough judge questions.

---

### 1. What problem are you solving?
Antarctic research stations rely heavily on diesel fuel for life-support heating and electricity. Transporting fuel via icebreakers is dangerous, logistically complex, and costs $3 to $7 USD per litre. Without intelligent predictive dispatch, diesel generators run continuously at partial loads to guard against weather drops. Polar Grid uses AI forecasting and linear programming optimization to maximize renewable use, buffer with batteries, and minimize diesel fuel.

---

### 2. Why Antarctica?
Antarctica is the most remote, logistically vulnerable, and environmentally protected region on Earth under the Antarctic Treaty System. Cutting diesel fuel saves immense transport costs, prevents catastrophic polar oil spills, and reduces carbon soot deposition on pristine ice sheets.

---

### 3. Why Mawson Station?
Mawson Station (Australian Antarctic Division, 67.60°S, 62.87°E) is an ideal case study:
1. It is one of the windiest coastal sites in Antarctica (frequent 10–25 m/s winds).
2. Australia has installed pioneering renewable hardware there, including two 100 kW Antarctic-grade wind turbines and solar PV arrays.
3. 30 years of public energy consumption records exist from the Australian Antarctic Data Centre (AADC).

---

### 4. Why ERA5?
ECMWF ERA5 is the gold-standard atmospheric reanalysis globally. In Antarctica, ground weather stations are sparse. ERA5 assimilates satellites, radiosondes, and weather radars into a physical numerical weather prediction model, providing continuous, high-resolution hourly weather variables (temperature, wind, solar irradiance) for Mawson's exact coordinates.

---

### 5. What datasets did you use?
1. **AADC Station Energy Records**: `indicator_59.csv` (monthly electricity usage 1986–2016) and `indicator_56.csv` (monthly generator fuel usage 1993–2016).
2. **ECMWF ERA5 Reanalysis**: 8,760 continuous hourly records for 2023 covering temperature, wind speed, wind direction, and solar irradiance.
3. **Local Reanalysis GRIB**: Decoded GRIB1 snapshot data for Mawson.

---

### 6. Which data is real?
- **Real Historical Data**: 30 years of monthly electricity records and 23 years of generator fuel records from AADC; hourly meteorological reanalysis from ECMWF.
- **Modeled Data**: The hourly electrical demand curve is synthesized from thermodynamic heating equations and diurnal shifts, strictly calibrated to real monthly totals.
- **Forecasted Data**: 1-hour rolling predictions from our machine learning models.
- **Simulated Dispatch**: Hourly generator and battery schedules computed by our linear program.

---

### 7. How did you get hourly demand?
Because station electricity is archived publicly as monthly aggregates (~135,000 kWh/month) rather than hourly meter streams, we modeled the hourly load using base scientific life-support power (~120 kW) + heating degree-hour deficit ($T_{\text{setpoint}} - T_{\text{ambient}}$) + diurnal crew activity. We then strictly calibrated this curve so its monthly integral matches real historical consumption.

---

### 8. Is the hourly load real?
No, and we state this clearly. It is a **calibrated thermodynamic model**. We never claim it is real-time sensor telemetry. In our code and dashboard, it is explicitly labeled: `MODELED_LOAD (Calibrated to Real Mawson Monthly Electricity Data)`.

---

### 9. Why is your R² so high (0.966 – 0.992)?
Our ML model is trained on an 80/20 chronological split and operates in a **1-step-ahead rolling persistence mode** (predicting hour $t$ using true observations from $t-1, t-2, t-24$ and cyclical solar/seasonal features). In physical meteorology, temperature, solar curves, and heating loads have strong 1-hour autocorrelation. If we ran an open-loop 48-hour recursive forecast without interim sensor updates, the $R^2$ would naturally degrade to ~0.70–0.85.

---

### 10. Is 78% diesel reduction guaranteed?
No, 78.57% is a **simulated dispatch saving for a 48-hour period in peak Austral Summer (late December)** when Antarctica has 24-hour sunlight and ~10 m/s wind. In Polar Winter (July), the reduction is ~26%. The realistic annual average saving is projected at **~38%–45%**.

---

### 11. Why does winter performance decrease?
During Antarctic winter, solar irradiance drops to zero (polar night), and extreme freezing temperatures increase space heating demands by 30–50%. The microgrid must rely solely on wind turbines and battery storage, requiring more diesel generator backup.

---

### 12. What happens during polar night?
In polar night (May to August), solar radiation is 0 W/m². Our system automatically sets solar PV output to 0.0 kW. The linear program relies on wind generation, charges the battery during high-wind hours, discharges it during lulls, and uses diesel only when battery SoC reaches its 20% minimum safety limit.

---

### 13. Why use AI?
Antarctic weather is notoriously chaotic (katabatic wind surges, blizzard fronts, sudden cloud cover). Traditional rule-based systems react after weather changes occur. AI models identify temporal patterns, lag correlations, and diurnal cycles ahead of time, allowing the system to pre-position battery storage before high-wind or low-wind events occur.

---

### 14. Why use optimization after ML?
Forecasting only predicts *what will happen* (wind speed, solar, demand). It does not decide *what to do*. The Linear Programming optimizer takes predictions and computes the exact physical generator setpoints and battery charge/discharge rates that minimize fuel while respecting physical limits (SoC, inverter C-rates, power balance).

---

### 15. Why not just use solar/wind directly?
Renewable energy cannot be throttled on demand. If wind gusts to 20 m/s, you produce excess energy that will trip the microgrid unless absorbed by a battery or curtailed. If wind drops to 2 m/s, station power crashes instantly unless a generator or battery is already scheduled to take the load. Direct unmanaged renewable integration leads to microgrid instability and generator damage.

---

### 16. What does the battery do?
The 300 kWh Battery Energy Storage System (BESS) acts as a high-speed dynamic buffer. It absorbs surplus renewable power during wind/solar surges and discharges power during brief lulls, preventing the diesel generator from constantly starting, stopping, and running at inefficient low loads.

---

### 17. What happens if wind suddenly drops?
Our stress tests specifically evaluated a sudden 200 kW $\to$ 0 kW wind drop:
1. In the first seconds, the battery discharges immediately up to its 100 kW inverter limit.
2. The optimizer starts the diesel generator to supply the remainder.
3. Power balance is maintained with zero unmet demand.

---

### 18. What is your novelty?
1. An integrated, end-to-end pipeline tailored to the physical constraints of Antarctic research stations.
2. Realistic temperature-derating physics: solar PV efficiency actually increases in cold Antarctic air (+17%), while wind turbines trip above 25 m/s for blizzard protection.
3. Mathematical optimization via Linear Programming guaranteeing global optimality in under 1 second.
4. Transparent modeling with full data integrity.

---

### 19. What is your biggest limitation?
Our historical station energy data is monthly rather than hourly. While our calibrated thermodynamic profile matches monthly reality, having true 15-minute smart meter data would allow the ML model to learn specific station routines (kitchen loads, science lab pumps, meltwater heating cycles).

---

### 20. What would you improve with more resources?
1. Ingest real-time SCADA telemetry from station automated weather stations (AWS).
2. Incorporate demand-side management (e.g., automatically scheduling water-maker reverse osmosis desalination during surplus wind hours).
3. Upgrade from Linear Programming to Mixed-Integer Linear Programming (MILP) with unit commitment (generator minimum up/down runtimes and startup fuel penalties).

---

### 21. How would real-time data improve the system?
Real-time smart meter and anemometer feeds would allow the ML model to update its autoregressive state continuously every 15 minutes, eliminating compounding drift and providing closed-loop operational control.

---

### 22. Can this work at other Antarctic stations?
Yes. The entire codebase is modular. By modifying `config/station_config.json` with new coordinates, turbine counts, PV capacity, and generator sizes, Polar Grid can optimize any polar outpost (e.g., India's Bharati and Maitri stations, or McMurdo Station).

---

### 23. Why Linear Programming?
Linear Programming with modern solvers (HiGHS) guarantees finding the **globally optimal** dispatch solution in milliseconds without getting trapped in local minima, unlike heuristic algorithms or genetic algorithms. It provides 100% mathematical reproducibility.

---

### 24. What happens if the optimizer cannot satisfy demand?
In our formulation, an emergency slack variable (`P_unmet`) is included with an enormous penalty weight ($1,000\times$). If total capacity is physically insufficient, the solver satisfies as much demand as possible, flags unmet load immediately, and alerts the operator, rather than crashing with an infeasible error.

---

### 25. Is this currently deployed at Mawson?
No. This is a **proof-of-concept MVP / Decision Support System** developed for SIH based on real historical data and validated physical models. It is designed to demonstrate technical feasibility to station operators and polar research agencies.
