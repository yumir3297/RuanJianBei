import http from "./adminHttp.js";

export async function fetchAdminRuntimeLimits() {
  const { data } = await http.get("/admin/runtime-limits");
  return data;
}
