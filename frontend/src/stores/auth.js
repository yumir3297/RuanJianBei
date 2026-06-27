import { defineStore } from "pinia";

const AUTH_KEY = "a5-admin-auth";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(AUTH_KEY) || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    login(password) {
      // 简单密码验证，可替换为后端接口
      if (password === import.meta.env.VITE_ADMIN_PASSWORD || password === "admin123") {
        const token = btoa(`admin:${Date.now()}`);
        this.token = token;
        localStorage.setItem(AUTH_KEY, token);
        return true;
      }
      return false;
    },
    logout() {
      this.token = null;
      localStorage.removeItem(AUTH_KEY);
    },
  },
});
