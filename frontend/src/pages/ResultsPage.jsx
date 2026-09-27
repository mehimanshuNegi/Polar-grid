import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import {
  ShieldCheck,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function ResultsPage({
  simSeason,
  setSimSeason,
  simHorizon,
  setSimHorizon,
  resultsData,
  loadingResults,
  onNavigate
}) {
  const [techOpen, setTechOpen] = useState(false);

  const summary = resultsData?.summary || null;
  const schedule = resultsData?.schedule || [];

  // Chart data from actual backend simulation
  const chartData = useMemo(() => {
    return schedule.map((row, idx) => {
      const d = new Date(row.timestamp);
      const timeLabel = isNaN(d.getTime())
        ? `H+${idx}`
        : `${String(d.getHours()).padStart(2, '0')}:00`;

      return {
        time: timeLabel,
        demand: Math.round((row.predicted_demand_kw || 0) * 10) / 10,
        wind: Math.round((row.wind_generation_kw || 0) * 10) / 10,
        solar: Math.round((row.solar_generation_kw || 0) * 10) / 10,
        batteryDischarge: Math.round((row.battery_discharge_kw || 0) * 10) / 10,
        diesel: Math.round((row.diesel_generation_kw || 0) * 10) / 10
      };
    });
  }, [schedule]);

  // Actual simulation metrics from backend pipeline
  const baselineFuel = summary ? Math.round(summary.baseline_diesel_fuel_litres).toLocaleString() : "—";
  const optimizedFuel = summary ? Math.round(summary.optimized_diesel_fuel_litres).toLocaleString() : "—";
  const savedFuel = summary ? Math.round(summary.diesel_fuel_saved_litres).toLocaleString() : "—";
  const reductionPct = summary ? summary.diesel_reduction_percent.toFixed(1) : "—";

  return (
    <div className="results-dashboard">
      {/* ================================================================ */}
      {/* 1. HEADER */}
      {/* ================================================================ */}
      <div className="res-header-strip">
        <div>
          <h1 className="res-main-title">SCENARIO & BENCHMARK OUTCOMES</h1>
          <p className="res-sub-title">Multi-season dispatch evaluation across extreme Antarctic conditions</p>
        </div>

        <div className="res-provenance-tag">
          <span>Simulation Engine: HiGHS LP · Hourly Time Step</span>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 2. SCENARIO CONTROLS (Austral Summer, Polar Night, Live, 24/48/72H) */}
      {/* ================================================================ */}
      <div className="res-toolbar-strip">
        <div className="res-filter-group">
          <span className="res-filter-label">SEASON SCENARIO:</span>
          <div className="res-btn-group">
            <button
              className={`btn-res-pill ${simSeason === 'summer' ? 'active' : ''}`}
              onClick={() => setSimSeason('summer')}
            >
              Austral Summer (24h Sun)
            </button>
            <button
              className={`btn-res-pill ${simSeason === 'winter' ? 'active' : ''}`}
              onClick={() => setSimSeason('winter')}
            >
              Polar Night (Zero Sun)
            </button>
            <button
              className={`btn-res-pill ${simSeason === 'live' ? 'active' : ''}`}
              onClick={() => setSimSeason('live')}
            >
              Live ECMWF IFS
            </button>
          </div>
        </div>

        <div className="res-filter-group">
          <span className="res-filter-label">HORIZON:</span>
          <div className="res-btn-group">
            <button
              className={`btn-res-pill ${simHorizon === 24 ? 'active' : ''}`}
              onClick={() => setSimHorizon(24)}
            >
              24H
            </button>
            <button
              className={`btn-res-pill ${simHorizon === 48 ? 'active' : ''}`}
              onClick={() => setSimHorizon(48)}
            >
              48H
            </button>
            <button
              className={`btn-res-pill ${simHorizon === 72 ? 'active' : ''}`}
              onClick={() => setSimHorizon(72)}
            >
              72H
            </button>
          </div>
        </div>

        {loadingResults && (
          <div className="res-loading-indicator">
            <RefreshCw className="spinning" size={14} color="#397F80" />
            <span>Calculating...</span>
          </div>
        )}
      </div>

      {/* ================================================================ */}
      {/* 3. FOUR CORE COMPARISON METRICS */}
      {/* ================================================================ */}
      <div className="res-metrics-grid">
        <div className="res-metric-card">
          <span className="res-card-label">DIESEL BASELINE</span>
          <div className="res-card-number mono-text">{baselineFuel} <span className="unit">L</span></div>
          <span className="res-card-sub">100% uncoordinated diesel run</span>
        </div>

        <div className="res-metric-card">
          <span className="res-card-label">POLAR GRID</span>
          <div className="res-card-number mono-text text-teal">{optimizedFuel} <span className="unit">L</span></div>
          <span className="res-card-sub">Optimized microgrid dispatch</span>
        </div>

        <div className="res-metric-card">
          <span className="res-card-label">FUEL SAVED</span>
          <div className="res-card-number mono-text text-success">{savedFuel} <span className="unit">L</span></div>
          <span className="res-card-sub">Polar diesel fuel conserved</span>
        </div>

        <div className="res-metric-card res-highlight-card">
          <span className="res-card-label">FUEL REDUCTION</span>
          <div className="res-card-number mono-text">{reductionPct}%</div>
          <span className="res-card-sub">{simHorizon}h {simSeason} scenario outcome</span>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 4. MAIN COMPARISON CHART */}
      {/* ================================================================ */}
      <div className="res-chart-card">
        <div className="res-chart-header">
          <div>
            <h2 className="section-title">
              {simSeason === 'summer'
                ? 'AUSTRAL SUMMER DISPATCH STACK'
                : simSeason === 'winter'
                ? 'POLAR NIGHT DISPATCH STACK'
                : 'LIVE WEATHER OPERATIONAL DISPATCH'}
            </h2>
            <span className="section-subtitle">
              Power generation by source serving station electricity demand over {simHorizon} hours
            </span>
          </div>

          <div className="chart-clean-legend">
            <div className="legend-chip">
              <span className="legend-line" style={{ backgroundColor: '#397F80' }}></span>
              <span>Wind</span>
            </div>
            <div className="legend-chip">
              <span className="legend-line" style={{ backgroundColor: '#B98532' }}></span>
              <span>Solar</span>
            </div>
            <div className="legend-chip">
              <span className="legend-line" style={{ backgroundColor: '#8FB9C4' }}></span>
              <span>Battery</span>
            </div>
            <div className="legend-chip">
              <span className="legend-line" style={{ backgroundColor: '#B6534B' }}></span>
              <span>Diesel</span>
            </div>
          </div>
        </div>

        <div className="res-chart-canvas" style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 15, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E0D8" vertical={false} />
              <XAxis
                dataKey="time"
                stroke="#60727A"
                tick={{ fill: '#60727A', fontSize: 12, fontFamily: 'Source Sans 3' }}
                tickLine={false}
              />
              <YAxis
                stroke="#60727A"
                tick={{ fill: '#60727A', fontSize: 12, fontFamily: 'Source Sans 3' }}
                tickLine={false}
                unit=" kW"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E2E0D8',
                  borderRadius: 6,
                  color: '#18313B',
                  boxShadow: '0 2px 8px rgba(24, 49, 59, 0.08)',
                  fontSize: 13
                }}
              />
              <Area type="monotone" dataKey="wind" stackId="1" stroke="#397F80" fill="#397F80" fillOpacity={0.75} name="Wind Generation" />
              <Area type="monotone" dataKey="solar" stackId="1" stroke="#B98532" fill="#B98532" fillOpacity={0.75} name="Solar Generation" />
              <Area type="monotone" dataKey="batteryDischarge" stackId="1" stroke="#8FB9C4" fill="#8FB9C4" fillOpacity={0.75} name="Battery Discharge" />
              <Area type="monotone" dataKey="diesel" stackId="1" stroke="#B6534B" fill="#B6534B" fillOpacity={0.65} name="Diesel Backup" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 5. 12-MONTH SIMULATION BENCHMARK (41.45%) */}
      {/* ================================================================ */}
      <div className="res-benchmark-card">
        <div className="res-benchmark-top">
          <div className="res-benchmark-badge">
            <ShieldCheck size={16} color="#4F8064" />
            <span>PRE-COMPUTED SIMULATION BENCHMARK</span>
          </div>
          <span className="res-benchmark-period mono-text">8,736 Hourly Steps · Full Seasonal Cycle</span>
        </div>

        <div className="res-benchmark-main">
          <div className="res-benchmark-num-col">
            <span className="res-benchmark-value mono-text">41.45%</span>
            <span className="res-benchmark-caption">Projected annual diesel reduction — 12-month simulation benchmark</span>
          </div>

          <div className="res-benchmark-desc-col">
            <p>
              Calculated across a full sequential 8,736-hour Antarctic annual cycle incorporating summer midnight sun, extended polar darkness, seasonal blizzard events, and generator load curves.
            </p>
            <p className="res-benchmark-note">
              <strong>Technical Distinction:</strong> The 41.45% annual figure is an offline simulation benchmark. Polar Grid operational control operates rolling on 24–72 hour forecast horizons.
            </p>
          </div>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 6. TECHNICAL DETAILS (Progressive Disclosure) */}
      {/* ================================================================ */}
      <div className="progressive-accordion">
        <button
          className="accordion-trigger"
          onClick={() => setTechOpen(!techOpen)}
        >
          <div className="trigger-left">
            <Info size={16} className="text-teal" />
            <span>TECHNICAL DETAILS</span>
          </div>
          {techOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {techOpen && (
          <div className="accordion-content">
            <div className="tech-cards-grid">
              <div className="tech-spec-box">
                <h4>SUMMER SPECIFICATIONS</h4>
                <p>Continuous 24h solar radiation, peak solar irradiance ~700 W/m², persistent thermal demand offset by daytime battery charging.</p>
              </div>
              <div className="tech-spec-box">
                <h4>POLAR NIGHT SPECIFICATIONS</h4>
                <p>Solar generation strictly 0.0 kW (sub-horizon sun). Base station load met by persistent coastal katabatic wind turbines and battery buffer, with diesel automated throttling.</p>
              </div>
              <div className="tech-spec-box">
                <h4>OPTIMIZATION SOLVER</h4>
                <p>SciPy HiGHS interior point / simplex solver enforcing zero unmet load and exact power conservation at every hour.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
