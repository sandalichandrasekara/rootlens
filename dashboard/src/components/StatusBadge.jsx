import React from 'react';
import '../styles/components/StatusBadge.css';

const statusConfig = {
  healthy: { label: 'Healthy', icon: '✓', color: 'green' },
  warning: { label: 'Warning', icon: '⚠', color: 'amber' },
  critical: { label: 'Critical', icon: '✕', color: 'red' },
  success: { label: 'Success', icon: '✓', color: 'green' },
  error: { label: 'Error', icon: '✕', color: 'red' },
  info: { label: 'Info', icon: 'ℹ', color: 'blue' },
};

const StatusBadge = ({ status, size = 'md', children }) => {
  const config = statusConfig[status] || statusConfig.info;

  return (
    <span className={`status-badge status-${config.color} size-${size}`}>
      <span className="status-icon">{config.icon}</span>
      <span className="status-label">{children || config.label}</span>
    </span>
  );
};

export default StatusBadge;
