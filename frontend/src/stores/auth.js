import { computed, ref } from "vue";
import { defineStore } from "pinia";
import adminHttp from "../api/adminHttp.js";
import {
  clearAdminToken,
  getAdminToken,
  setAdminToken,
  subscribeAdminToken,
} from "../utils/adminAuthStorage.js";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(getAdminToken());
  const isAuthenticated = computed(() => Boolean(token.value));
  subscribeAdminToken((nextToken) => { token.value = nextToken; });

  async function login(password) {
    try {
      const { data } = await adminHttp.post("/auth/login", { password });
      setAdminToken(data.token);
      return true;
    } catch (error) {
      const detail = error?.response?.data?.detail;
      if (detail) throw new Error(detail);
      throw new Error("登录失败，请检查网络连接");
    }
  }

  function logout() {
    clearAdminToken();
  }

  return { token, isAuthenticated, login, logout };
});
