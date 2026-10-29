import { defineStore } from "pinia";
import http from "../api/http";

const AUTH_KEY = "a5-admin-auth";

function readAuthToken() {
  try { return localStorage.getItem(AUTH_KEY) || null; } catch { return null; }
}

function removeAuthToken() {
  try { localStorage.removeItem(AUTH_KEY); } catch { /* storage may be disabled */ }
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: readAuthToken(),
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(password) {
      try {
        const { data } = await http.post("/auth/login", { password });
        this.token = data.token;
        try { localStorage.setItem(AUTH_KEY, data.token); } catch { /* keep auth in memory */ }
        return true;
      } catch (error) {
        const detail = error?.response?.data?.detail;
        if (detail) {
          throw new Error(detail);
        }
        throw new Error("登录失败，请检查网络连接");
      }
    },
    logout() {
      this.token = null;
      removeAuthToken();
    },
  },
});
