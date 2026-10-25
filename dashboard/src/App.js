import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import { ThemeProvider } from './context/ThemeContext';
import ErrorBoundary from './components/ErrorBoundary';

// Public Pages
import Home from './components/Home';
import About from './components/About';
import Features from './components/Features';
import Pricing from './components/Pricing';
import Contact from './components/Contact';
import Docs from './components/Docs';

// Dashboard Layout
import DashboardLayout from './components/DashboardLayout';

// Dashboard Pages
import Dashboard from './components/Dashboard';
import LiveMetrics from './components/LiveMetrics';
import RCAResults from './components/RCAResults';
import WorkloadGenerator from './components/WorkloadGenerator';

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <Router>
          <Routes>
            {/* Public Pages */}
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/features" element={<Features />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/docs" element={<Docs />} />

            {/* Dashboard Pages */}
            <Route
              path="/dashboard"
              element={
                <DashboardLayout title="Home">
                  <Dashboard />
                </DashboardLayout>
              }
            />
            <Route
              path="/metrics"
              element={
                <DashboardLayout title="Live Metrics">
                  <LiveMetrics />
                </DashboardLayout>
              }
            />
            <Route
              path="/analysis"
              element={
                <DashboardLayout title="RCA Results">
                  <RCAResults />
                </DashboardLayout>
              }
            />
            <Route
              path="/workload"
              element={
                <DashboardLayout title="Generate Workloads">
                  <WorkloadGenerator />
                </DashboardLayout>
              }
            />
          </Routes>
        </Router>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
