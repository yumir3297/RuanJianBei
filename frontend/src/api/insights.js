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

export function fetchEmotionSummary() {
  return http.get("/insights/emotion-summary").then((r) => r.data);
}

export function submitVisitorFeedback(payload) {
  return http.post("/insights/feedback", payload).then((r) => r.data);
}

export function fetchExperienceReport(range = "week") {
  return http.get("/insights/experience-report", { params: { range } }).then((r) => r.data);
}
