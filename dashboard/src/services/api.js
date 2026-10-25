import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL
  ? `${process.env.REACT_APP_API_URL}/api`
  : (process.env.NODE_ENV === 'development'
      ? 'http://localhost:8080/api'
      : '/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject({
      status: error.response?.status,
      message: error.response?.data?.message || error.message,
      data: error.response?.data,
      originalError: error,
    });
  }
);

// Health check endpoint
export const healthCheck = () => api.get('/health');

// Metrics endpoints
export const getMetrics = () => api.get('/metrics');

// RCA endpoints
export const runRCA = () => api.post('/rca/run', {});

export const getLatestRCA = () => api.get('/rca/latest');

export const getRCAHistory = () => api.get('/rca/history');

export const getRCAStats = () => api.get('/rca/stats');

export const clearRCAHistory = () => api.delete('/rca/clear');

export const testRCA = (payload) => api.post('/rca/test', payload);

export const generateWorkload = (payload) => api.post('/workload/generate', payload);

export const purgeQueue = () => api.post('/workload/purge', {});

export const checkConnectivity = async () => {
  try {
    const response = await healthCheck();
    return {
      isConnected: true,
      apiUrl: API_BASE_URL,
      status: response.data?.status,
    };
  } catch (error) {
    return {
      isConnected: false,
      apiUrl: API_BASE_URL,
      error: error.message,
    };
  }
};

export default api;