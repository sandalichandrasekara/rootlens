import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, StatusBadge, Button, Table } from './index';
import { getRCAHistory, getRCAStats, runRCA, clearRCAHistory } from '../services/api';
import '../styles/pages/RCAResults.css';

const rootCauseConfig = {
  'POD_COLD_START': { label: 'Cold Start', status: 'warning', color: '#00d9a3' },
  'SCHEDULING_CONTENTION': { label: 'Scheduling Contention', status: 'warning', color: '#00d9a3' },
  'METRIC_PROPAGATION_LAG': { label: 'Metric Lag', status: 'info', color: '#00d9a3' },
  'UNKNOWN': { label: 'Unknown', status: 'critical', color: '#767a81' }
};

const subCauseConfig = {
  // Cold Start
  'image_pull_latency': { label: 'Image Pull Latency', color: '#f59e0b' },
  'init_container_delay': { label: 'Init Container Delay', color: '#8b5cf6' },
  'readiness_probe_failure': { label: 'Readiness Probe Failure', color: '#ef4444' },
  'container_runtime_slow': { label: 'Container Runtime Slow', color: '#6366f1' },
  'registry_timeout': { label: 'Registry Timeout', color: '#ec4899' },
  // Scheduling
  'taint_conflict': { label: 'Taint Conflict', color: '#f59e0b' },
  'resource_quota_exceeded': { label: 'Resource Quota Exceeded', color: '#ef4444' },
  'node_affinity_mismatch': { label: 'Node Affinity Mismatch', color: '#8b5cf6' },
  'pdb_violation': { label: 'PDB Violation', color: '#6366f1' },
  'insufficient_resources': { label: 'Insufficient Resources', color: '#ec4899' },
  // Metric Propagation
  'keda_polling_lag': { label: 'KEDA Polling Lag', color: '#f59e0b' },
  'metric_backend_slow': { label: 'Metric Backend Slow', color: '#8b5cf6' },
  'queue_depth_spike': { label: 'Queue Depth Spike', color: '#6366f1' },
  'scaler_misconfiguration': { label: 'Scaler Misconfiguration', color: '#10b981' }
};

