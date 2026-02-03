import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// KPI endpoints
export const getKPIs = {
  daily: (params) => api.get('/kpis/daily', { params }),
  weekly: (params) => api.get('/kpis/weekly', { params }),
  monthly: (params) => api.get('/kpis/monthly', { params }),
};

// Prediction endpoints
export const getPredictions = {
  dashboard: () => api.get('/predictions/dashboard'),
  failures: (params) => api.get('/predictions/failures', { params }),
  highRisk: (params) => api.get('/predictions/failures/high-risk', { params }),
  pmOptimization: (params) => api.get('/predictions/pm-optimization', { params }),
  insights: (params) => api.get('/predictions/insights', { params }),
  summary: () => api.get('/predictions/summary'),
};

export default api;