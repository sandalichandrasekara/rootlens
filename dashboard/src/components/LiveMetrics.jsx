import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Card, ChartContainer } from './index';
import { getMetrics } from '../services/api';
import '../styles/pages/LiveMetrics.css';

const LiveMetrics = () => {
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await getMetrics();
        const data = response.data;

        setMetrics(data);
        setLoading(false);

        setHistory(prev => {
          const newHistory = [...prev, {
            time: new Date(data.timestamp).toLocaleTimeString(),
            queueDepth: data.queue_depth,
            podCount: data.pod_count,
            desiredReplicas: data.desired_replicas,
            messageRate: parseFloat((data.message_rate ?? 0).toFixed(2)),
          }];
          return newHistory.slice(-20);
        });
      } catch {
        setLoading(false);
      }
    };

    fetchMetrics();

    const interval = setInterval(fetchMetrics, 2000);

    return () => clearInterval(interval);
  }, []);

  const timeRanges = [
    { value: '15m', label: '15m' },
    { value: '1h', label: '1h' },
    { value: '6h', label: '6h' },
    { value: '24h', label: '24h' },
  ];

  const handleExportCSV = () => {
    if (history.length === 0) return;

    const headers = ['Time', 'Queue Depth', 'Pod Count', 'Desired Replicas', 'Message Rate'];
    const rows = history.map(row => [
      row.time,
      row.queueDepth,
      row.podCount,
      row.desiredReplicas,
      row.messageRate
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `rootlens-metrics-${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="metrics-loading">
        <div className="spinner"></div>
        <p>Loading metrics...</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="metrics-loading">
        <p style={{ color: 'var(--color-text-secondary)' }}>
          Unable to load metrics - Make sure the API server is reachable
        </p>
      </div>
    );
  }

  return (
    <div className="live-metrics-page">
      <div className="metrics-filter">
        <label>Time Range:</label>
        <div className="time-buttons">
          {timeRanges.map((range) => (
            <button
              key={range.value}
              className={`time-btn ${timeRange === range.value ? 'active' : ''}`}
              onClick={() => setTimeRange(range.value)}
            >
              {range.label}
            </button>
          ))}
        </div>
        <div className="filter-spacer"></div>
        <button className="export-btn" onClick={handleExportCSV} disabled={history.length === 0}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Export CSV
        </button>
      </div>

      <div className="metrics-cards-grid">
        <Card className="metric-card">
          <h3>Queue Depth</h3>
          <div className="metric-large-value">{metrics.queue_depth}</div>
          <p className="metric-unit">messages</p>
        </Card>

        <Card className="metric-card">
          <h3>Active Pods</h3>
          <div className="metric-large-value">{metrics.pod_count}</div>
          <p className="metric-unit">pods running</p>
        </Card>

        <Card className="metric-card">
          <h3>Desired Replicas</h3>
          <div className="metric-large-value">{metrics.desired_replicas}</div>
          <p className="metric-unit">target replicas</p>
        </Card>

        <Card className="metric-card">
          <h3>Message Rate</h3>
          <div className="metric-large-value">{(metrics.message_rate ?? 0).toFixed(2)}</div>
          <p className="metric-unit">messages/sec</p>
        </Card>
      </div>

      <div className="charts-grid">
        <ChartContainer
          title="Queue Depth Over Time"
          subtitle="Number of messages waiting in queue"
          height="400px"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={history}
              margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
            >
              <defs>
                <linearGradient id="colorQueueDepth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="time"
                stroke="var(--color-text-tertiary)"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="var(--color-text-tertiary)"
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '8px',
                  color: 'var(--color-text-primary)',
                }}
                labelStyle={{ color: 'var(--color-text-primary)' }}
              />
              <Legend
                wrapperStyle={{ color: 'var(--color-text-secondary)' }}
              />
              <Area
                type="monotone"
                dataKey="queueDepth"
                stroke="var(--color-accent)"
                fillOpacity={1}
                fill="url(#colorQueueDepth)"
                name="Queue Depth"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        <ChartContainer
          title="Pod Count Over Time"
          subtitle="Active replicas vs desired replicas"
          height="400px"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={history}
              margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="time"
                stroke="var(--color-text-tertiary)"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="var(--color-text-tertiary)"
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '8px',
                  color: 'var(--color-text-primary)',
                }}
                labelStyle={{ color: 'var(--color-text-primary)' }}
              />
              <Legend
                wrapperStyle={{ color: 'var(--color-text-secondary)' }}
              />
              <Line
                type="monotone"
                dataKey="podCount"
                stroke="var(--color-success)"
                strokeWidth={2}
                dot={{ fill: 'var(--color-success)', r: 4 }}
                activeDot={{ r: 6 }}
                name="Active Pods"
              />
              <Line
                type="monotone"
                dataKey="desiredReplicas"
                stroke="var(--color-accent)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: 'var(--color-accent)', r: 4 }}
                activeDot={{ r: 6 }}
                name="Desired Replicas"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </div>

      <ChartContainer
        title="Message Rate Over Time"
        subtitle="Throughput in messages per second"
        height="300px"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={history}
            margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="time"
              stroke="var(--color-text-tertiary)"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="var(--color-text-tertiary)"
              style={{ fontSize: '12px' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                color: 'var(--color-text-primary)',
              }}
              labelStyle={{ color: 'var(--color-text-primary)' }}
            />
            <Legend
              wrapperStyle={{ color: 'var(--color-text-secondary)' }}
            />
            <Line
              type="monotone"
              dataKey="messageRate"
              stroke="var(--color-warning)"
              strokeWidth={2}
              dot={{ fill: 'var(--color-warning)', r: 4 }}
              activeDot={{ r: 6 }}
              name="Message Rate (msg/s)"
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  );
};

export default LiveMetrics;