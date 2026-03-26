import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Create axios instance with credentials
const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth API
export const authApi = {
  exchangeSession: async (sessionId) => {
    const response = await api.post('/auth/session', { session_id: sessionId });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  
  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
};

// Campaign Brief API
export const campaignBriefApi = {
  create: async (data) => {
    const response = await api.post('/campaign-briefs', data);
    return response.data;
  },
  
  getById: async (id) => {
    const response = await api.get(`/campaign-briefs/${id}`);
    return response.data;
  },
  
  list: async () => {
    const response = await api.get('/campaign-briefs');
    return response.data;
  },
  
  linkToUser: async () => {
    const response = await api.post('/campaign-briefs/link');
    return response.data;
  },
};

export default api;
