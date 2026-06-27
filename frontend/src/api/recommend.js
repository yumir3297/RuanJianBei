import http from "./http";

export async function fetchRecommendations(payload) {
  const { data } = await http.post("/recommend/", payload);
  return data;
}

