import http from "./http";

export function fetchSpotAttention() {
  return http.get("/insights/spot-attention").then((r) => r.data);
}

export function fetchVisitorGroups() {
  return http.get("/insights/visitor-groups").then((r) => r.data);
}

export function fetchQATrend() {
  return http.get("/insights/qa-trend").then((r) => r.data);
}

export function fetchBlindSpotTop() {
  return http.get("/insights/blind-spot-top").then((r) => r.data);
}
