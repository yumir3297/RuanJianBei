import axios from "axios";

const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "")
  .trim()
  .replace(/\/+$/, "");

// Empty means same-origin. Development servers proxy /api; production sites
// should route the same /api prefix to the shared backend.
export const API_BASE_URL = configuredApiBaseUrl;
export const DEFAULT_REQUEST_TIMEOUT = 10000;

export function createHttpClient(baseUrl = API_BASE_URL) {
  return axios.create({
    baseURL: `${String(baseUrl || "").replace(/\/+$/, "")}/api`,
    timeout: DEFAULT_REQUEST_TIMEOUT,
  });
}
