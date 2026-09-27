import React, { useState, useEffect, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import {
  Wind,
  Sun,
  Battery,
  Fuel,
  RefreshCw,
  Zap,
  ChevronDown,
  ChevronUp,
  Sliders,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  ShieldAlert,
  Info
} from 'lucide-react';

export default function OperationsPage({
  horizon,
  setHorizon,
  loading,
  weatherMetadata,
  scheduleData,
  stationInfo,
  batteryState = 'NORMAL',
  dieselState = 'NORMAL',
  operationsSummary,
  dispatchNotice,
  onUpdateEquipmentState
}) {
  const [techOpen, setTechOpen] = useState(false);
  const [showFullSchedule, setShowFullSchedule] = useState(false);

  // Simulation Setup local draft state
  const [selectedBattery, setSelectedBattery] = useState(batteryState || 'NORMAL');
  const [selectedDiesel, setSelectedDiesel] = useState(dieselState || 'NORMAL');
  const [simulationAppliedMessage, setSimulationAppliedMessage] = useState(false);
  const [simulationErrorMessage, setSimulationErrorMessage] = useState(false);

  useEffect(() => {
    if (batteryState) setSelectedBattery(batteryState);
  }, [batteryState]);

  useEffect(() => {
    if (dieselState) setSelectedDiesel(dieselState);
  }, [dieselState]);

  const handleApplySimulation = async () => {
    if (onUpdateEquipmentState) {
      const ok = await onUpdateEquipmentState(selectedBattery, selectedDiesel);
      if (ok !== false) {
        setSimulationAppliedMessage(true);
        setSimulationErrorMessage(false);
        setTimeout(() => {
          setSimulationAppliedMessage(false);
        }, 4000);
      } else {
        setSimulationErrorMessage(true);
        setSimulationAppliedMessage(false);
        setTimeout(() => {
          setSimulationErrorMessage(false);
        }, 4000);
      }
    }
  };

  // Simulated equipment initial assumptions vs optimizer projected dispatch
  const simulatedInitialSoc = operationsSummary?.initial_simulated_soc_percent ?? (batteryState === 'CRITICAL' ? 20 : batteryState === 'LOW' ? 25 : 50);
  const maxDieselAvailability = operationsSummary?.max_available_diesel_kw ?? (dieselState === 'CRITICAL' ? 125 : dieselState === 'LIMITED' ? 250 : 375);

  // Hour 0 current operational values directly from authoritative optimizer schedule & summary
  const current = scheduleData[0] || {};
  const currentDemand = operationsSummary?.current_demand_kw ?? Math.round((current.predicted_demand_kw ?? 0) * 10) / 10;
  const currentWindPower = operationsSummary?.current_wind_kw ?? Math.round((current.wind_generation_kw ?? 0) * 10) / 10;
  const currentSolarPower = operationsSummary?.current_solar_kw ?? Math.round((current.solar_generation_kw ?? 0) * 10) / 10;
  const currentTotalRenewable = Math.round((currentWindPower + currentSolarPower) * 10) / 10;

  const currentBatSoc = operationsSummary?.current_projected_soc_percent ?? Math.round((current.battery_soc_percent ?? 50) * 10) / 10;
  const currentBatCharge = operationsSummary?.current_battery_charge_kw ?? Math.round((current.battery_charge_kw ?? 0) * 10) / 10;
  const currentBatDischarge = operationsSummary?.current_battery_discharge_kw ?? Math.round((current.battery_discharge_kw ?? 0) * 10) / 10;
  const currentDieselPower = operationsSummary?.current_diesel_kw ?? Math.round((current.diesel_generation_kw ?? 0) * 10) / 10;
  const currentUnmet = operationsSummary?.current_unmet_demand_kw ?? Math.round((current.unmet_demand_kw ?? 0) * 10) / 10;

  const isCharging = currentBatCharge > 0.05;
  const isDischarging = currentBatDischarge > 0.05;
  const isDieselActive = currentDieselPower > 0.05;
  const isWindActive = currentWindPower > 0.05;
  const isSolarActive = currentSolarPower > 0.05;

  // Battery status text
  const batStatusText = isCharging
    ? `Charging (+${currentBatCharge.toFixed(1)} kW)`
    : isDischarging
    ? `Discharging (-${currentBatDischarge.toFixed(1)} kW)`
    : 'Standby';

  // Recommended Dispatch Decision (Dominant Action Hero)
  const recommendation = useMemo(() => {
    if (currentUnmet > 0.1) {
      return {
        title: "LOAD SHEDDING REQUIRED — INSUFFICIENT GENERATION",
        explanation: "Available renewable generation, battery reserves and diesel capacity cannot meet station demand.",
        type: "critical"
      };
    } else if (isDieselActive && isDischarging) {
      return {
        title: "WIND + BATTERY + DIESEL BACKUP",
        explanation: "Renewable energy and battery discharge serve base load with diesel generator covering the remaining deficit.",
        type: "warning"
      };
    } else if (isDieselActive) {
      return {
        title: "DIESEL BACKUP REQUIRED",
        explanation: "Renewable output and battery reserves are low; generator is providing necessary electrical backup.",
        type: "warning"
      };
    } else if (isCharging) {
      return {
        title: "USE RENEWABLES + CHARGE BATTERY",
        explanation: "Surplus renewable power is meeting total station load and recharging the 300 kWh battery storage.",
        type: "success"
      };
    } else if (isDischarging) {
      return {
        title: "USE RENEWABLES + DISCHARGE BATTERY",
        explanation: "Clean energy from wind, solar and battery storage meets 100% of station demand. Diesel remains OFF.",
        type: "success"
      };
    } else {
      return {
        title: "100% DIRECT RENEWABLE SUPPLY",
        explanation: "Station electricity demand is met entirely by direct wind and solar generation with zero diesel emissions.",
        type: "success"
      };
    }
  }, [currentUnmet, isDieselActive, isCharging, isDischarging]);

  // Chart data: Station Demand vs Renewable Available
  const chartData = useMemo(() => {
    return scheduleData.map((row, idx) => {
      const d = new Date(row.timestamp);
      const timeLabel = isNaN(d.getTime())
        ? `H+${idx}`
        : `${String(d.getHours()).padStart(2, '0')}:00`;

      const totalRen = (row.solar_generation_kw || 0) + (row.wind_generation_kw || 0);

      return {
        time: timeLabel,
        demand: Math.round((row.predicted_demand_kw || 0) * 10) / 10,
        renewable: Math.round(totalRen * 10) / 10
      };
    });
  }, [scheduleData]);

  // Dynamic Live Impact & Diesel Savings (Strictly derived from backend schedule & fuel model)
  const impactMetrics = useMemo(() => {
    // 1. Check if operationsSummary has the precomputed evaluated figures
    const baselineFuel = operationsSummary?.baseline_diesel_fuel_litres ?? operationsSummary?.baseline_diesel_litres;
    const optimizedFuel = operationsSummary?.optimized_diesel_fuel_litres ?? operationsSummary?.optimized_diesel_litres;
    const fuelSaved = operationsSummary?.diesel_fuel_saved_litres ?? operationsSummary?.diesel_saved_litres;
    const reductionPct = operationsSummary?.diesel_reduction_percent;
    const renCoveragePct = operationsSummary?.renewable_penetration_percent ?? operationsSummary?.renewable_coverage_percent;

    if (baselineFuel !== undefined && baselineFuel > 0 && optimizedFuel !== undefined) {
      const bFuel = Math.round(baselineFuel * 10) / 10;
      const oFuel = Math.round(optimizedFuel * 10) / 10;
      const sFuel = Math.max(0, Math.round((fuelSaved !== undefined ? fuelSaved : (bFuel - oFuel)) * 10) / 10);
      const redPct = Math.max(0, Math.round((reductionPct !== undefined ? reductionPct : ((sFuel / bFuel) * 100)) * 10) / 10);
      const covPct = Math.max(0, Math.round((renCoveragePct !== undefined ? renCoveragePct : 0) * 10) / 10);
      return {
        valid: true,
        baselineFuel: bFuel,
        optimizedFuel: oFuel,
        dieselAvoided: sFuel,
        reductionPercent: redPct,
        renewableCoverage: covPct
      };
    }

    // 2. Direct computation from actual schedule rows if summary is not yet available
    if (scheduleData && scheduleData.length > 0) {
      let totalDemandKwh = 0;
      let totalRenUsedKwh = 0;
      let totalOptimizedFuel = 0;
      let totalBaselineFuel = 0;

      // Fuel curve parameters: a = 0.24 L/kWh, b = 0.04 L/kW_rated, P_rated = 375.0 kW
      const fuelA = 0.24;
      const fuelB = 0.04;
      const pRated = operationsSummary?.diesel_capacity_kw ?? 375.0;

      scheduleData.forEach((row) => {
        const dKw = Number(row.predicted_demand_kw || 0);
        const renUsedKw = Number(row.renewable_used_kw || 0);
        const optFuel = Number(row.diesel_fuel_litres || 0);
        const baseFuel = (fuelA * dKw + fuelB * pRated) * 1.0;

        totalDemandKwh += dKw;
        totalRenUsedKwh += renUsedKw;
        totalOptimizedFuel += optFuel;
        totalBaselineFuel += baseFuel;
      });

      if (totalBaselineFuel > 0) {
        const bFuel = Math.round(totalBaselineFuel * 10) / 10;
        const oFuel = Math.round(totalOptimizedFuel * 10) / 10;
        const sFuel = Math.max(0, Math.round((bFuel - oFuel) * 10) / 10);
        const redPct = Math.max(0, Math.round(((sFuel / bFuel) * 100) * 10) / 10);
        const covPct = totalDemandKwh > 0 ? Math.max(0, Math.round(((totalRenUsedKwh / totalDemandKwh) * 100) * 10) / 10) : 0;
        return {
          valid: true,
          baselineFuel: bFuel,
          optimizedFuel: oFuel,
          dieselAvoided: sFuel,
          reductionPercent: redPct,
          renewableCoverage: covPct
        };
      }
    }

    return { valid: false };
  }, [operationsSummary, scheduleData]);

  // Weather metadata
  const isLive = Boolean(weatherMetadata?.is_live);
  const isCached = weatherMetadata?.mode === 'cached' || weatherMetadata?.source?.includes('Cached');
  const weatherLabel = isLive ? 'LIVE ECMWF IFS' : (isCached ? 'CACHED WEATHER' : 'HISTORICAL');
  const timestampPrefix = isLive ? 'Updated: ' : (isCached ? 'Cache updated: ' : 'Archive: ');
  const updateTimestamp = weatherMetadata?.updated_at || 'Checking feed...';

  // Alerts list from simulated equipment state
  const alerts = operationsSummary?.alerts || [];

  // Table rows preview
  const displayedRows = showFullSchedule ? scheduleData : scheduleData.slice(0, 6);

  return (
    <div className="operations-dashboard">
      {/* ================================================================ */}
      {/* 1. COMPACT PROFESSIONAL HEADER */}
      {/* ================================================================ */}
      <div className="ops-header-strip">
        <div className="ops-header-identity">
          <div className="ops-station-line">
            <span className="ops-station-title">POLAR GRID</span>
            <span className="ops-station-sep">·</span>
            <span className="ops-station-loc">Mawson Station, Antarctica</span>
          </div>
          <div className="ops-coords-line mono-text">
            67.6027° S · 62.8738° E
          </div>
        </div>

        <div className="ops-header-status-side">
          {dispatchNotice && (
            <span className="dispatch-badge">
              {dispatchNotice}
            </span>
          )}
          <div className="ops-live-tag">
            <span className="live-dot-teal"></span>
            <span className="live-tag-text">{weatherLabel}</span>
          </div>
          <span className="ops-update-time mono-text">
            {timestampPrefix}{updateTimestamp}
          </span>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 2. SIMULATION SETUP (COMPACT OPERATOR INPUT STRIP) */}
      {/* ================================================================ */}
      <section className="ops-section simulation-setup-section">
        <div className="sim-setup-card">
          <div className="sim-setup-header">
            <div className="sim-setup-title-group">
              <div className="sim-setup-title-row">
                <Sliders size={16} className="text-teal" />
                <h3 className="sim-setup-title">SIMULATION SETUP</h3>
              </div>
              <p className="sim-setup-subtitle">
                What-if equipment conditions — weather and historical data remain unchanged.
              </p>
            </div>

            <div className="sim-setup-disclaimer">
              <span className="sim-disclaimer-badge">SIMULATED EQUIPMENT</span>
              <span className="sim-disclaimer-note">
                These are prototype equipment assumptions, not live Mawson BMS/SCADA telemetry.
              </span>
            </div>
          </div>

          <div className="sim-setup-body">
            {/* Battery State Control */}
            <div className="sim-control-col">
              <div className="sim-control-label-row">
                <Battery size={14} className="text-teal" />
                <span className="sim-control-label">BATTERY STATE</span>
              </div>
              <div className="sim-btn-group">
                {['NORMAL', 'LOW', 'CRITICAL'].map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => setSelectedBattery(b)}
                    className={`sim-toggle-btn ${selectedBattery === b ? 'active' : ''} ${b === 'CRITICAL' ? 'btn-critical' : b === 'LOW' ? 'btn-warning' : 'btn-normal'}`}
                  >
                    {b}
                  </button>
                ))}
              </div>
              <div className="sim-control-desc">
                <div>Initial simulated SoC: <strong>{selectedBattery === 'CRITICAL' ? '20%' : selectedBattery === 'LOW' ? '25%' : '50%'}</strong></div>
                <div className="sim-subnote">(NORMAL = 50% · LOW = 25% · CRITICAL = 20%)</div>
              </div>
            </div>

            <div className="sim-divider-v"></div>

            {/* Diesel Availability Control */}
            <div className="sim-control-col">
              <div className="sim-control-label-row">
                <Fuel size={14} className="text-coral" />
                <span className="sim-control-label">DIESEL AVAILABILITY</span>
              </div>
              <div className="sim-btn-group">
                {['NORMAL', 'LIMITED', 'CRITICAL'].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setSelectedDiesel(d)}
                    className={`sim-toggle-btn ${selectedDiesel === d ? 'active' : ''} ${d === 'CRITICAL' ? 'btn-critical' : d === 'LIMITED' ? 'btn-warning' : 'btn-normal'}`}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <div className="sim-control-desc">
                <div>Maximum available generation: <strong>{selectedDiesel === 'CRITICAL' ? '125 kW' : selectedDiesel === 'LIMITED' ? '250 kW' : '375 kW'}</strong></div>
                <div className="sim-subnote">({selectedDiesel === 'CRITICAL' ? '1 generator available' : selectedDiesel === 'LIMITED' ? '2 generators available' : '3 generators available'})</div>
              </div>
            </div>

            <div className="sim-divider-v"></div>

            {/* Action Column */}
            <div className="sim-action-col">
              <button
                type="button"
                onClick={handleApplySimulation}
                className="btn-apply-simulation"
                disabled={loading}
              >
                <RefreshCw size={14} className={loading ? "spinning" : ""} />
                <span>APPLY SIMULATION</span>
              </button>

              {simulationAppliedMessage && (
                <div className="sim-status-message">
                  ✓ Simulation applied — dispatch updated
                </div>
              )}

              {simulationErrorMessage && (
                <div className="sim-status-message" style={{ color: 'var(--color-critical)' }}>
                  ⚠ Simulation update failed — previous state retained
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* ALERTS (Small unobtrusive alert banners) */}
      {/* ================================================================ */}
      {alerts.length > 0 && (
        <div className="ops-alerts-row">
          {alerts.map((alertMsg, idx) => (
            <div
              key={idx}
              className={`ops-alert-banner ${alertMsg.includes('🔴') ? 'alert-critical' : 'alert-warning'}`}
            >
              <AlertTriangle size={15} />
              <span>{alertMsg}</span>
            </div>
          ))}
        </div>
      )}

      {/* ================================================================ */}
      {/* 3. CURRENT POWER */}
      {/* ================================================================ */}
      <section className="ops-section current-power-section">
        <div className="section-head-row">
          <h2 className="section-title">CURRENT POWER</h2>
          <span className="section-subtitle">Current modeled power balance and operational status</span>
        </div>

        <div className="current-power-container">
          {/* Dominant Station Demand Card */}
          <div className="demand-dominant-card">
            <div className="demand-card-header">
              <span className="demand-tag">STATION DEMAND</span>
              <span className="demand-status-chip">
                {currentTotalRenewable >= currentDemand ? "100% Clean Met" : `${Math.round((currentTotalRenewable / Math.max(1, currentDemand)) * 100)}% Renewable`}
              </span>
            </div>
            <div className="demand-main-number">
              <span className="demand-val">{currentDemand}</span>
              <span className="demand-unit">kW</span>
            </div>
            <div className="demand-card-meta">
              <span>Scientific labs, life support & thermal heating load</span>
            </div>
          </div>

          {/* 4 Compact Source Metric Cards */}
          <div className="source-cards-grid">
            {/* WIND */}
            <div className={`source-card ${isWindActive ? 'is-active' : 'is-idle'}`}>
              <div className="source-card-top">
                <div className="source-card-icon-group">
                  <Wind size={16} className="text-teal" />
                  <span className="source-name">WIND</span>
                </div>
                <span className={`source-status-badge ${isWindActive ? 'badge-active' : 'badge-idle'}`}>
                  {isWindActive ? 'Available' : 'Calm'}
                </span>
              </div>
              <div className="source-power-row">
                <span className="source-number">{currentWindPower}</span>
                <span className="source-unit">kW</span>
              </div>
              <span className="source-footnote">2 × 100 kW turbines</span>
            </div>

            {/* SOLAR */}
            <div className={`source-card ${isSolarActive ? 'is-active' : 'is-idle'}`}>
              <div className="source-card-top">
                <div className="source-card-icon-group">
                  <Sun size={16} className="text-teal" />
                  <span className="source-name">SOLAR</span>
                </div>
                <span className={`source-status-badge ${isSolarActive ? 'badge-active' : 'badge-idle'}`}>
                  {isSolarActive ? 'Available' : 'Darkness'}
                </span>
              </div>
              <div className="source-power-row">
                <span className="source-number">{currentSolarPower}</span>
                <span className="source-unit">kW</span>
              </div>
              <span className="source-footnote">100 kW PV array</span>
            </div>

            {/* BATTERY */}
            <div className={`source-card ${isCharging || isDischarging ? 'is-active' : 'is-idle'}`}>
              <div className="source-card-top">
                <div className="source-card-icon-group">
                  <Battery size={16} className="text-teal" />
                  <span className="source-name">BATTERY</span>
                </div>
                <span className={`source-status-badge ${isCharging ? 'badge-charge' : isDischarging ? 'badge-discharge' : 'badge-idle'}`}>
                  {isCharging ? 'Charging' : isDischarging ? 'Discharging' : 'Standby'}
                </span>
              </div>
              <div className="source-power-row">
                <span className="source-number">{currentBatSoc}%</span>
                <span className="source-unit">Projected</span>
              </div>
              <div className="source-detail-lines">
                <div className="source-detail-line">Initial simulated SoC: <strong>{simulatedInitialSoc}%</strong></div>
                <div className="source-detail-line">Current projected SoC: <strong>{currentBatSoc}%</strong></div>
                <div className="source-detail-line">Status: <strong>{isCharging ? `Charging (+${currentBatCharge} kW)` : isDischarging ? `Discharging (-${currentBatDischarge} kW)` : 'Standby'}</strong></div>
              </div>
            </div>

            {/* DIESEL */}
            <div className={`source-card ${isDieselActive ? 'is-alert' : 'is-idle'}`}>
              <div className="source-card-top">
                <div className="source-card-icon-group">
                  <Fuel size={16} className={isDieselActive ? 'text-coral' : 'text-muted'} />
                  <span className="source-name">DIESEL</span>
                </div>
                <span className={`source-status-badge ${isDieselActive ? 'badge-active-diesel' : 'badge-standby'}`}>
                  {isDieselActive ? 'Dispatched' : 'Standby'}
                </span>
              </div>
              <div className="source-power-row">
                <span className="source-number">{currentDieselPower}</span>
                <span className="source-unit">kW</span>
              </div>
              <div className="source-detail-lines">
                <div className="source-detail-line">Simulated availability: <strong>{dieselState} ({maxDieselAvailability} kW)</strong></div>
                <div className="source-detail-line">Modeled dispatch: <strong>{currentDieselPower} kW</strong></div>
                <div className="source-detail-line">Max generators: <strong>{dieselState === 'CRITICAL' ? '1 of 3' : dieselState === 'LIMITED' ? '2 of 3' : '3 of 3'} available</strong></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* 4. ENERGY FLOW (SINGLE-LINE MICROGRID POWER FLOW) */}
      {/* ================================================================ */}
      <section className="ops-section energy-flow-section">
        <div className="schematic-container">
          <div className="schematic-header">
            <div>
              <span className="schematic-title">ENERGY FLOW — SINGLE-LINE MICROGRID POWER ROUTING</span>
              <span className="schematic-sub">Dynamic routing calculated by HiGHS LP</span>
            </div>
          </div>

          <div className="schematic-diagram-wrapper">
            <svg
              className="schematic-svg"
              viewBox="0 0 860 220"
              preserveAspectRatio="xMidYMid meet"
            >
              <defs>
                <marker
                  id="arrow-teal"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#397F80" />
                </marker>
                <marker
                  id="arrow-green"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#4F8064" />
                </marker>
                <marker
                  id="arrow-coral"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#B6534B" />
                </marker>
                <marker
                  id="arrow-muted"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#A4B3B6" />
                </marker>
              </defs>

              {/* 1. SOURCES COLUMN (Left: X=10 to 180) */}
              {/* Wind Node */}
              <rect x="20" y="15" width="160" height="38" rx="6" className={`node-rect ${isWindActive ? 'node-active' : 'node-idle'}`} />
              <text x="35" y="38" className="node-label">WIND</text>
              <text x="165" y="38" textAnchor="end" className="node-val mono-text">{currentWindPower} kW</text>

              {/* Solar Node */}
              <rect x="20" y="65" width="160" height="38" rx="6" className={`node-rect ${isSolarActive ? 'node-active' : 'node-idle'}`} />
              <text x="35" y="88" className="node-label">SOLAR</text>
              <text x="165" y="88" textAnchor="end" className="node-val mono-text">{currentSolarPower} kW</text>

              {/* Battery Node */}
              <rect x="20" y="115" width="160" height="38" rx="6" className={`node-rect ${isCharging || isDischarging ? 'node-active' : 'node-idle'}`} />
              <text x="35" y="138" className="node-label">BATTERY</text>
              <text x="165" y="138" textAnchor="end" className="node-val mono-text">
                {isCharging ? `+${currentBatCharge} kW` : isDischarging ? `-${currentBatDischarge} kW` : '0 kW'}
              </text>

              {/* Diesel Node */}
              <rect x="20" y="165" width="160" height="38" rx="6" className={`node-rect ${isDieselActive ? 'node-critical' : 'node-idle'}`} />
              <text x="35" y="188" className="node-label">DIESEL</text>
              <text x="165" y="188" textAnchor="end" className="node-val mono-text">{currentDieselPower} kW</text>

              {/* 2. CONNECTING LINES TO BUS (X=180 to X=420) */}
              {/* Wind Line */}
              <path
                d="M 180 34 L 380 34 L 380 110 L 420 110"
                fill="none"
                stroke={isWindActive ? "#397F80" : "#D4D2C9"}
                strokeWidth={isWindActive ? "2.5" : "1.5"}
                strokeDasharray={isWindActive ? "none" : "4 4"}
                markerEnd={isWindActive ? "url(#arrow-teal)" : undefined}
              />

              {/* Solar Line */}
              <path
                d="M 180 84 L 340 84 L 340 110 L 420 110"
                fill="none"
                stroke={isSolarActive ? "#397F80" : "#D4D2C9"}
                strokeWidth={isSolarActive ? "2.5" : "1.5"}
                strokeDasharray={isSolarActive ? "none" : "4 4"}
                markerEnd={isSolarActive ? "url(#arrow-teal)" : undefined}
              />

              {/* Battery Line (Bidirectional) */}
              {isCharging ? (
                /* Flow: Busbar -> Battery */
                <path
                  d="M 420 134 L 340 134 L 340 134 L 180 134"
                  fill="none"
                  stroke="#4F8064"
                  strokeWidth="2.5"
                  markerEnd="url(#arrow-green)"
                />
              ) : (
                /* Flow: Battery -> Busbar (or idle) */
                <path
                  d="M 180 134 L 340 134 L 340 110 L 420 110"
                  fill="none"
                  stroke={isDischarging ? "#8FB9C4" : "#D4D2C9"}
                  strokeWidth={isDischarging ? "2.5" : "1.5"}
                  strokeDasharray={isDischarging ? "none" : "4 4"}
                  markerEnd={isDischarging ? "url(#arrow-teal)" : undefined}
                />
              )}

              {/* Diesel Line */}
              <path
                d="M 180 184 L 380 184 L 380 110 L 420 110"
                fill="none"
                stroke={isDieselActive ? "#B6534B" : "#D4D2C9"}
                strokeWidth={isDieselActive ? "2.5" : "1.5"}
                strokeDasharray={isDieselActive ? "none" : "4 4"}
                markerEnd={isDieselActive ? "url(#arrow-coral)" : undefined}
              />

              {/* 3. MICROGRID BUSBAR (Center: X=420 to X=460) */}
              <rect x="420" y="30" width="22" height="160" rx="3" fill="#18313B" />
              <text
                x="431"
                y="110"
                fill="#FFFFFF"
                fontSize="9"
                fontWeight="700"
                fontFamily="sans-serif"
                textAnchor="middle"
                transform="rotate(-90 431 110)"
                letterSpacing="1.2"
              >
                MICROGRID BUS (415V)
              </text>

              {/* 4. LINE FROM BUSBAR TO STATION DEMAND (X=442 to X=620) */}
              <line
                x1="442"
                y1="110"
                x2="615"
                y2="110"
                stroke="#397F80"
                strokeWidth="3.5"
                markerEnd="url(#arrow-teal)"
              />

              {/* 5. STATION DEMAND LOAD SINK (Right: X=620 to 830) */}
              <rect x="620" y="65" width="215" height="90" rx="8" className="node-sink" />
              <text x="635" y="93" className="sink-label">STATION DEMAND</text>
              <text x="635" y="125" className="sink-number mono-text">{currentDemand} kW</text>
              <text x="635" y="145" className="sink-sub">Mawson Station Core Load</text>
            </svg>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* 5. RECOMMENDED ACTION (One dominant clean card) */}
      {/* ================================================================ */}
      <section className="ops-section">
        <div className={`recommendation-card rec-${recommendation.type}`}>
          <div className="rec-top-row">
            <span className="rec-badge-label">RECOMMENDED ACTION</span>
            <span className="rec-engine-tag mono-text">HiGHS OPTIMIZER</span>
          </div>

          <h3 className="rec-headline">{recommendation.title}</h3>
          <p className="rec-explanation">{recommendation.explanation}</p>

          <div className="rec-source-breakdown">
            <div className="rec-breakdown-item">
              <span className="rb-label">Wind</span>
              <span className="rb-val mono-text">{currentWindPower} kW</span>
            </div>
            <span className="rb-divider">|</span>
            <div className="rec-breakdown-item">
              <span className="rb-label">Solar</span>
              <span className="rb-val mono-text">{currentSolarPower} kW</span>
            </div>
            <span className="rb-divider">|</span>
            <div className="rec-breakdown-item">
              <span className="rb-label">Battery</span>
              <span className="rb-val mono-text">
                {isCharging ? `+${currentBatCharge} kW` : isDischarging ? `-${currentBatDischarge} kW` : `${currentBatSoc}% SoC`}
              </span>
            </div>
            <span className="rb-divider">|</span>
            <div className="rec-breakdown-item">
              <span className="rb-label">Diesel</span>
              <span className="rb-val mono-text">{currentDieselPower} kW</span>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* 6. POLAR GRID IMPACT / DIESEL SAVINGS PANEL (LIVE HORIZON) */}
      {/* ================================================================ */}
      <section className="ops-section">
        <div className="impact-panel-card">
          <div className="impact-header-row">
            <div>
              <div className="impact-title-group">
                <h3 className="impact-title">POLAR GRID IMPACT</h3>
                <span className="impact-badge-horizon mono-text">NEXT {horizon} HOURS</span>
                <span className="impact-badge-mode">LIVE HORIZON IMPACT</span>
              </div>
              <p className="impact-subtitle">
                Diesel use vs 100% diesel baseline for selected planning horizon
              </p>
            </div>
            <div className="impact-provenance-tag mono-text">
              <span>HiGHS Optimizer Dispatch</span>
            </div>
          </div>

          {!impactMetrics.valid ? (
            <div className="impact-unavailable-state">
              <span>Impact data unavailable for this horizon</span>
            </div>
          ) : (
            <div className="impact-content-grid">
              {/* Primary Metric: Reduction Percentage */}
              <div className="impact-primary-col">
                <span className="impact-primary-caption">DIESEL REDUCTION</span>
                <div className="impact-primary-value-row">
                  <span className="impact-big-percent mono-text">
                    {impactMetrics.reductionPercent.toFixed(1)}%
                  </span>
                </div>
                <span className="impact-primary-sub">
                  vs 100% Diesel Baseline ({horizon}h)
                </span>
              </div>

              {/* Center: Comparison Bars */}
              <div className="impact-bars-col">
                <div className="impact-bars-header">
                  <span className="bars-title">DIESEL USE — SELECTED HORIZON</span>
                  <span className="bars-sub mono-text">Total Fuel Consumed</span>
                </div>

                <div className="comparison-bars-wrapper">
                  {/* Baseline Bar */}
                  <div className="comp-bar-group">
                    <div className="comp-bar-meta">
                      <span className="bar-label">Diesel-Only Baseline</span>
                      <span className="bar-val mono-text">{impactMetrics.baselineFuel.toLocaleString()} L</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill bar-fill-baseline" style={{ width: '100%' }}></div>
                    </div>
                  </div>

                  {/* Polar Grid Bar */}
                  <div className="comp-bar-group">
                    <div className="comp-bar-meta">
                      <span className="bar-label text-teal">Polar Grid</span>
                      <span className="bar-val text-teal mono-text">{impactMetrics.optimizedFuel.toLocaleString()} L</span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill bar-fill-polargrid"
                        style={{
                          width: `${Math.min(100, Math.max(3, (impactMetrics.optimizedFuel / Math.max(1, impactMetrics.baselineFuel)) * 100))}%`
                        }}
                      ></div>
                    </div>
                  </div>
                </div>

                {/* Diesel Avoided Callout */}
                <div className="diesel-avoided-callout">
                  {impactMetrics.dieselAvoided > 0 ? (
                    <div className="avoided-pill-success">
                      <span className="avoided-arrow">↓</span>
                      <strong className="avoided-num mono-text">{impactMetrics.dieselAvoided.toLocaleString()} L</strong>
                      <span className="avoided-label">DIESEL AVOIDED</span>
                    </div>
                  ) : (
                    <div className="avoided-pill-neutral">
                      <strong className="avoided-num mono-text">0 L</strong>
                      <span className="avoided-label">No diesel reduction in this horizon</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Secondary Metric: Renewable Coverage */}
              <div className="impact-secondary-col">
                <div className="coverage-metric-box">
                  <span className="coverage-label">RENEWABLE COVERAGE</span>
                  <div className="coverage-val mono-text">
                    {impactMetrics.renewableCoverage.toFixed(1)}%
                  </div>
                  <span className="coverage-sub">
                    Actual wind + solar energy used to serve station demand
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ================================================================ */}
      {/* 7. NEXT 24/48/72 HOURS (Primary Forecast Visualization) */}
      {/* ================================================================ */}
      <section className="ops-section">
        <div className="chart-card-wrapper">
          <div className="chart-header-row">
            <div>
              <h2 className="section-title">NEXT {horizon} HOURS FORECAST</h2>
              <span className="section-subtitle">
                Station electrical demand vs predicted total renewable generation (Wind + Solar)
              </span>
            </div>

            <div className="chart-toolbar">
              {/* Horizon Selector */}
              <div className="horizon-btn-group">
                <button
                  className={`btn-horizon ${horizon === 24 ? 'active' : ''}`}
                  onClick={() => setHorizon(24)}
                >
                  24H
                </button>
                <button
                  className={`btn-horizon ${horizon === 48 ? 'active' : ''}`}
                  onClick={() => setHorizon(48)}
                >
                  48H
                </button>
                <button
                  className={`btn-horizon ${horizon === 72 ? 'active' : ''}`}
                  onClick={() => setHorizon(72)}
                >
                  72H
                </button>
              </div>

              {/* Chart Legend */}
              <div className="chart-clean-legend">
                <div className="legend-chip">
                  <span className="legend-line line-teal"></span>
                  <span>Station Demand</span>
                </div>
                <div className="legend-chip">
                  <span className="legend-line line-ice"></span>
                  <span>Renewable Available</span>
                </div>
              </div>
            </div>
          </div>

          <div className="chart-canvas-area" style={{ width: '100%', height: 320 }}>
            {loading ? (
              <div className="chart-loading-state">
                <RefreshCw className="spinning" size={24} color="#397F80" />
                <span>Solving optimal dispatch with HiGHS...</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 15, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E0D8" vertical={false} />
                  <XAxis
                    dataKey="time"
                    stroke="#60727A"
                    tick={{ fill: '#60727A', fontSize: 12, fontFamily: 'Source Sans 3' }}
                    tickLine={false}
                    interval={horizon === 24 ? 2 : horizon === 48 ? 4 : 6}
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
                  <Line
                    type="monotone"
                    dataKey="demand"
                    name="Station Demand"
                    stroke="#18313B"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5, fill: '#18313B' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="renewable"
                    name="Renewable Available"
                    stroke="#397F80"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5, fill: '#397F80' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* 8. SCHEDULE (Short preview initially, expandable) */}
      {/* ================================================================ */}
      <section className="ops-section">
        <div className="schedule-card-wrapper">
          <div className="schedule-header-row">
            <div>
              <h3 className="section-title">SCHEDULE PREVIEW</h3>
              <span className="section-subtitle">
                Hourly dispatch decisions solved by the HiGHS linear programming optimizer
              </span>
            </div>

            <button
              className="btn-toggle-schedule"
              onClick={() => setShowFullSchedule(!showFullSchedule)}
            >
              {showFullSchedule ? `SHOW PREVIEW (6 HOURS)` : `VIEW FULL SCHEDULE (${scheduleData.length} HOURS)`}
            </button>
          </div>

          <div className="schedule-table-container">
            <table className="ops-schedule-table">
              <thead>
                <tr>
                  <th>TIME</th>
                  <th>DEMAND</th>
                  <th>RENEWABLE</th>
                  <th>BATTERY</th>
                  <th>DIESEL</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map((row, idx) => {
                  const d = new Date(row.timestamp);
                  const timeStr = isNaN(d.getTime())
                    ? `H+${idx}`
                    : `${String(d.getHours()).padStart(2, '0')}:00`;

                  const batCharge = row.battery_charge_kw || 0;
                  const batDischarge = row.battery_discharge_kw || 0;
                  const batText = batCharge > 0.05
                    ? `+${batCharge.toFixed(1)} kW (Chg)`
                    : batDischarge > 0.05
                    ? `-${batDischarge.toFixed(1)} kW (Dis)`
                    : `${(row.battery_soc_percent || 50).toFixed(0)}% SoC`;

                  const totalRen = (row.solar_generation_kw || 0) + (row.wind_generation_kw || 0);
                  const dslKw = row.diesel_generation_kw || 0;

                  return (
                    <tr key={idx} className={idx === 0 ? "row-now" : ""}>
                      <td className="mono-text">
                        <strong>{timeStr}</strong>
                        {idx === 0 && <span className="now-pill">NOW</span>}
                      </td>
                      <td className="mono-text">{Number(row.predicted_demand_kw || 0).toFixed(1)} kW</td>
                      <td className="mono-text text-teal">{Number(totalRen).toFixed(1)} kW</td>
                      <td className="mono-text">{batText}</td>
                      <td className="mono-text">
                        {dslKw > 0.05 ? (
                          <span className="text-coral">{dslKw.toFixed(1)} kW</span>
                        ) : (
                          <span className="text-muted">0.0 kW (Off)</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/* 11. TECHNICAL DETAILS (Progressive Disclosure) */}
      {/* ================================================================ */}
      <section className="ops-section">
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
                  <h4>HiGHS LINEAR PROGRAM</h4>
                  <p>
                    Exact linear programming formulation minimizing total diesel fuel penalty and unserved load penalties over the {horizon}-hour planning horizon subject to continuous energy balance.
                  </p>
                </div>

                <div className="tech-spec-box">
                  <h4>BATTERY SPECIFICATION</h4>
                  <p>
                    300 kWh lithium iron phosphate (LiFePO4) storage, maximum 100 kW charge/discharge rate, 90% roundtrip efficiency, bounded strictly between 20% minimum SoC and 95% maximum SoC.
                  </p>
                </div>

                <div className="tech-spec-box">
                  <h4>DIESEL SPECIFICATION</h4>
                  <p>
                    Three 125 kW generator sets (375 kW nominal total). Linear fuel curve: 0.24 L/kWh generated + 0.04 L/kW rated capacity.
                  </p>
                </div>

                <div className="tech-spec-box">
                  <h4>DATA PROVENANCE</h4>
                  <p>
                    ECMWF IFS operational forecast feed via Open-Meteo API. Historical hourly benchmarks calibrated from official Australian Antarctic Data Centre (AADC) station monthly records.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
