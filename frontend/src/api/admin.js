import http from "./http";

export async function fetchAdminOverview() {
  const { data } = await http.get("/admin/overview");
  return data;
}

export async function fetchAdminAnalytics() {
  const { data } = await http.get("/admin/analytics");
  return data;
}

export async function fetchBlindSpots(status = "open", limit = 50) {
  const { data } = await http.get("/admin/blind-spots", { params: { status, limit } });
  return data;
}

export async function resolveBlindSpotWithFAQ(id, payload) {
  const { data } = await http.post(`/admin/blind-spots/${id}/resolve-with-faq`, payload);
  return data;
}

export async function syncOfficialData() {
  const { data } = await http.post("/admin/sync-processed-data", null, { timeout: 30000 });
  return data;
}

export async function rebuildVectorIndex() {
  const { data } = await http.post("/admin/build-rag-index", null, { timeout: 120000 });
  return data;
}

export async function fetchAvatarConfig() {
  const { data } = await http.get("/admin/avatar-configs/active");
  return data;
}

export async function fetchAvatarConfigs() {
  const { data } = await http.get("/admin/avatar-configs");
  return data;
}

export async function saveAvatarConfig(configId) {
  const { data } = await http.put(`/admin/avatar-configs/${configId}/activate`);
  return data;
}

export async function updateAvatarConfig(configId, voiceType) {
  const { data } = await http.put(`/admin/avatar-configs/${configId}`, { voice_type: voiceType });
  return data;
}

export async function fetchDisplayAssets() {
  const { data } = await http.get("/admin/display-assets");
  return data;
}

export async function uploadTouristBackground(imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);
  const { data } = await http.post("/admin/display-assets/tourist-background", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
  return data;
}

export async function clearTouristBackground() {
  const { data } = await http.delete("/admin/display-assets/tourist-background");
  return data;
}

export async function updateWelcomeText(text) {
  const { data } = await http.put("/admin/display-assets/welcome-text", { text });
  return data;
}
