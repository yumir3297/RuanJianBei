import { defineStore } from "pinia";
import http from "../api/http";

const AUTH_KEY = "a5-admin-auth";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(AUTH_KEY) || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(password) {
      try {
        const { data } = await http.post("/auth/login", { password });
        this.token = data.token;
        localStorage.setItem(AUTH_KEY, data.token);
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
      localStorage.removeItem(AUTH_KEY);
    },
  },
});
