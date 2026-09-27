import React from 'react';
import {
  Activity,
  Sun,
  Sliders,
  ArrowRight,
  Compass
} from 'lucide-react';

export default function HomePage({ onNavigate }) {
  return (
    <div className="home-dashboard">
      {/* ================================================================ */}
      {/* 1. HERO HEADER */}
      {/* ================================================================ */}
      <div className="home-hero-card">
        <div className="home-tag">ANTARCTIC CLEAN ENERGY MANAGEMENT</div>
        <h1 className="home-title">POLAR GRID</h1>
        <p className="home-problem-statement">
          Autonomous microgrid decision support to minimize expensive polar diesel fuel consumption while guaranteeing 100% electrical reliability for Mawson Station, Antarctica.
        </p>

        <div className="home-location-badge mono-text">
          <Compass size={14} className="text-teal" />
          <span>Mawson Station · 67.6027° S · 62.8738° E · Mac. Robertson Land</span>
        </div>

        <div className="home-cta-row">
          <button
            className="btn-home-primary"
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

      {/* ================================================================ */}
      {/* 2. THREE SIMPLE VISUAL BLOCKS (PREDICT, ESTIMATE, OPTIMIZE) */}
      {/* ================================================================ */}
      <div className="home-blocks-grid">
        {/* BLOCK 1: PREDICT */}
        <div className="home-block-card">
          <div className="block-step-badge">STEP 1</div>
          <div className="block-icon-wrapper">
            <Activity size={24} className="text-teal" />
          </div>
          <h2 className="block-title">PREDICT</h2>
          <div className="block-arrow-line">→ Forecast station demand</div>
          <p className="block-description">
            Models sub-zero heating load and scientific power requirements using thermal building equations and historical station occupancy dynamics.
          </p>
        </div>

        {/* BLOCK 2: ESTIMATE */}
        <div className="home-block-card">
          <div className="block-step-badge">STEP 2</div>
          <div className="block-icon-wrapper">
            <Sun size={24} className="text-teal" />
          </div>
          <h2 className="block-title">ESTIMATE</h2>
          <div className="block-arrow-line">→ Estimate renewable availability</div>
          <p className="block-description">
            Computes hourly wind turbine and solar PV potential directly from live ECMWF IFS numerical weather forecasts.
          </p>
        </div>

        {/* BLOCK 3: OPTIMIZE */}
        <div className="home-block-card">
          <div className="block-step-badge">STEP 3</div>
          <div className="block-icon-wrapper">
            <Sliders size={24} className="text-teal" />
          </div>
          <h2 className="block-title">OPTIMIZE</h2>
          <div className="block-arrow-line">→ Schedule renewable + battery + diesel</div>
          <p className="block-description">
            HiGHS linear programming solver determines optimal hourly battery charging, discharging, and minimal diesel generator dispatch.
          </p>
        </div>
      </div>
    </div>
  );
}
