# POLAR GRID: 3-5 MINUTE SIH DEMO SCRIPT

**Project**: Polar Grid – AI-Assisted Renewable Energy Forecasting & Microgrid Dispatch Optimization  
**Location**: Mawson Station, Antarctica  
**Audience**: SIH Evaluation Panel / Jury  
**Time Limit**: 3 to 5 Minutes  

---

## DEMO CHEAT-SHEET: STEP-BY-STEP SEQUENCE

### STEP 1: Introduction & The Problem (40 Seconds)
- **WHAT TO CLICK**: Ensure dashboard is open at `http://127.0.0.1:8000/`. (Default: Austral Summer, 48 Hours).
- **WHAT TO SHOW**: Point to the Header, Mawson Station badge (`67.60°S, 62.87°E`), and the live system status.
- **WHAT TO SAY**:
  > *"Respected Judges, Antarctic scientific research stations rely almost entirely on diesel generators for electricity and heating. Transporting diesel to Antarctica via icebreakers is hazardous, environmentally sensitive, and costs upwards of $3 to $7 USD per litre. While stations like Australia’s Mawson Station have installed wind turbines and solar panels, Antarctic weather fluctuates violently. Without predictive dispatch, diesel generators are kept running continuously as a safeguard. Polar Grid is an intelligent decision-support system that forecasts weather and station demand 24 to 72 hours ahead, and uses linear programming optimization to schedule the cleanest, most fuel-efficient dispatch possible."*

---

### STEP 2: Data Transparency & Provenance (30 Seconds)
- **WHAT TO CLICK**: Highlight the **Data Provenance Banner** below the header.
- **WHAT TO SHOW**: The 4 badges: `REAL AADC (MONTHLY 1986–2016)`, `ERA5 REANALYSIS`, `CALIBRATED LOAD`, and `LINEAR PROGRAM (HiGHS)`.
- **WHAT TO SAY**:
  > *"Before showing our AI models, here is our data honesty commitment: We do not invent real-world telemetry. We utilized 30 years of official historical monthly electricity records from the Australian Antarctic Data Centre. Because station data is recorded monthly rather than hourly, we synthesized an hourly demand curve based on Antarctic heating degree physics and diurnal station activity, and strictly calibrated it so its monthly sum matches real historical consumption (~185 kW continuous load). Our weather data is genuine hourly ECMWF ERA5 reanalysis for Mawson’s exact coordinates."*

---

### STEP 3: The AI Forecast (40 Seconds)
- **WHAT TO CLICK**: Scroll down to the **AI Operational Forecasting** section. Click on the `DEMAND`, `WIND`, `SOLAR`, and `TEMP` tabs.
- **WHAT TO SHOW**: The dotted prediction line matching the solid actual observation line, and the metric chips ($R^2$, MAE, RMSE).
- **WHAT TO SAY**:
  > *"Here is our forecasting stage. We trained Gradient Boosting regressors using a strict chronological 80/20 train/test split—no random shuffling. Our model predicts ambient temperature, wind velocity, solar irradiance, and station demand with out-of-sample R² scores between 0.96 and 0.99. This high precision is achieved because our model operates in a 1-hour-ahead rolling persistence mode, updating predictions as station telemetry arrives."*

---

### STEP 4: Renewable Estimation & Microgrid Optimization (45 Seconds)
- **WHAT TO CLICK**: Scroll to the **Optimal Microgrid Dispatch & Battery Dynamics** section.
- **WHAT TO SHOW**: The stacked area chart (Green = Direct Renewable, Purple = Battery Discharge, Red = Diesel Generator) vs. the White line (Total Demand).
- **WHAT TO SAY**:
  > *"Next, our physics models convert forecast weather into electrical generation potential: 100 kW of solar PV with cold-temperature efficiency boost, and two 100 kW Antarctic wind turbines with cut-in, rated, and storm cut-off limits. Then, our Linear Programming optimizer—solved with SciPy’s HiGHS solver—decides for each future hour how much power should come from renewables, battery storage, and diesel to satisfy demand while minimizing fuel consumption. You can see how green renewable energy and purple battery storage supply almost the entire load, keeping diesel generation minimal."*

