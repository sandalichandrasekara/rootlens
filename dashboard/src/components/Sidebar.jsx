import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../styles/Sidebar.css';

const Sidebar = ({ isCollapsed, setIsCollapsed, mobileOpen, setMobileOpen }) => {
  const location = useLocation();

  const navItems = [
    {
      label: 'Home',
      path: '/dashboard',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      )
    },
    {
      label: 'Workloads',
      path: '/workload',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
      )
    },
    {
      label: 'Live Metrics',
      path: '/metrics',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
      )
    },
    {
      label: 'RCA Results',
      path: '/analysis',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
          <path d="M11 8v6"/>
          <path d="M8 11h6"/>
        </svg>
      )
    },
  ];

  const isActive = (path) => location.pathname === path;

  const handleNavClick = () => {
    if (mobileOpen) setMobileOpen(false);
  };

  return (
    <>
      {mobileOpen && (
        <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />
      )}
      <div className={`sidebar ${isCollapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          {!isCollapsed && (
            <Link to="/" className="logo-section">
              <img src="/rootlens-preview.png" alt="RootLens" className="logo-image" />
              <span className="logo-text">RootLens</span>
            </Link>
          )}
          <button
            className="collapse-btn desktop-only"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? 'Open sidebar' : 'Close sidebar'}
          >
            {isCollapsed ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12h18M3 6h18M3 18h18" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            )}
          </button>
          <button
            className="collapse-btn mobile-only"
            onClick={() => setMobileOpen(false)}
            title="Close sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
              title={isCollapsed ? item.label : ''}
              onClick={handleNavClick}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span className="nav-label">{item.label}</span>}
            </Link>
          ))}
        </nav>
      </div>
    </>
  );
};

export default Sidebar;
