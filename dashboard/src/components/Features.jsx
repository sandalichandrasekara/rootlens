import React from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const Features = () => {
  return (
    <div className="home-modern">
      <Navbar />

      <section className="page-hero">
        <div className="container">
          <div className="hero-badge">Kubernetes Scaling Intelligence</div>
          <h1>Powerful Capabilities</h1>
          <p>Everything you need to diagnose, understand, and optimize your Kubernetes autoscaling pipeline</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-header">
            <h2>Core Capabilities</h2>
            <p>Built for DevOps teams who need reliable, fast autoscaling diagnostics</p>
          </div>
          <div className="features-detail-grid">
            <div className="feature-detail-card">
              <div className="feature-detail-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                </svg>
              </div>
              <div className="feature-detail-content">
                <h3>Live Metrics Dashboard</h3>
                <p>Real-time monitoring of queue depth, pod count, and scaling events with interactive charts.</p>
                <ul className="feature-list">
                  <li>Real-time data streaming</li>
                  <li>Interactive time-range filters</li>
                  <li>Historical trend analysis</li>
                  <li>Queue depth visualization</li>
                </ul>
                <Link to="/dashboard" className="feature-link-btn">Explore Dashboard</Link>
              </div>
            </div>

            <div className="feature-detail-card">
              <div className="feature-detail-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 16v-4"/>
                  <path d="M12 8h.01"/>
                </svg>
              </div>
              <div className="feature-detail-content">
                <h3>Intelligent Root Cause Analysis</h3>
                <p>Automated detection and classification of scaling delays with confidence scoring.</p>
                <ul className="feature-list">
                  <li>Multiple root cause categories</li>
                  <li>Confidence scoring</li>
                  <li>Evidence-based analysis</li>
                  <li>Remediation suggestions</li>
                </ul>
                <Link to="/analysis" className="feature-link-btn">Try RCA Analysis</Link>
              </div>
            </div>

            <div className="feature-detail-card">
              <div className="feature-detail-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                </svg>
              </div>
              <div className="feature-detail-content">
                <h3>Workload Testing</h3>
                <p>Generate synthetic workloads to validate autoscaling behavior under various conditions.</p>
                <ul className="feature-list">
                  <li>Configurable message count</li>
                  <li>Adjustable message size</li>
                  <li>Spike mode for load testing</li>
                  <li>Queue purge functionality</li>
                </ul>
                <Link to="/workload" className="feature-link-btn">Generate Workloads</Link>
              </div>
            </div>

            <div className="feature-detail-card">
              <div className="feature-detail-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
              </div>
              <div className="feature-detail-content">
                <h3>RCA History & Export</h3>
                <p>Browse RCA results with confidence breakdowns, sub-cause details, and CSV export.</p>
                <ul className="feature-list">
                  <li>Last 50 RCA results</li>
                  <li>Per-result confidence breakdown</li>
                  <li>Sub-cause probability distribution</li>
                  <li>CSV export from live metrics</li>
                </ul>
                <Link to="/analysis" className="feature-link-btn">View RCA Results</Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-header">
            <h2>What We Detect</h2>
            <p>Key categories of scaling delays that impact Kubernetes autoscaling</p>
          </div>
          <div className="detect-cards">
            <div className="detect-card">
              <div className="detect-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
              </div>
              <h3>Pod Cold Start</h3>
              <p>Container image pull, initialization, and application startup delays.</p>
              <div className="detect-card-details">
                <span>Typical: 10-60s</span>
                <span>Impact: High</span>
              </div>
            </div>
            <div className="detect-card">
              <div className="detect-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
              </div>
              <h3>Scheduling Contention</h3>
              <p>Kubernetes scheduler delays due to resource constraints or affinity rules.</p>
              <div className="detect-card-details">
                <span>Typical: 5-30s</span>
                <span>Impact: Medium</span>
              </div>
            </div>
            <div className="detect-card">
              <div className="detect-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
              </div>
              <h3>Metric Propagation Lag</h3>
              <p>Delays in KEDA receiving queue metrics through the observability pipeline.</p>
              <div className="detect-card-details">
                <span>Typical: 15-45s</span>
                <span>Impact: Variable</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section final-cta-section">
        <div className="container cta-container">
          <h2>Ready to Get Started?</h2>
          <p>Launch the dashboard and start diagnosing scaling issues today</p>
          <div className="cta-buttons-row">
            <Link to="/dashboard" className="btn btn-primary btn-lg">Launch Dashboard</Link>
            <Link to="/docs" className="btn btn-secondary btn-lg">Read Documentation</Link>
          </div>
        </div>
      </section>

      <footer className="footer-modern">
        <div className="container">
          <div className="footer-links-row">
            <div className="footer-brand">
              <span className="footer-logo">RootLens</span>
              <p className="footer-tagline">Kubernetes scaling diagnostics, explained.</p>
            </div>
            <div className="footer-nav">
              <div className="footer-nav-group">
                <span className="footer-nav-label">Product</span>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/analysis">RCA Results</Link>
                <Link to="/metrics">Live Metrics</Link>
              </div>
              <div className="footer-nav-group">
                <span className="footer-nav-label">Resources</span>
                <Link to="/docs">Documentation</Link>
                <Link to="/docs">API Reference</Link>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 RootLens. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Features;
