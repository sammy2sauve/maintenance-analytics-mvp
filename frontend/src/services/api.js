import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ts_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
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
  updateSuggestionStatus: (id, status) => api.patch(`/predictions/pm-optimization/${id}/status`, { status }),
};

// Work order endpoints
export const getWorkOrders = {
  recent: (params) => api.get('/work-orders/recent', { params }),
  stats: (params) => api.get('/work-orders/stats', { params }),
};

// Report generation -- returns a Blob for browser download
export const generateReport = async ({ sections, days, format, reportType = 'summary' }) => {
  const token = localStorage.getItem('ts_token');
  const response = await fetch(`${API_BASE_URL}/reports/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ sections, days: days || null, format, report_type: reportType }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Report generation failed');
  }
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : `truesignal-report.${format}`;
  return { blob, filename };
};

// Settings endpoints
export const getSettings = {
  pushToFaciliWorks: (suggestionId, locationId) =>
    api.post('/settings/faciliworks-push-wo', { suggestion_id: suggestionId, location_id: locationId }),
};

export default api;