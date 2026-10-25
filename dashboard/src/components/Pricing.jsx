import React from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const Pricing = () => {
  return (
    <div className="home-modern">
      <Navbar />

      <section className="page-hero">
        <div className="container">
          <div className="hero-badge">Kubernetes Scaling Intelligence</div>
          <h1>Simple, Transparent Pricing</h1>
          <p>Start free with the Community edition. Upgrade when your team needs more.</p>
        </div>
      </section>

      <section className="section pricing-page-section">
        <div className="container">
          <div className="pricing-grid">
            <div className="pricing-card">
              <div className="pricing-header">
                <h3>Community</h3>
                <div className="pricing-price">
                  <span className="price">Free</span>
                  <span className="period">forever</span>
                </div>
                <p className="pricing-description">Full-featured open-source edition for developers and small teams</p>
              </div>
              <ul className="pricing-features">
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Full RCA engine with ML explainers
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Real-time metrics dashboard
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Workload generator
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  7-day data retention
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  GitHub community support
                </li>
              </ul>
              <Link to="/dashboard" className="btn btn-secondary btn-full">Get Started Free</Link>
            </div>

            <div className="pricing-card featured">
              <div className="pricing-badge">Most Popular</div>
              <div className="pricing-header">
                <h3>Team</h3>
                <div className="pricing-price">
                  <span className="price">$29</span>
                  <span className="period">/month</span>
                </div>
                <p className="pricing-description">For engineering teams that need extended retention and direct support</p>
              </div>
              <ul className="pricing-features">
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Everything in Community
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  90-day data retention
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Email support (48h response)
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Automatic analysis triggers
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  CSV data export
                </li>
              </ul>
              <Link to="/contact" className="btn btn-primary btn-full">Start 14-Day Trial</Link>
            </div>

            <div className="pricing-card">
              <div className="pricing-header">
                <h3>Business</h3>
                <div className="pricing-price">
                  <span className="price">$99</span>
                  <span className="period">/month</span>
                </div>
                <p className="pricing-description">For organisations that need priority support, compliance, and onboarding</p>
              </div>
              <ul className="pricing-features">
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Everything in Team
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  1-year data retention
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Priority support (24h response)
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Onboarding call included
                </li>
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Invoice billing available
                </li>
              </ul>
              <Link to="/contact" className="btn btn-secondary btn-full">Contact Us</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-header">
            <h2>Frequently Asked Questions</h2>
          </div>
          <div className="faq-grid-pricing">
            <div className="faq-item-pricing">
              <h3>Can I try RootLens before purchasing?</h3>
              <p>Yes, the Community edition is completely free with all core features. Team and Business plans include a 14-day free trial.</p>
            </div>
            <div className="faq-item-pricing">
              <h3>What payment methods do you accept?</h3>
              <p>We accept all major credit cards. Business plans can arrange invoice billing.</p>
            </div>
            <div className="faq-item-pricing">
              <h3>Can I upgrade or downgrade my plan?</h3>
              <p>Yes, you can change your plan at any time. Upgrades take effect immediately, downgrades apply at the next billing cycle.</p>
            </div>
            <div className="faq-item-pricing">
              <h3>Is RootLens self-hosted or SaaS?</h3>
              <p>RootLens is self-hosted and runs inside your Kubernetes cluster. Your metrics and RCA data never leave your infrastructure.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section final-cta-section">
        <div className="container cta-container">
          <h2>Start Diagnosing Faster</h2>
          <p>Get started free today. Upgrade when your team is ready.</p>
          <div className="cta-buttons-row">
            <Link to="/dashboard" className="btn btn-primary btn-lg">Try Free</Link>
            <Link to="/contact" className="btn btn-secondary btn-lg">Talk to Us</Link>
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

export default Pricing;
