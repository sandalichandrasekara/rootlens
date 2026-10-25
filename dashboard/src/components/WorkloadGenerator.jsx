import React, { useState, useEffect } from 'react';
import { Card, Button, Slider } from './index';
import { generateWorkload, purgeQueue } from '../services/api';
import '../styles/pages/WorkloadGenerator.css';

const WorkloadGenerator = () => {
  const [messageCount, setMessageCount] = useState(500);
  const [messageSize, setMessageSize] = useState(1024);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [purgeConfirming, setPurgeConfirming] = useState(false);

  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(null), 5000);
    return () => clearTimeout(timer);
  }, [feedback]);

  useEffect(() => {
    if (!purgeConfirming) return;
    const timer = setTimeout(() => setPurgeConfirming(false), 3000);
    return () => clearTimeout(timer);
  }, [purgeConfirming]);

  const totalKB = ((messageCount * messageSize) / 1024).toFixed(0);
  const totalMB = (totalKB / 1024).toFixed(2);
  const payloadLabel = totalKB >= 1024 ? `${totalMB} MB` : `${totalKB} KB`;

  const handleCountInput = (e) => {
    const val = Math.min(10000, Math.max(1, parseInt(e.target.value, 10) || 1));
    setMessageCount(val);
  };

  const handleSizeInput = (e) => {
    const val = Math.min(10000, Math.max(512, parseInt(e.target.value, 10) || 512));
    setMessageSize(val);
  };

  const handleGenerate = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const response = await generateWorkload({ count: messageCount, size: messageSize, mode: 'spike' });
      setFeedback({ type: 'success', message: response.data.message || 'Workload generated successfully!' });
    } catch (error) {
      setFeedback({ type: 'error', message: `Failed to generate workload: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handlePurge = async () => {
    if (!purgeConfirming) {
      setPurgeConfirming(true);
      return;
    }
    setPurgeConfirming(false);
    setLoading(true);
    setFeedback(null);
    try {
      const response = await purgeQueue();
      setFeedback({ type: 'success', message: response.data.message || 'Queue purged successfully!' });
    } catch (error) {
      setFeedback({ type: 'error', message: `Failed to purge queue: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workload-generator-page">
      <div className="workload-header">
        <h2>Workload Generator</h2>
        <p className="workload-subtitle">Simulate traffic to test KEDA autoscaling behavior</p>
      </div>

      <div className="params-grid">
        <Card title="Message Count" className="param-card">
          <Slider
            label="Count"
            min={1}
            max={10000}
            value={messageCount}
            onChange={setMessageCount}
            step={messageCount >= 1000 ? 500 : 50}
            id="message-count"
          />
          <div className="param-value-row">
            <input
              type="number"
              className="param-number-input"
              value={messageCount}
              min={1}
              max={10000}
              onChange={handleCountInput}
            />
            <span className="param-unit">messages</span>
          </div>
        </Card>

        <Card title="Message Size" className="param-card">
          <Slider
            label="Size"
            min={512}
            max={10000}
            value={messageSize}
            onChange={setMessageSize}
            step={512}
            unit=" bytes"
            id="message-size"
          />
          <div className="param-value-row">
            <input
              type="number"
              className="param-number-input"
              value={messageSize}
              min={512}
              max={10000}
              step={512}
              onChange={handleSizeInput}
            />
            <span className="param-unit">bytes</span>
          </div>
        </Card>
      </div>

      <div className="payload-summary">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        </svg>
        <span>Total payload: <strong>~{payloadLabel}</strong></span>
        <span className="payload-divider">·</span>
        <span>This will push <strong>{messageCount.toLocaleString()} messages</strong> to the queue and trigger KEDA scaling</span>
      </div>

      {feedback && (
        <div className={`feedback-message feedback-${feedback.type}`}>
          <span className="feedback-icon">
            {feedback.type === 'success' ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 8v4"/>
                <path d="M12 16h.01"/>
              </svg>
            )}
          </span>
          <span className="feedback-text">{feedback.message}</span>
        </div>
      )}

      <div className="action-buttons">
        <Button
          variant="primary"
          size="lg"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate Workload'}
        </Button>

        <Button
          variant="danger"
          size="lg"
          onClick={handlePurge}
          disabled={loading}
        >
          {purgeConfirming ? 'Tap again to confirm' : 'Purge Queue'}
        </Button>
      </div>
    </div>
  );
};

export default WorkloadGenerator;
