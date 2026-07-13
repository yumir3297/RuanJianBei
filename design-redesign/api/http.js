import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const DEFAULT_REQUEST_TIMEOUT = 10000;

const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: DEFAULT_REQUEST_TIMEOUT,
});

export default http;
