import axios from "axios";

const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "")
  .trim()
  .replace(/\/+$/, "");

// Empty means same-origin. In development Vite proxies /api to the backend;
// production deployments should expose the same /api reverse proxy.
export const API_BASE_URL = configuredApiBaseUrl;

export const DEFAULT_REQUEST_TIMEOUT = 10000;

const AUTH_KEY = "a5-admin-auth";

const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: DEFAULT_REQUEST_TIMEOUT,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(AUTH_KEY);
    }
    return Promise.reject(error);
  },
);

export default http;
