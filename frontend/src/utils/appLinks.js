function safeAppUrl(value, { developmentFallback = "" } = {}) {
  const candidate = String(value || developmentFallback || "").trim();
  if (!candidate) return "";
  try {
    const url = new URL(candidate);
    if (url.protocol === "https:") return url.href.replace(/\/$/, "");
    if (import.meta.env.DEV && url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
      return url.href.replace(/\/$/, "");
    }
  } catch { /* invalid or non-absolute URL */ }
  return "";
}

export const touristAppUrl = safeAppUrl(import.meta.env.VITE_TOURIST_APP_URL, {
  developmentFallback: import.meta.env.DEV ? "http://localhost:5173" : "",
});
