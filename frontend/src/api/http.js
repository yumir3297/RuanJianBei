import { API_BASE_URL, DEFAULT_REQUEST_TIMEOUT, createHttpClient } from "./transport.js";

export { API_BASE_URL, DEFAULT_REQUEST_TIMEOUT, createHttpClient };

// Tourist transport is intentionally anonymous. Admin identity belongs to adminHttp.js.
const http = createHttpClient(API_BASE_URL);

export default http;
