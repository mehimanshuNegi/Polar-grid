import React, { useState } from 'react';
import {
  Database,
  CloudSun,
  ShieldCheck,
  Sliders,
  Layers,
  ArrowRight,
  ArrowDown,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function HowItWorksPage({ onNavigate }) {
  const [techOpen, setTechOpen] = useState(false);

  return (
    <div className="how-it-works-dashboard">
      {/* ================================================================ */}
      {/* 1. HEADER */}
      {/* ================================================================ */}
      <div className="how-header-strip">
        <div>
          <h1 className="how-main-title">HOW POLAR GRID WORKS</h1>
          <p className="how-sub-title">System architecture: from historical data & live ECMWF weather to optimized dispatch</p>
        </div>

        <div className="how-provenance-tag">
          <span>Dual Architecture: Historical ML Path & Live Operational Path</span>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 2. DUAL-PATH ARCHITECTURE VISUALIZATION */}
      {/* ================================================================ */}
      <div className="dual-path-container">
        {/* PATH A: HISTORICAL VALIDATION */}
        <div className="path-column path-historical">
          <div className="path-column-header">
            <span className="path-badge">PATH A</span>
            <h2 className="path-title">HISTORICAL VALIDATION PATH</h2>
            <span className="path-desc">Unseen backtesting of the machine learning demand model</span>
          </div>

          <div className="path-flow-vertical">
            <div className="flow-step-box">
              <span className="step-tag">DATA SOURCES</span>
              <h4>AADC Monthly Electricity + ERA5 Reanalysis</h4>
              <p>Official 30-year station records combined with hourly meteorological reanalysis.</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box">
              <span className="step-tag">CALIBRATION</span>
              <h4>Calibrated Hourly Station Benchmark</h4>
              <p>Generates high-resolution hourly load dataset honoring monthly station fuel consumption.</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box">
              <span className="step-tag">MACHINE LEARNING</span>
              <h4>HistGradientBoostingRegressor</h4>
              <p>Trained on 80% chronological split with causal time-lag weather features.</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box step-result">
              <span className="step-tag">OUTCOME</span>
              <h4>Historical Backtest (Validation Page)</h4>
              <p>Predicted vs Actual demand comparison on unseen holdout test period (Oct 21 – Dec 31).</p>
            </div>
          </div>
        </div>

        {/* PATH B: LIVE OPERATIONAL DISPATCH */}
        <div className="path-column path-operational">
          <div className="path-column-header">
            <span className="path-badge badge-teal">PATH B</span>
            <h2 className="path-title">LIVE OPERATIONAL PATH</h2>
            <span className="path-desc">Real-time weather forecast to automated microgrid scheduling</span>
          </div>

          <div className="path-flow-vertical">
            <div className="flow-step-box">
              <span className="step-tag">LIVE INPUT</span>
              <h4>Live ECMWF IFS Forecast via Open-Meteo</h4>
              <p>Real-time numerical atmospheric forecast for Mawson Station (67.6027° S, 62.8738° E).</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box">
              <span className="step-tag">PHYSICAL MODELS</span>
              <h4>Renewable Estimation + Thermal Demand</h4>
              <p>PV cell temperature curves, cubic wind turbine aerodynamics, and station heating demand.</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box">
              <span className="step-tag">EQUIPMENT CONDITIONS</span>
              <h4>Simulated Equipment State</h4>
              <p>Configurable initial battery SoC (50%/25%/20%) and diesel generator capacity (375/250/125 kW).</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box">
              <span className="step-tag">OPTIMIZATION</span>
              <h4>HiGHS Linear Programming Solver</h4>
              <p>Solves 24–72 hour multi-period dispatch minimizing diesel fuel while enforcing exact power balance.</p>
            </div>

            <div className="flow-arrow"><ArrowDown size={18} /></div>

            <div className="flow-step-box step-result result-teal">
              <span className="step-tag">FASTAPI & REACT</span>
              <h4>Operations Dashboard</h4>
              <p>Real-time recommended action, single-line power flow diagram, and hourly dispatch schedule.</p>
            </div>
          </div>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 3. ARCHITECTURE HONESTY DISTINCTION */}
      {/* ================================================================ */}
      <div className="how-honesty-card">
        <h3 className="how-honesty-title">TRANSPARENT SYSTEM BOUNDARIES</h3>
        <p>
          Polar Grid maintains strict technical honesty between its components:
        </p>
        <ul className="how-honesty-list">
          <li><strong>Live Operational Weather:</strong> Powered exclusively by live ECMWF IFS numerical forecasts. Polar Grid does not claim to generate its own numerical weather predictions.</li>
          <li><strong>Operational Demand:</strong> Computed dynamically using station thermal balance equations based on live forecast temperatures. The machine learning model is strictly reserved for historical validation backtests.</li>
          <li><strong>Equipment Telemetry:</strong> Battery and diesel availability states are clearly designated as <em>prototype assumptions</em> for what-if scenario testing, not fabricated live Mawson hardware telemetry.</li>
          <li><strong>Annual Fuel Reduction (41.45%):</strong> An offline simulation benchmark calculated over 8,736 sequential hourly steps, not a real-time field measurement.</li>
        </ul>
      </div>

      {/* ================================================================ */}
      {/* 4. TECHNICAL DETAILS (PROGRESSIVE DISCLOSURE) */}
      {/* ================================================================ */}
      <div className="progressive-accordion">
        <button
          className="accordion-trigger"
          onClick={() => setTechOpen(!techOpen)}
        >
          <div className="trigger-left">
            <Info size={16} className="text-teal" />
            <span>TECHNICAL DETAILS ▸</span>
          </div>
          {techOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {techOpen && (
          <div className="accordion-content">
            <div className="tech-cards-grid">
              <div className="tech-spec-box">
                <h4>HiGHS LP FORMULATION</h4>
                <p>
                  Objective: Min ∑ [ c_diesel × P_diesel(t) + c_unmet × P_unmet(t) + c_bat × (P_ch(t) + P_dis(t)) ]<br />
                  Conservation: P_solar(t) + P_wind(t) + P_dis(t) + P_diesel(t) + P_unmet(t) - P_ch(t) = P_demand(t)
                </p>
              </div>

              <div className="tech-spec-box">
                <h4>BATTERY STORAGE MODEL</h4>
                <p>
                  300 kWh lithium iron phosphate (LiFePO4) storage, maximum 100 kW charge/discharge rate, 90% roundtrip efficiency, bounded strictly between 20% minimum SoC and 95% maximum SoC.
                </p>
              </div>

              <div className="tech-spec-box">
                <h4>DIESEL GENERATOR CURVES</h4>
                <p>
                  Three 125 kW generator sets (375 kW nominal total). Linear fuel curve: 0.24 L/kWh generated + 0.04 L/kW rated capacity.
                </p>
              </div>

              <div className="tech-spec-box">
                <h4>PHYSICAL RENEWABLE MODELS</h4>
                <p>
                  Wind Turbines: 2 × 100 kW rated with cut-in 3.5 m/s, rated 12.0 m/s, cut-out storm shutdown 25.0 m/s. Solar PV: 100 kW DC array with -0.38%/°C cell temperature coefficient.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CTA TO OPERATIONS */}
      <div className="how-bottom-action">
        <button
          className="btn-primary"
          onClick={() => {
            onNavigate('operations');
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        >
          <span>OPEN OPERATIONS DASHBOARD</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
