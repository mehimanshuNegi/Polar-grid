import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import HowItWorksPage from './pages/HowItWorksPage';
import AiValidationPage from './pages/AiValidationPage';
import OperationsPage from './pages/OperationsPage';
import ResultsPage from './pages/ResultsPage';

export default function App() {
  // Page Routing State with Hash Support
  const getInitialPage = () => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const hash = window.location.hash.replace('#', '').toLowerCase();
      if (['home', 'how-it-works', 'validation', 'operations', 'results'].includes(hash)) {
        return hash;
      }
      if (hash === 'dashboard') {
        return 'operations';
      }
      if (hash === 'scenarios') {
        return 'results';
      }
    }
    return 'home';
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').toLowerCase();
      if (['home', 'how-it-works', 'validation', 'operations', 'results'].includes(hash)) {
        setCurrentPage(hash);
      } else if (hash === 'dashboard') {
        setCurrentPage('operations');
      } else if (hash === 'scenarios') {
        setCurrentPage('results');
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handlePageChange = (page) => {
    setCurrentPage(page);
    if (typeof window !== 'undefined') {
      window.location.hash = page;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Operational Settings (Strictly 24h/48h/72h rolling horizons, LIVE weather)
  const [horizon, setHorizon] = useState(24);
  const [loadingOps, setLoadingOps] = useState(false);

  // Simulated Equipment State (Prototype What-If Layer)
  const [batteryState, setBatteryState] = useState('NORMAL'); // 'NORMAL', 'LOW', 'CRITICAL'
  const [dieselState, setDieselState] = useState('NORMAL');   // 'NORMAL', 'LIMITED', 'CRITICAL'
  const [dispatchNotice, setDispatchNotice] = useState(null);
  const [operationsSummary, setOperationsSummary] = useState(null);

  // Simulation Settings for Results Page
  const [simSeason, setSimSeason] = useState('summer'); // 'summer' or 'winter'
  const [simHorizon, setSimHorizon] = useState(48); // 24, 48, 72
  const [loadingResults, setLoadingResults] = useState(false);

  // Data states
  const [stationInfo, setStationInfo] = useState({
    station: "Mawson Station",
    country: "Australia (AAD)",
    coordinates: { latitude: -67.6027, longitude: 62.8738 },
    status: "Operational",
    load_telemetry_note: "MODELED HOURLY LOAD — CALIBRATED TO REAL MAWSON MONTHLY ELECTRICITY DATA (AADC)"
  });

  const [scheduleData, setScheduleData] = useState([]);
  const [weatherMetadata, setWeatherMetadata] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [resultsData, setResultsData] = useState(null);

  // 1. Fetch Station Status (Once)
  useEffect(() => {
    fetch('/api/status')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setStationInfo(data); })
      .catch(() => null);

    fetch('/api/validation')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setValidationData(data); })
      .catch(() => null);
  }, []);

  // 2. Fetch Operational Schedule & Live Weather (Changes with horizon or equipment state)
  const fetchOperationsData = async (h = horizon, bState = batteryState, dState = dieselState) => {
    setLoadingOps(true);
    try {
      // Live ECMWF schedule with simulated equipment state
      const schedUrl = `/api/schedule?horizon=${h}&season=live&battery_state=${bState}&diesel_state=${dState}`;
      const schedRes = await fetch(schedUrl).catch(() => null);
      if (schedRes && schedRes.ok) {
        const sData = await schedRes.json();
        setScheduleData(sData.schedule || []);
        if (sData.weather_metadata) {
          setWeatherMetadata(sData.weather_metadata);
        }
        if (sData.summary) {
          setOperationsSummary(sData.summary);
        }
        return true;
      }
      return false;
    } catch (err) {
      console.warn("Operational data fetch issue:", err);
      return false;
    } finally {
      setLoadingOps(false);
    }
  };

  useEffect(() => {
    fetchOperationsData(horizon, batteryState, dieselState);
  }, [horizon]);

  // Handler for simulated equipment state changes (re-runs HiGHS dispatch)
  const handleUpdateEquipmentState = async (newBatState, newDslState) => {
    const nextB = newBatState !== undefined ? newBatState : batteryState;
    const nextD = newDslState !== undefined ? newDslState : dieselState;
    const success = await fetchOperationsData(horizon, nextB, nextD);
    if (success) {
      setBatteryState(nextB);
      setDieselState(nextD);
      setDispatchNotice("Dispatch updated");
      setTimeout(() => {
        setDispatchNotice(null);
      }, 3500);
      return true;
    } else {
      setDispatchNotice("Simulation update failed");
      setTimeout(() => {
        setDispatchNotice(null);
      }, 3500);
      return false;
    }
  };

  // 3. Fetch Results Simulation Data (Changes with simSeason or simHorizon)
  const resultsCacheRef = useRef({});
  const activeReqRef = useRef(null);

  const fetchResultsData = async (s, h) => {
    const key = `${s}_${h}`;
    if (resultsCacheRef.current[key]) {
      setResultsData(resultsCacheRef.current[key]);
      return;
    }
    setLoadingResults(true);
    activeReqRef.current = key;
    try {
      const res = await fetch(`/api/schedule?horizon=${h}&season=${s}`).catch(() => null);
      if (res && res.ok) {
        const data = await res.json();
        resultsCacheRef.current[key] = data;
        if (activeReqRef.current === key) {
          setResultsData(data);
        }
      }
    } catch (err) {
      console.warn("Results simulation fetch issue:", err);
    } finally {
      if (activeReqRef.current === key) {
        setLoadingResults(false);
      }
    }
  };

  useEffect(() => {
    fetchResultsData(simSeason, simHorizon);
  }, [simSeason, simHorizon]);

  return (
    <div className="site-wrapper">
      {/* Top Navigation Bar with Strict Weather Labeling */}
      <Navbar
        currentPage={currentPage}
        setCurrentPage={handlePageChange}
        weatherMetadata={weatherMetadata}
      />

      {/* Main Page Routing Container */}
      <main className="main-content-container">
        {currentPage === 'home' && (
          <HomePage onNavigate={handlePageChange} />
        )}

        {currentPage === 'how-it-works' && (
          <HowItWorksPage onNavigate={handlePageChange} />
        )}

        {currentPage === 'validation' && (
          <AiValidationPage
            validationData={validationData}
            onNavigate={handlePageChange}
          />
        )}

        {currentPage === 'operations' && (
          <OperationsPage
            horizon={horizon}
            setHorizon={(h) => {
              setHorizon(h);
              fetchOperationsData(h, batteryState, dieselState);
            }}
            loading={loadingOps}
            weatherMetadata={weatherMetadata}
            scheduleData={scheduleData}
            stationInfo={stationInfo}
            batteryState={batteryState}
            dieselState={dieselState}
            operationsSummary={operationsSummary}
            dispatchNotice={dispatchNotice}
            onUpdateEquipmentState={handleUpdateEquipmentState}
          />
        )}

        {currentPage === 'results' && (
          <ResultsPage
            simSeason={simSeason}
            setSimSeason={setSimSeason}
            simHorizon={simHorizon}
            setSimHorizon={setSimHorizon}
            resultsData={resultsData}
            loadingResults={loadingResults}
            onNavigate={handlePageChange}
          />
        )}
      </main>

      {/* Unified Site Footer */}
      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand-col">
            <span className="footer-brand-title">POLAR GRID</span>
            <span className="footer-brand-desc">
              AI-Assisted Renewable Energy Management System • Mawson Station, Antarctica
            </span>
          </div>
          <div className="footer-info-col">
            <span><strong>Station Location:</strong> 67.6027° S, 62.8738° E • Mac. Robertson Land</span>
            <span><strong>Weather Feed:</strong> ECMWF IFS Numerical Weather Prediction & ERA5 Reanalysis</span>
            <span><strong>Optimization:</strong> SciPy HiGHS Exact Linear Programming Solver</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
