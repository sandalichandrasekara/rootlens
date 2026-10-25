import React from 'react';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';

const Docs = () => {
  return (
    <div className="home-modern">
      <Navbar />

      <section className="page-hero">
        <div className="container">
          <div className="hero-badge">Kubernetes Scaling Intelligence</div>
          <h1>Documentation</h1>
          <p>Complete installation, configuration, and usage guide for RootLens</p>
        </div>
      </section>

      <section className="section docs-section">
        <div className="container docs-container">
          <div className="docs-block">
            <h2>Quick Start</h2>
            <ol className="docs-steps">
              <li>
                <strong>Install the backend service</strong>
                <p>Deploy the RootLens backend to your Kubernetes cluster using Helm or kubectl manifests.</p>
              </li>
              <li>
                <strong>Configure KEDA scaler</strong>
                <p>Set up a RabbitMQ scaler with KEDA and configure the queue name and metrics thresholds.</p>
              </li>
              <li>
                <strong>Access the dashboard</strong>
                <p>Open the web dashboard and navigate to the Dashboard page to verify metrics are being collected.</p>
              </li>
              <li>
                <strong>Run your first RCA</strong>
                <p>Generate a workload and run Root Cause Analysis to identify any scaling bottlenecks.</p>
              </li>
            </ol>
          </div>

          <div className="docs-block">
            <h2>Installation</h2>

            <h3>Prerequisites</h3>
            <ul className="docs-list">
              <li>Kubernetes 1.19+</li>
              <li>KEDA 2.0+ deployed on the cluster</li>
              <li>RabbitMQ message queue (3.8+)</li>
              <li>Prometheus (optional, for metrics collection)</li>
            </ul>

            <h3>Backend Deployment</h3>
            <p>Clone the RootLens repository and deploy the backend service:</p>
            <pre className="docs-code">
{`# Clone the repository
git clone https://github.com/rootlens/rootlens.git
cd rootlens

# Deploy using Go backend
go run cmd/server/main.go

# Or build and run
go build -o rootlens ./cmd/server
./rootlens`}
            </pre>

            <h3>Dashboard Setup</h3>
            <p>The dashboard is typically deployed as part of the backend service. Access it at:</p>
            <pre className="docs-code">
{`# Forward the dashboard port from your cluster:
kubectl port-forward -n rootlens svc/rootlens-web 3000:3000

# Then open:
http://localhost:3000`}
            </pre>
          </div>

          <div className="docs-block">
            <h2>Configuration</h2>
            <h3>Environment Variables</h3>
            <p>Configure RootLens through environment variables:</p>
            <div className="docs-table-wrapper">
              <table className="docs-table">
                <thead>
                  <tr>
                    <th>Variable</th>
                    <th>Default</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>RABBITMQ_HOST</code></td>
                    <td>localhost</td>
                    <td>RabbitMQ hostname</td>
                  </tr>
                  <tr>
                    <td><code>RABBITMQ_PORT</code></td>
                    <td>5672</td>
                    <td>RabbitMQ port</td>
                  </tr>
                  <tr>
                    <td><code>QUEUE_NAME</code></td>
                    <td>default</td>
                    <td>Queue name to monitor</td>
                  </tr>
                  <tr>
                    <td><code>SCALING_THRESHOLD</code></td>
                    <td>75</td>
                    <td>Queue depth % to trigger RCA</td>
                  </tr>
                  <tr>
                    <td><code>COLD_START_TIMEOUT</code></td>
                    <td>30</td>
                    <td>Cold start timeout (seconds)</td>
                  </tr>
                  <tr>
                    <td><code>SCHEDULING_TIMEOUT</code></td>
                    <td>15</td>
                    <td>Scheduling timeout (seconds)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="docs-block">
            <h2>Usage Guide</h2>

            <h3>Dashboard</h3>
            <p>The main overview page showing system health, current metrics, and recent scaling events.</p>

            <h3>Live Metrics</h3>
            <p>Real-time monitoring of queue depth, pod count, and message rate. Use time range filters to view historical data.</p>

            <h3>RCA Analysis</h3>
            <p>Click "Run RCA Now" to analyze recent scaling delays. The system will:</p>
            <ul className="docs-list">
              <li>Collect metrics from the last scaling event</li>
              <li>Analyze timing to identify the bottleneck</li>
              <li>Display the root cause with confidence score</li>
              <li>Provide evidence and remediation recommendations</li>
            </ul>

            <h3>Workload Generator</h3>
            <p>Test autoscaling behavior by generating synthetic workloads. Configure:</p>
            <ul className="docs-list">
              <li><strong>Message Count:</strong> Total messages to send (1-10,000)</li>
              <li><strong>Message Size:</strong> Bytes per message (512-10,000)</li>
              <li><strong>Spike Mode:</strong> Sends all messages immediately to trigger scaling</li>
              <li><strong>Purge Queue:</strong> Clear the queue to reset state</li>
            </ul>

            <h3>RCA History</h3>
            <p>All analyses are stored and displayed in the RCA Results page. Each entry shows the root cause, confidence score, evidence, and timestamp for every scaling event diagnosed.</p>
          </div>

          <div className="docs-block">
            <h2>Troubleshooting</h2>

            <h3>No metrics appearing</h3>
            <ul className="docs-list">
              <li>Verify RabbitMQ is accessible from the cluster</li>
              <li>Check QUEUE_NAME environment variable matches your actual queue</li>
              <li>Review backend logs: <code>kubectl logs -n rootlens deployment/rootlens-backend</code></li>
            </ul>

            <h3>RCA analysis returns "Unknown"</h3>
            <ul className="docs-list">
              <li>Ensure sufficient data is collected (at least one scaling event)</li>
              <li>Verify timeout thresholds are correctly configured</li>
              <li>Check that pod events are being captured by Kubernetes API</li>
            </ul>

            <h3>Workload generation fails</h3>
            <ul className="docs-list">
              <li>Verify RabbitMQ credentials are correct</li>
              <li>Check queue permissions allow publishing</li>
              <li>Monitor RabbitMQ memory and connections</li>
            </ul>
          </div>

          <div className="docs-block">
            <h2>Best Practices</h2>
            <ul className="docs-list highlight">
              <li><strong>Run regular analyses:</strong> Schedule RCA runs to track trends over time</li>
              <li><strong>Test before production:</strong> Use Workload Generator to validate changes in non-prod</li>
              <li><strong>Monitor cold start:</strong> Track pod initialization times during image updates</li>
              <li><strong>Review reports:</strong> Export reports for incident analysis and postmortems</li>
              <li><strong>Adjust thresholds:</strong> Fine-tune sensitivity based on your workload characteristics</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section final-cta-section">
        <div className="container cta-container">
          <h2>Ready to Get Started?</h2>
          <p>Launch the dashboard and start diagnosing scaling issues</p>
          <div className="cta-buttons-row">
            <Link to="/dashboard" className="btn btn-primary btn-lg">
              Launch Dashboard
            </Link>
            <Link to="/contact" className="btn btn-secondary btn-lg">
              Get Support
            </Link>
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

export default Docs;