const RCAResults = () => {
  const [latestResult, setLatestResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [running, setRunning] = useState(false);
  const [rcaError, setRcaError] = useState(null);
  const [showSubCauseDetails, setShowSubCauseDetails] = useState(false);

  const fetchData = async () => {
    try {
      const [historyRes, statsRes] = await Promise.all([
        getRCAHistory(),
        getRCAStats()
      ]);

      setHistory(historyRes.data);
      setStats(statsRes.data);

      if (historyRes.data.length > 0) {
        setLatestResult(historyRes.data[historyRes.data.length - 1]);
      }
    } catch {
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setShowSubCauseDetails(false);
  }, [latestResult?.detected_at]);

  const handleRunRCA = async () => {
    setRunning(true);
    setRcaError(null);
    try {
      const response = await runRCA();
      setLatestResult(response.data);
      await fetchData();
    } catch {
      setRcaError('Analysis failed — ensure the API server is reachable and a workload is running.');
    } finally {
      setRunning(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await clearRCAHistory();
      setHistory([]);
      setLatestResult(null);
      setStats(null);
    } catch {
    }
  };

  const getRootCauseInfo = (rootCause) => {
    return rootCauseConfig[rootCause] || rootCauseConfig.UNKNOWN;
  };

  const getExplainerStatusBadge = (status) => {
    const statusConfig = {
      'agreement': { status: 'success', label: 'Methods Agree' },
      'disagreement': { status: 'warning', label: 'Methods Disagree' },
      'ml_uncertain': { status: 'info', label: 'ML Uncertain' },
      'ml_unavailable': { status: 'warning', label: 'ML Unavailable' },
      'ml_disabled': { status: 'info', label: 'ML Disabled' },
      'no_scaling_detected': { status: 'info', label: 'No Scaling Detected' },
      'explainer_success': { status: 'success', label: 'Explainer Active' },
      'explainer_fallback': { status: 'warning', label: 'Explainer Fallback' }
    };
    return statusConfig[status] || { status: 'info', label: status || 'Unknown' };
  };

  const showSubCauseConfidence = (result) => {
    return result?.sub_cause &&
      result?.sub_cause !== 'undetermined' &&
      result?.sub_cause_confidence > 0;
  };

  const getSubCauseInfo = (subCause) => {
    return subCauseConfig[subCause] || { label: subCause?.replace(/_/g, ' ') || 'Unknown', color: '#767a81' };
  };

  const getSubCauseProbabilitiesData = () => {
    if (!latestResult?.sub_cause_probabilities) return [];
    return Object.entries(latestResult.sub_cause_probabilities).map(([cause, prob]) => ({
      name: getSubCauseInfo(cause).label,
      probability: parseFloat((prob * 100).toFixed(1)),
      fullName: cause
    })).sort((a, b) => b.probability - a.probability);
  };

  const getSubCauseFeatures = () => {
    if (!latestResult?.sub_cause_explanation?.top_features) return [];
    return latestResult.sub_cause_explanation.top_features.slice(0, 5).map(feature => ({
      name: feature.feature.replace(/_/g, ' '),
      importance: parseFloat((feature.importance * 100).toFixed(1)),
      value: parseFloat(feature.value.toFixed(2)),
    }));
  };

  const tableColumns = [
    { key: 'time', label: 'Time', width: '120px' },
    { key: 'rootCause', label: 'Root Cause', width: '160px' },
    { key: 'subCause', label: 'Sub-Cause', width: '180px' },
    { key: 'confidence', label: 'Confidence', width: '100px' },
    { key: 'status', label: 'Status', width: '140px' }
  ];

  const tableData = history.slice(-10).reverse().map((result) => ({
    time: result.detected_at ? new Date(result.detected_at).toLocaleTimeString() : 'N/A',
    rootCause: result.root_cause ? (getRootCauseInfo(result.root_cause)?.label || 'Unknown') : 'N/A',
    subCause: result.sub_cause ? getSubCauseInfo(result.sub_cause).label : '-',
    confidence: result.final_confidence ? `${(result.final_confidence * 100).toFixed(1)}%` :
                (result.rule_based_confidence ? `${(result.rule_based_confidence * 100).toFixed(1)}%` : 'N/A'),
    status: getExplainerStatusBadge(result.method_agreement)?.label || 'N/A'
  }));

  return (
    <div className="rca-results-page">
      <div className="rca-action-bar">
        <div className="rca-title">
          <h2>Root Cause Analysis</h2>
          <p className="rca-subtitle">Diagnose scaling delays and identify bottlenecks</p>
        </div>
        <div className="rca-action-buttons">
          {history.length > 0 && (
            <Button
              variant="secondary"
              size="lg"
              onClick={handleClearHistory}
            >
              Clear History
            </Button>
          )}
          <Button
            variant="primary"
            size="lg"
            onClick={handleRunRCA}
            disabled={running}
          >
            {running ? 'Running Analysis...' : 'Run RCA Now'}
          </Button>
        </div>
      </div>

      {rcaError && (
        <div className="rca-inline-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4"/>
            <path d="M12 16h.01"/>
          </svg>
          <span>{rcaError}</span>
        </div>
      )}

      {!latestResult && !rcaError && (
        <div className="rca-empty-state">
          <div className="empty-state-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
              <path d="M11 8v6"/>
              <path d="M8 11h6"/>
            </svg>
          </div>
          <h3>No Analysis Results Yet</h3>
          <p>Generate a workload to trigger KEDA autoscaling, then run RCA to diagnose any scaling delays.</p>
          <Link to="/workload" className="btn btn-secondary btn-sm">Generate a Workload</Link>
        </div>
      )}

      {latestResult && (
        <Card className="rca-result-card highlight" title="Latest Analysis Result">
          <div className="result-grid">
            <div className="result-item">
              <label>Root Cause</label>
              <div className="root-cause-display">
                <StatusBadge status={getRootCauseInfo(latestResult.root_cause)?.status}>
                  {getRootCauseInfo(latestResult.root_cause)?.label}
                </StatusBadge>
              </div>
            </div>

            <div className="result-item">
              <label>Final Confidence</label>
              <div className="confidence-display">
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{ width: `${(latestResult.final_confidence || latestResult.confidence || 0) * 100}%` }}
                  ></div>
                </div>
                <span className="confidence-value">
                  {((latestResult.final_confidence || latestResult.confidence || 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="result-item">
              <label>Explainer Status</label>
              <div className="agreement-display">
                <StatusBadge status={getExplainerStatusBadge(latestResult.method_agreement)?.status}>
                  {getExplainerStatusBadge(latestResult.method_agreement)?.label}
                </StatusBadge>
              </div>
            </div>
          </div>

          {(latestResult.root_cause === 'UNKNOWN' || latestResult.method_agreement === 'no_scaling_detected') && (
            <div className="no-scaling-message section-divider">
              <div className="info-banner">
                <div className="info-icon-svg">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 16v-4"/>
                    <path d="M12 8h.01"/>
                  </svg>
                </div>
                <div className="info-content">
                  <strong>No Active Scaling Detected</strong>
                  <p>
                    To get meaningful RCA results, generate a workload first and wait 10-15 seconds
                    for KEDA to detect the queue spike and start scaling pods. Then run RCA again.
                  </p>
                </div>
              </div>
            </div>
          )}

          {latestResult.root_cause !== 'UNKNOWN' && (
          <div className="confidence-breakdown section-divider">
            <h3>Confidence Breakdown</h3>
            <div className="confidence-rows">
              <div className="confidence-row">
                <div className="confidence-row-label">
                  <span className="method-name">Rule-Based Classifier</span>
                  <span className="method-weight">× 0.6</span>
                </div>
                <div className="confidence-bar-container">
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill rule-based"
                      style={{ width: `${(latestResult.rule_based_confidence || 0) * 100}%` }}
                    ></div>
                  </div>
                  <span className="confidence-percent">
                    {((latestResult.rule_based_confidence || 0) * 100).toFixed(1)}%
                  </span>
                  <span className="confidence-contribution">
                    = {((latestResult.rule_based_confidence || 0) * 0.6 * 100).toFixed(1)}
                  </span>
                </div>
              </div>

              {showSubCauseConfidence(latestResult) ? (
                <div className="confidence-row">
                  <div className="confidence-row-label">
                    <span className="method-name">ML Explainer</span>
                    <span className="method-weight">× 0.4</span>
                  </div>
                  <div className="confidence-bar-container">
                    <div className="confidence-bar">
                      <div
                        className="confidence-fill ml-based"
                        style={{ width: `${(latestResult.sub_cause_confidence || 0) * 100}%` }}
                      ></div>
                    </div>
                    <span className="confidence-percent ml">
                      {((latestResult.sub_cause_confidence || 0) * 100).toFixed(1)}%
                    </span>
                    <span className="confidence-contribution">
                      = {((latestResult.sub_cause_confidence || 0) * 0.4 * 100).toFixed(1)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="confidence-row ml-unavailable">
                  <div className="confidence-row-label">
                    <span className="method-name">ML Explainer</span>
                    <span className="method-weight">× 0.4</span>
                  </div>
                  <div className="confidence-bar-container">
                    <span className="ml-status-text">
                      {latestResult.method_agreement === 'ml_disabled' ? 'Disabled' : 'Pending Analysis'}
                    </span>
                  </div>
                </div>
              )}

              <div className="confidence-divider"></div>

              <div className="confidence-row combined">
                <div className="confidence-row-label">
                  <span className="method-name">Final Score</span>
                </div>
                <div className="confidence-bar-container">
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill combined"
                      style={{ width: `${(latestResult.final_confidence || 0) * 100}%` }}
                    ></div>
                  </div>
                  <span className="confidence-percent combined">
                    {((latestResult.final_confidence || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="confidence-formula">
                <span className="formula-text">
                  {showSubCauseConfidence(latestResult)
                    ? `Rule ${((latestResult.rule_based_confidence || 0) * 100).toFixed(0)}% × 0.6 + ML ${((latestResult.sub_cause_confidence || 0) * 100).toFixed(0)}% × 0.4 = ${((latestResult.final_confidence || 0) * 100).toFixed(1)}%`
                    : 'Hybrid score: rule-based (60%) + ML explainer (40%)'}
                </span>
              </div>
            </div>
          </div>
          )}

          {latestResult.sub_cause && (
            <div className="section-divider sub-cause-section">
              <div className="sub-cause-header">
                <div className="sub-cause-badge">
                  <div className="sub-cause-info">
                    <span className="sub-cause-label">Sub-Cause Identified</span>
                    <span className="sub-cause-name" style={{ color: getSubCauseInfo(latestResult.sub_cause).color }}>
                      {getSubCauseInfo(latestResult.sub_cause).label}
                    </span>
                  </div>
                </div>
                {latestResult.sub_cause_confidence !== undefined && (
                  <div className="sub-cause-confidence">
                    <span className="confidence-label">Confidence</span>
                    <div className="confidence-bar">
                      <div
                        className="confidence-fill sub-cause"
                        style={{ width: `${latestResult.sub_cause_confidence * 100}%` }}
                      ></div>
                    </div>
                    <span className="confidence-value">
                      {(latestResult.sub_cause_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>

              {/* Sub-cause details toggle */}
              {(getSubCauseProbabilitiesData().length > 0 || getSubCauseFeatures().length > 0) && (
                <div className="sub-cause-details-toggle">
                  <button
                    className="toggle-button"
                    onClick={() => setShowSubCauseDetails(!showSubCauseDetails)}
                  >
                    {showSubCauseDetails ? '▼ Hide Sub-Cause Details' : '▶ Show Sub-Cause Details'}
                  </button>
                </div>
              )}

              {showSubCauseDetails && (
                <div className="sub-cause-details-content">
                  {/* Sub-cause probability distribution */}
                  {getSubCauseProbabilitiesData().length > 0 && (
                    <div className="sub-cause-probabilities">
                      <h4>Sub-Cause Probabilities</h4>
                      <div className="probability-bars">
                        {getSubCauseProbabilitiesData().map((item, idx) => (
                          <div key={idx} className="probability-item">
                            <div className="probability-label">{item.name}</div>
                            <div className="probability-bar">
                              <div
                                className="probability-fill"
                                style={{
                                  width: `${item.probability}%`,
                                  backgroundColor: getSubCauseInfo(item.fullName).color
                                }}
                              ></div>
                            </div>
                            <div className="probability-value">{item.probability.toFixed(1)}%</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sub-cause contributing features */}
                  {getSubCauseFeatures().length > 0 && (
                    <div className="sub-cause-features">
                      <h4>Top Contributing Factors</h4>
                      <div className="features-list">
                        {getSubCauseFeatures().map((feature, idx) => (
                          <div key={idx} className="feature-item">
                            <div className="feature-name">{feature.name}</div>
                            <div className="feature-bar">
                              <div
                                className="feature-impact sub-cause"
                                style={{ width: `${feature.importance}%` }}
                              ></div>
                            </div>
                            <div className="feature-stats">
                              <span className="impact">{feature.importance.toFixed(1)}%</span>
                              <span className="value">val: {feature.value}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sub-cause explanation summary */}
                  {latestResult.sub_cause_explanation?.summary && (
                    <div className="sub-cause-summary">
                      <h4>Analysis Summary</h4>
                      <p>{latestResult.sub_cause_explanation.summary}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Sub-cause specific recommendations */}
              {(latestResult.sub_cause_recommendations || []).length > 0 && (
                <div className="sub-cause-recommendations">
                  <h4>Targeted Recommendations</h4>
                  <ul className="recommendations-list">
                    {latestResult.sub_cause_recommendations.map((item, idx) => (
                      <li key={idx}>→ {item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className="section-divider">
            <p className="timestamp-value">
              <strong>Detected At:</strong> {new Date(latestResult.detected_at || latestResult.timestamp).toLocaleString()}
            </p>
          </div>

          {(latestResult.evidence || []).length > 0 && (
            <div className="section-divider">
              <h3>Evidence</h3>
              <ul className="evidence-list">
                {latestResult.evidence.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
          )}

          {(latestResult.recommendations || []).length > 0 && (
            <div className="section-divider">
              <h3>Recommendations</h3>
              <ul className="recommendations-list">
                {latestResult.recommendations.map((item, idx) => (
                  <li key={idx}>→ {item}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      <div className="rca-stats-grid">
        <Card className="stat-card">
          <h3>Total Analyses</h3>
          <div className="stat-number">{stats?.total_analyses || 0}</div>
          <p className="stat-meta">RCA runs completed</p>
        </Card>

        <Card className="stat-card">
          <h3>Average Confidence</h3>
          <div className="stat-number">{((stats?.avg_confidence || 0) * 100).toFixed(1)}%</div>
          <p className="stat-meta">accuracy score</p>
        </Card>

      </div>

      <Card title="Analysis History">
        <Table columns={tableColumns} data={tableData} />
      </Card>
    </div>
  );
};

export default RCAResults;
