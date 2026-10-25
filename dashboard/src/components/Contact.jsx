import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const Contact = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    subject: 'general',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="home-modern">
      <Navbar />

      <section className="page-hero">
        <div className="container">
          <div className="hero-badge">Kubernetes Scaling Intelligence</div>
          <h1>Contact Us</h1>
          <p>Have questions about RootLens? We'd love to hear from you.</p>
        </div>
      </section>

      <section className="section contact-section">
        <div className="container">
          <div className="contact-grid">
            <div className="contact-form-wrapper">
              <h2>Send us a Message</h2>
              {submitted ? (
                <div className="success-message">
                  <div className="success-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                  <h3>Message received!</h3>
                  <p>Thanks for reaching out. For the fastest response, open a GitHub issue or discussion.</p>
                  <button className="btn btn-secondary" onClick={() => setSubmitted(false)}>Back to Form</button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="contact-form">
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="name">Name *</label>
                      <input type="text" id="name" name="name" value={formData.name} onChange={handleChange} required placeholder="Your name" />
                    </div>
                    <div className="form-group">
                      <label htmlFor="email">Email *</label>
                      <input type="email" id="email" name="email" value={formData.email} onChange={handleChange} required placeholder="you@company.com" />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="company">Company</label>
                      <input type="text" id="company" name="company" value={formData.company} onChange={handleChange} placeholder="Your company name" />
                    </div>
                    <div className="form-group">
                      <label htmlFor="subject">Subject *</label>
                      <select id="subject" name="subject" value={formData.subject} onChange={handleChange} required>
                        <option value="general">General Inquiry</option>
                        <option value="support">Technical Support</option>
                        <option value="feedback">Feedback</option>
                        <option value="bug">Bug Report</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group">
                    <label htmlFor="message">Message *</label>
                    <textarea id="message" name="message" value={formData.message} onChange={handleChange} required rows="6" placeholder="Tell us about your project or questions..." />
                  </div>
                  <button type="submit" className="btn btn-primary">Send Message</button>
                </form>
              )}
            </div>

            <div className="contact-info">
              <div className="info-card">
                <div className="info-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
                  </svg>
                </div>
                <h3>GitHub Discussions</h3>
                <p>Best way to reach us</p>
              </div>
              <div className="info-card">
                <div className="info-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 6v6l4 2"/>
                  </svg>
                </div>
                <h3>Response Time</h3>
                <p>24-48 hours</p>
              </div>
              <div className="info-card social-card">
                <h3>Find Us On GitHub</h3>
                <div className="social-links">
                  <a href="https://github.com/rootlens" target="_blank" rel="noopener noreferrer" title="GitHub">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                  </a>
                </div>
              </div>
            </div>
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

export default Contact;
