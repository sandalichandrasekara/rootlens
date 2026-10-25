import React from 'react';
import '../styles/components/ChartContainer.css';

const ChartContainer = ({
  title,
  subtitle,
  children,
  loading = false,
  error = null,
  height = '300px',
  action,
}) => {
  return (
    <div className="chart-container" style={{ height }}>
      <div className="chart-header">
        <div className="chart-info">
          {title && <h3 className="chart-title">{title}</h3>}
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
        {action && <div className="chart-action">{action}</div>}
      </div>

      <div className="chart-body">
        {loading ? (
          <div className="chart-loading">
            <div className="spinner"></div>
            <p>Loading chart...</p>
          </div>
        ) : error ? (
          <div className="chart-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4"/>
              <path d="M12 16h.01"/>
            </svg>
            <p>{error}</p>
          </div>
        ) : (
          <div className="chart-content">{children}</div>
        )}
      </div>
    </div>
  );
};

export default ChartContainer;
