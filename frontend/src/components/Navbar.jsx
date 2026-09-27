import React, { useState } from 'react';
import { Compass, Menu, X, Home, BookOpen, ShieldCheck, Activity, BarChart2, Radio } from 'lucide-react';

export default function Navbar({ currentPage, setCurrentPage, weatherMetadata }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'operations', label: 'Dashboard', icon: Activity },
    { id: 'validation', label: 'Validation', icon: ShieldCheck },
    { id: 'results', label: 'Scenarios', icon: BarChart2 },
    { id: 'how-it-works', label: 'How It Works', icon: BookOpen }
  ];

  const handleNavClick = (id) => {
    setCurrentPage(id);
    setMobileMenuOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isLive = Boolean(weatherMetadata?.is_live);
  const weatherLabel = isLive ? 'ECMWF IFS' : (weatherMetadata?.mode === 'cached' ? 'CACHED' : 'HISTORICAL');
  const updateTimestamp = weatherMetadata?.updated_at || 'Checking feed...';

  return (
    <header className="site-navbar">
      {/* Top Console Bar */}
      <div className="navbar-container">
        {/* Brand / Operations Header */}
        <div className="navbar-brand" onClick={() => handleNavClick('operations')} style={{ cursor: 'pointer' }}>
          <div className="brand-text-group">
            <div className="brand-title-row">
              <span className="brand-title">POLAR GRID</span>
              <span className="brand-location">Mawson Station, Antarctica</span>
            </div>
            <div className="brand-coords-row">
              <span className="brand-coords mono-text">67.6027° S · 62.8738° E</span>
            </div>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="navbar-links" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                className={`nav-link-btn ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                <Icon size={14} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Status & Live Weather Console Widget */}
        <div className="navbar-status-area">
          <div className={`nav-weather-badge ${isLive ? 'is-live' : 'is-fallback'}`}>
            <span className="status-dot"></span>
            <span className="weather-headline">{isLive ? 'LIVE ECMWF IFS' : weatherLabel}</span>
          </div>
          <span className="weather-time mono-text">Updated: {updateTimestamp}</span>
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          className="mobile-toggle-btn"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="mobile-nav-drawer">
          <div className="mobile-coords-banner">
            <span>Mawson Station · 67.6027° S · 62.8738° E</span>
            <span className="mobile-weather-pill">{isLive ? '● ECMWF LIVE' : '○ CACHED'}</span>
          </div>
          <div className="mobile-nav-items">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  className={`mobile-nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => handleNavClick(item.id)}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
