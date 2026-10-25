import React from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const Home = () => {
  return (
    <div className="home-modern">
      <Navbar />

      <section className="hero-modern">
        <div className="hero-container">
          <div className="hero-content">
            <div className="hero-badge">Kubernetes Scaling Intelligence</div>
            <h1 className="hero-title">
              Diagnose Kubernetes Scaling Delays Instantly
            </h1>
            <p className="hero-description">
              Stop guessing. Start resolving scaling failures with RootLens.
            </p>
            <div className="hero-buttons">
              <Link to="/dashboard" className="btn btn-primary btn-lg">
                Launch Dashboard
              </Link>
              <Link to="/docs" className="btn btn-secondary btn-lg">
                View Documentation
              </Link>
            </div>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <div className="stat-number">Automated</div>
              <div className="stat-text">Root Cause Detection</div>
            </div>
            <div className="stat">
              <div className="stat-number">Real Time</div>
              <div className="stat-text">Pipeline Monitoring</div>
            </div>
            <div className="stat">
              <div className="stat-number">ML Powered</div>
              <div className="stat-text">Confidence Scoring</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section problem-section">
        <div className="container">
          <div className="section-header">
            <h2>The Hidden Problem in Kubernetes Autoscaling</h2>
            <p>Scaling delays are hard to diagnose. The root cause is often invisible.</p>
          </div>
          <div className="problems-grid">
            <div className="problem-card">
              <div className="card-number">1</div>
              <h3>Invisible Bottlenecks</h3>
              <p>Pods scale slowly, but why? Cold start delays, scheduling contention, or metric lag remain hidden.</p>
            </div>
            <div className="problem-card">
              <div className="card-number">2</div>
              <h3>Time-Consuming Debugging</h3>
              <p>Manually correlating RabbitMQ, Kubernetes, and KEDA logs drains engineering resources.</p>
            </div>
            <div className="problem-card">
              <div className="card-number">3</div>
              <h3>Misguided Optimizations</h3>
              <p>Without precise diagnosis, teams optimize the wrong components and miss the real culprit.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section solution-section">
        <div className="container">
          <div className="section-header">
            <h2>Meet RootLens</h2>
            <p>Automated root cause detection for Kubernetes autoscaling pipelines</p>
          </div>
          <div className="solution-content">
            <div className="solution-text">
              <h3>Stop Correlating Logs Manually</h3>
              <p>
                RootLens continuously monitors your autoscaling pipeline, correlates signals from RabbitMQ,
                Kubernetes, and KEDA, then pinpoints the exact bottleneck causing delays.
              </p>
              <ul className="solution-list">
                <li>Instant classification of scaling delay root causes</li>
                <li>ML-enhanced confidence scoring with explainability</li>
                <li>Actionable remediation recommendations per root cause</li>
                <li>Historical insights for continuous improvement</li>
              </ul>
              <Link to="/dashboard" className="btn btn-secondary">
                Explore the Dashboard
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section how-it-works-modern">
        <div className="container">
          <div className="section-header">
            <h2>How It Works</h2>
            <p>Three steps from cluster connection to root cause diagnosis</p>
          </div>
          <div className="problems-grid">
            <div className="problem-card">
              <div className="card-number">1</div>
              <h3>Connect</h3>
              <p>Deploy RootLens alongside your cluster. It connects to KEDA, RabbitMQ, and Prometheus, no code changes needed.</p>
            </div>
            <div className="problem-card">
              <div className="card-number">2</div>
              <h3>Monitor</h3>
              <p>RootLens continuously ingests pod events, queue depth, and scaling signals to track your autoscaling pipeline in real time.</p>
            </div>
            <div className="problem-card">
              <div className="card-number">3</div>
              <h3>Diagnose</h3>
              <p>When a delay occurs, the rule-based engine and ML explainer pinpoint the root cause and surface a clear, actionable recommendation.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section benefits-modern">
        <div className="container">
          <div className="section-header">
            <h2>Why Teams Choose RootLens</h2>
            <p>Built for engineering teams that need reliable, fast autoscaling</p>
          </div>
          <div className="benefits-cards">
            <div className="benefit-card">
              <div className="benefit-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              </div>
              <h3>Fast Diagnosis</h3>
              <p>Get answers in seconds instead of hours of manual debugging</p>
            </div>
            <div className="benefit-card">
              <div className="benefit-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
                  <path d="M22 12A10 10 0 0 0 12 2v10z"/>
                </svg>
              </div>
              <h3>Data-Driven</h3>
              <p>Make infrastructure decisions backed by real evidence and metrics</p>
            </div>
            <div className="benefit-card">
              <div className="benefit-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  <polyline points="9 12 11 14 15 10"/>
                </svg>
              </div>
              <h3>Better SLAs</h3>
              <p>Meet performance targets with faster troubleshooting and resolution</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section dashboard-preview-section">
        <div className="container">
          <div className="section-header">
            <h2>Experience RootLens in Action</h2>
            <p>Watch how scaling incidents are diagnosed and resolved in real time</p>
          </div>
          <div className="dashboard-preview-content">
            <div className="dashboard-screenshot">
              <div className="screenshot-browser">
                <div className="browser-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div className="browser-url">rootlens dashboard</div>
              </div>
              <div className="screenshot-image">
                <img
                  src="/dashboard-preview.png"
                  alt="RootLens dashboard showing root cause analysis results"
                  className="dashboard-preview-img"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section credibility-section">
        <div className="container">
          <div className="section-header">
            <h2>Built for Kubernetes-Native Teams</h2>
            <p>Designed for DevOps engineers working with KEDA autoscaling</p>
          </div>
          <div className="tech-stack">
            <span className="tech-badge">
              <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Kubernetes_logo_without_workmark.svg/3840px-Kubernetes_logo_without_workmark.svg.png" alt="Kubernetes" loading="lazy" />
            </span>
            <span className="tech-badge">
              <img src="https://keda.sh/img/logos/keda-icon-color.png" alt="KEDA" loading="lazy" />
            </span>
            <span className="tech-badge">
              <img src="https://www.rabbitmq.com/assets/files/rabbitmq-logo-e91cacd38fcef5219149bc5cfa10b384.svg" alt="RabbitMQ" loading="lazy" />
            </span>
            <span className="tech-badge">
              <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Prometheus_software_logo.svg/1280px-Prometheus_software_logo.svg.png" alt="Prometheus" loading="lazy" />
            </span>
            <span className="tech-badge">
              <img src="https://go.dev/blog/go-brand/Go-Logo/PNG/Go-Logo_Blue.png" alt="Go" loading="lazy" />
            </span>
            <span className="tech-badge">
              <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/React-icon.svg/3840px-React-icon.svg.png" alt="React" loading="lazy" />
            </span>
          </div>
        </div>
      </section>

      <section className="section final-cta-section">
        <div className="container cta-container">
          <h2>Stop Guessing. Start Resolving.</h2>
          <p>Diagnose Kubernetes scaling failures with confidence using RootLens</p>
          <div className="cta-buttons-row">
            <Link to="/dashboard" className="btn btn-primary btn-lg">
              Launch Dashboard
            </Link>
            <Link to="/docs" className="btn btn-secondary btn-lg">
              Read the Docs
            </Link>
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

export default Home;
