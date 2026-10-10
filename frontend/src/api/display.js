import http, { API_BASE_URL } from "./http";

export async function fetchPublicDisplayAssets() {
  const { data } = await http.get("/display-assets/");
  return data;
}

export function resolveDisplayAssetUrl(assetUrl) {
  if (!assetUrl) return "";
  if (/^https?:\/\//i.test(assetUrl)) return assetUrl;
  return `${API_BASE_URL}${assetUrl.startsWith("/") ? assetUrl : `/${assetUrl}`}`;
}
