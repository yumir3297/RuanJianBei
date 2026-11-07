import http from "./http.js";

// Visitor feedback is a public visitor action; analytics reads live in adminInsights.js.
export function submitVisitorFeedback(payload) {
  return http.post("/insights/feedback", payload).then((r) => r.data);
}
