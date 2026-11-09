export async function fetchWalkingRoute(poiIds, { signal } = {}) {
  const response = await fetch("/api/guide/map/walking-route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ poi_ids: poiIds }),
    signal,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "路线请求失败");
  return data;
}
