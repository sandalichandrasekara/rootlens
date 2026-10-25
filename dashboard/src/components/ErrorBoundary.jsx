import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.content}>
            <h2 style={styles.title}>Something went wrong</h2>
            <p style={styles.message}>
              An unexpected error occurred. Please try refreshing the page.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={styles.details}>
                <summary style={styles.summary}>Error Details</summary>
                <pre style={styles.errorText}>
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
            <div style={styles.actions}>
              <button style={styles.button} onClick={this.handleRetry}>
                Try Again
              </button>
              <button
                style={styles.buttonSecondary}
                onClick={() => window.location.reload()}
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    backgroundColor: '#0d1117',
    padding: '20px',
  },
  content: {
    maxWidth: '500px',
    textAlign: 'center',
    color: '#c9d1d9',
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    marginBottom: '16px',
    color: '#f0f6fc',
  },
  message: {
    fontSize: '16px',
    marginBottom: '24px',
    color: '#8b949e',
  },
  details: {
    textAlign: 'left',
    marginBottom: '24px',
    padding: '16px',
    backgroundColor: '#161b22',
    borderRadius: '8px',
    border: '1px solid #30363d',
  },
  summary: {
    cursor: 'pointer',
    color: '#58a6ff',
    marginBottom: '8px',
  },
  errorText: {
    fontSize: '12px',
    color: '#f85149',
    overflow: 'auto',
    maxHeight: '200px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
  },
  button: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#ffffff',
    backgroundColor: '#238636',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  buttonSecondary: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#c9d1d9',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '6px',
    cursor: 'pointer',
  },
};

export default ErrorBoundary;
