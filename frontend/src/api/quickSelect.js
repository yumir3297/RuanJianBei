import http from "./http";

export async function fetchQuickSelectBootstrap() {
  const { data } = await http.get("/quick-select/bootstrap");
  return data;
}
