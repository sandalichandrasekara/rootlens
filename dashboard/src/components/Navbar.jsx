import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const Navbar = () => {
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const navLinks = [
    { path: '/features', label: 'Features' },
    { path: '/pricing', label: 'Pricing' },
    { path: '/docs', label: 'Docs' },
    { path: '/contact', label: 'Contact' },
  ];

  return (
    <nav className="home-nav">
      <div className="nav-container">
        <Link to="/" className="nav-logo" onClick={() => setMobileOpen(false)}>
          <img src="/rootlens-preview.png" alt="RootLens" className="logo-image" />
          <span className="logo-text">RootLens</span>
        </Link>

        <button
          className="nav-hamburger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          )}
        </button>

        <div className={`nav-links ${mobileOpen ? 'nav-links--open' : ''}`}>
          {navLinks.map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={isActive(path) ? 'active' : ''}
              onClick={() => setMobileOpen(false)}
            >
              {label}
            </Link>
          ))}
          <button
            className="theme-toggle-btn-nav"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5" />
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="nav-backdrop" onClick={() => setMobileOpen(false)} />
      )}
    </nav>
  );
};

export default Navbar;
