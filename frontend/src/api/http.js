import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 10000,
});

export default http;

