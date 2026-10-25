import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { healthCheck, getRCAHistory } from '../services/api';
import '../styles/pages/Dashboard.css';

const Dashboard = () => {
  const [systemStatus, setSystemStatus] = useState({
    cluster: 'Checking...',
    monitoring: 'Checking...',
    rcaEngine: 'Checking...',
    isHealthy: null
  });
  const [latestRCA, setLatestRCA] = useState(null);

  useEffect(() => {
    const fetchHealthStatus = async () => {
      try {
        const response = await healthCheck();
        const data = response.data;
        setSystemStatus({
          cluster: data.status === 'healthy' ? 'Active' : 'Degraded',
          monitoring: data.rabbitmq?.connected ? 'Running' : 'Disconnected',
          rcaEngine: data.ml_service?.available ? 'Ready' : 'Unavailable',
          isHealthy: data.status === 'healthy'
        });
      } catch (error) {
        setSystemStatus({
          cluster: 'Offline',
          monitoring: 'Unknown',
          rcaEngine: 'Unknown',
          isHealthy: false
        });
      }
    };

    fetchHealthStatus();
    const interval = setInterval(fetchHealthStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchLatestRCA = async () => {
      try {
        const res = await getRCAHistory();
        const history = res.data;
        if (history && history.length > 0) {
          setLatestRCA(history[history.length - 1]);
        }
      } catch {
      }
    };
    fetchLatestRCA();
  }, []);

  return (
    <div className="dashboard-home">
      <section className="welcome-section">
        <h1>Welcome to RootLens</h1>
        <p className="welcome-description">
          Your intelligent diagnostic platform for Kubernetes autoscaling.
          Uncover hidden bottlenecks, pinpoint scaling delays, and optimize your cluster performance.
        </p>
      </section>

      <section className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <Link to="/workload" className="quick-action-card">
            <div className="action-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <h3>Generate Workloads</h3>
            <p>Simulate traffic and test autoscaling behavior</p>
          </Link>

          <Link to="/metrics" className="quick-action-card">
            <div className="action-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
              </svg>
            </div>
            <h3>View Live Metrics</h3>
            <p>Monitor real-time cluster and queue metrics</p>
          </Link>

          <Link to="/analysis" className="quick-action-card">
            <div className="action-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
                <path d="M11 8v6"/>
                <path d="M8 11h6"/>
              </svg>
            </div>
            <h3>View RCA Results</h3>
            <p>Analyze root causes of scaling delays</p>
          </Link>
        </div>
      </section>

      {latestRCA && (
        <section className="latest-rca-section">
          <h2>Latest Diagnosis</h2>
          <div className="latest-rca-card">
            <div className="latest-rca-info">
              <div className="latest-rca-cause">
                <span className="latest-rca-label">Root Cause</span>
                <span className="latest-rca-value">
                  {{
                    'POD_COLD_START': 'Cold Start',
                    'SCHEDULING_CONTENTION': 'Scheduling Contention',
                    'METRIC_PROPAGATION_LAG': 'Metric Propagation Lag',
                    'UNKNOWN': 'Unknown'
                  }[latestRCA.root_cause] || latestRCA.root_cause}
                </span>
              </div>
              <div className="latest-rca-confidence">
                <span className="latest-rca-label">Confidence</span>
                <span className="latest-rca-value">
                  {((latestRCA.final_confidence || latestRCA.confidence || 0) * 100).toFixed(1)}%
                </span>
              </div>
              {latestRCA.detected_at && (
                <div className="latest-rca-time">
                  <span className="latest-rca-label">Detected</span>
                  <span className="latest-rca-value secondary">
                    {new Date(latestRCA.detected_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
            <Link to="/analysis" className="btn btn-secondary btn-sm">View Details</Link>
          </div>
        </section>
      )}

      <section className="system-overview-section">
        <h2>System Overview</h2>
        <div className="status-grid">
          <div className="status-card">
            <div className={`status-indicator ${systemStatus.cluster === 'Active' ? 'active' : systemStatus.cluster === 'Checking...' ? 'pending' : 'inactive'}`}></div>
            <div className="status-info">
              <span className="status-label">Cluster Status</span>
              <span className="status-value">{systemStatus.cluster}</span>
            </div>
          </div>

          <div className="status-card">
            <div className={`status-indicator ${systemStatus.monitoring === 'Running' ? 'active' : systemStatus.monitoring === 'Checking...' ? 'pending' : 'inactive'}`}></div>
            <div className="status-info">
              <span className="status-label">Monitoring Status</span>
              <span className="status-value">{systemStatus.monitoring}</span>
            </div>
          </div>

          <div className="status-card">
            <div className={`status-indicator ${systemStatus.rcaEngine === 'Ready' ? 'active' : systemStatus.rcaEngine === 'Checking...' ? 'pending' : 'inactive'}`}></div>
            <div className="status-info">
              <span className="status-label">RCA Engine</span>
              <span className="status-value">{systemStatus.rcaEngine}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="workflow-section">
        <h2>How to Use RootLens</h2>
        <div className="workflow-steps">
          <div className="workflow-step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h4>Generate Workload</h4>
              <p>Create synthetic traffic to trigger autoscaling events</p>
            </div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h4>Observe Metrics</h4>
              <p>Watch real-time metrics as your cluster responds</p>
            </div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h4>Analyze Results</h4>
              <p>View RCA to understand scaling delays</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
