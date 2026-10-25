import React from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const About = () => {
  return (
    <div className="home-modern">
      <Navbar />

      <section className="page-hero">
        <div className="container">
          <div className="hero-badge">Kubernetes Scaling Intelligence</div>
          <h1>About RootLens</h1>
          <p>Automated Root Cause Detection for Kubernetes Autoscaling Delays</p>
        </div>
      </section>

      <section className="section docs-section">
        <div className="container docs-container">
          <div className="docs-block">
            <h2>What is RootLens?</h2>
            <p>
              RootLens is a diagnostic platform designed to automatically identify and diagnose root causes of scaling delays in Kubernetes autoscaling pipelines using KEDA (Kubernetes Event Driven Autoscaling).
            </p>
            <p>
              In modern cloud-native architectures, autoscaling is critical for cost efficiency and performance. However, when scaling doesn't happen quickly enough, it's often difficult to determine why. Is it a cold start issue? Scheduling contention? Or metric propagation lag?
            </p>
            <p>
              RootLens answers this question by collecting metrics from RabbitMQ, Kubernetes, and KEDA, then analyzing the data to pinpoint the exact bottleneck in your autoscaling pipeline.
            </p>
          </div>

          <div className="docs-block">
            <h2>The Problem We Solve</h2>
            <p>
              Event-driven autoscaling with KEDA is powerful, but when scaling is slow, diagnosing the cause is painful. RootLens identifies three root cause categories that account for the vast majority of KEDA scaling delays:
            </p>
            <ul className="docs-list highlight">
              <li>
                <strong>Pod Cold Start:</strong> The time required to initialize a container and start the application. This includes pulling the image, creating the container, and running initialization scripts.
              </li>
              <li>
                <strong>Scheduling Contention:</strong> The delay in the Kubernetes scheduler placing a pod on an available node. This occurs when cluster resources are fully utilized or scheduling constraints are complex.
              </li>
              <li>
                <strong>Metric Propagation Lag:</strong> The time it takes for queue metrics to flow through the system (RabbitMQ → Prometheus → KEDA) and trigger scaling decisions.
              </li>
            </ul>
            <p>
              By isolating these three categories with a hybrid rule-based and ML engine, RootLens gives operators a precise, confidence-scored answer — not just a signal to investigate.
            </p>
          </div>

          <div className="docs-block">
            <h2>System Architecture</h2>
            <p>RootLens consists of four components working together:</p>
            <div className="about-architecture">
              <div className="arch-card">
                <div className="arch-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                    <line x1="8" y1="21" x2="16" y2="21"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                </div>
                <h3>Go API Server</h3>
                <p>Collects metrics from RabbitMQ, the Kubernetes API, and KEDA scalers. Runs the rule-based RCA engine and exposes a REST API.</p>
              </div>
              <div className="arch-card">
                <div className="arch-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                  </svg>
                </div>
                <h3>ML Explainer Service</h3>
                <p>A Python/Flask service hosting three category-specific RandomForest models for sub-cause classification.</p>
              </div>
              <div className="arch-card">
                <div className="arch-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                  </svg>
                </div>
                <h3>Web Dashboard</h3>
                <p>A React-based interface for visualising metrics, running RCA analysis, and browsing history.</p>
              </div>
              <div className="arch-card">
                <div className="arch-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  </svg>
                </div>
                <h3>Kubernetes Operator</h3>
                <p>A controller-runtime operator that reconciles a single <code>RootLens</code> CRD into the full stack deployment.</p>
              </div>
            </div>
          </div>

          <div className="docs-block">
            <h2>Key Features</h2>
            <div className="about-features">
              <div className="about-feature">
                <h3>Root Cause Classification</h3>
                <p>Automatically categorize scaling delays into cold start, scheduling, or metric lag</p>
              </div>
              <div className="about-feature">
                <h3>Live Metrics Dashboard</h3>
                <p>Monitor queue depth, pod count, and scaling events in real-time</p>
              </div>
              <div className="about-feature">
                <h3>Workload Generator</h3>
                <p>Create synthetic workloads to test autoscaling behavior under different conditions</p>
              </div>
              <div className="about-feature">
                <h3>RCA History</h3>
                <p>Browse the last 50 RCA results, view confidence breakdowns, and export data as CSV</p>
              </div>
              <div className="about-feature">
                <h3>ML Sub-Cause Explainer</h3>
                <p>Category-specific RandomForest models identify the precise sub-cause within each category</p>
              </div>
              <div className="about-feature">
                <h3>Evidence-Based Analysis</h3>
                <p>View supporting signals, feature importance, and actionable recommendations</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section final-cta-section">
        <div className="container cta-container">
          <h2>Ready to Get Started?</h2>
          <p>Check out the documentation or launch the dashboard to explore RootLens</p>
          <div className="cta-buttons-row">
            <Link to="/docs" className="btn btn-primary btn-lg">View Documentation</Link>
            <Link to="/dashboard" className="btn btn-secondary btn-lg">Launch Dashboard</Link>
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

export default About;
