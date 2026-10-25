import React, { useState } from 'react';
import Sidebar from './Sidebar';
import '../styles/DashboardLayout.css';

const DashboardLayout = ({ children, title }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className={`dashboard-layout ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <div className="mobile-topbar">
        <button
          className="mobile-menu-btn"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <span className="mobile-topbar-title">{title}</span>
      </div>

      <main className="main-content">
        {title && <div className="page-title">{title}</div>}
        <div className="content-area">{children}</div>
      </main>
    </div>
  );
};

export default DashboardLayout;