---

### STEP 5: Battery Constraints & Safety (25 Seconds)
- **WHAT TO CLICK**: Point to the **Battery State of Charge (SoC %)** chart below the dispatch graph.
- **WHAT TO SHOW**: The purple SoC curve staying strictly between the dashed red line (20% Min) and dashed green line (95% Max).
- **WHAT TO SAY**:
  > *"In extreme polar environments, over-discharging batteries can freeze and destroy them. As you can see, our optimizer strictly enforces a 20% to 95% safety band, guaranteeing that battery energy is conserved and buffered safely with 90% round-trip efficiency."*

---

### STEP 6: Impact & Baseline Comparison (35 Seconds)
- **WHAT TO CLICK**: Scroll to the **Diesel Reduction Benchmark** and the top KPI cards.
- **WHAT TO SHOW**: The side-by-side bar chart: Baseline (`2,486 L`) vs. Polar Grid (`533 L`), and the **78.57%** reduction card.
- **WHAT TO SAY**:
  > *"Comparing our optimized schedule against a standard 100% diesel baseline over this 48-hour period: Polar Grid cuts diesel fuel consumption from 2,486 litres down to 533 litres—saving over 1,950 litres of fuel. That represents a 78.6% simulated fuel reduction, saving an estimated $6,000 to $14,000 in fuel delivery logistics and preventing 5.2 tonnes of CO2 emissions in just two days."*

---

### STEP 7: Seasonality Contrast — Switch to Winter (45 Seconds)
- **WHAT TO CLICK**: Scroll to the top controls and click: **`❄️ Polar Night (Jul • No Sun)`**.
- **WHAT TO SHOW**: 
  1. The banner updates to: *"Active Demonstration: Polar Winter (July) — Complete polar night (solar = 0 kW)"*.
  2. The KPI card updates to **`25.76%` simulated diesel reduction**.
  3. The stacked dispatch chart now shows solar is at 0 kW, with wind and battery providing the clean energy.
- **WHAT TO SAY**:
  > *"A critical scientific question is: what happens in winter? If we switch to our Polar Night scenario in July, Antarctica experiences 24-hour darkness. Solar generation drops to exactly 0 kW. However, Mawson Station is notoriously windy. Even with zero sun, our wind turbines and battery storage still deliver a 25.8% simulated diesel reduction! This contrast is vital: 78% is peak summer performance, while 26% is polar night performance, resulting in a realistic annual projected saving of 38% to 45%."*

---

### STEP 8: Horizon Control Demo (20 Seconds)
- **WHAT TO CLICK**: Click the **`24 Hours`** button, then the **`72 Hours`** button.
- **WHAT TO SHOW**: The entire dashboard, charts, and schedule table instantly re-compute and update in real-time without reloading the webpage.
- **WHAT TO SAY**:
  > *"Operators can adjust planning horizons dynamically. Whether planning short-term 24-hour operations or extended 72-hour weather storm windows, the linear program solves and updates the dispatch schedule in real time."*

---

### STEP 9: Schedule Table & Actionable Output (20 Seconds)
- **WHAT TO CLICK**: Scroll down to the **Recommended Operational Schedule Table**.
- **WHAT TO SHOW**: The hourly timetable showing exact kW targets for solar, wind, battery charge (+), discharge (-), SoC %, and diesel generation.
- **WHAT TO SAY**:
  > *"Finally, Polar Grid outputs an actionable hourly schedule for the station stationmaster or automated SCADA system, indicating exact generator settings and battery charge/discharge instructions for every hour ahead."*

---

### STEP 10: Conclusion & Next Steps (15 Seconds)
- **WHAT TO SAY**:
  > *"To conclude: Polar Grid demonstrates that AI forecasting combined with mathematical linear programming can drastically cut diesel reliance at polar stations. With real-time smart meter integration, this system could be deployed to save hundreds of thousands of litres of fuel across Antarctic stations. Thank you, and we welcome your questions!"*
