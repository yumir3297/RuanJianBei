import { API_BASE_URL, DEFAULT_REQUEST_TIMEOUT, createHttpClient } from "./transport.js";
import { clearAdminToken, getAdminToken } from "../utils/adminAuthStorage.js";

const adminHttp = createHttpClient(API_BASE_URL);
adminHttp.defaults.timeout = DEFAULT_REQUEST_TIMEOUT;

adminHttp.interceptors.request.use((config) => {
  const token = getAdminToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

adminHttp.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) clearAdminToken();
    return Promise.reject(error);
  },
);

export default adminHttp;
