import http from "./http.js";

export async function fetchVisitorConfig() {
  const { data } = await http.get("/visitor-config");
  return data;
}
