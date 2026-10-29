import { defineStore } from "pinia";
import {
  bootstrapTourSessions, createTourSession, fetchTourSession, fetchTourSessions,
  fetchTourTrash, purgeTourSession, removeTourSession, restoreTourSession, saveTourSession,
} from "../api/tourSessions.js";
import { getOperationKey } from "../utils/tourSessionKeys.js";

function newKey() {
  return globalThis.crypto?.randomUUID?.() || `tour-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useTourSessionsStore = defineStore("tourSessions", {
  state: () => ({
    csrfToken: "",
    identityId: "",
    items: [],
    trash: [],
    current: null,
    draftSnapshot: null,
    saveState: "idle",
    error: "",
    operationKeys: {},
  }),
  actions: {
    async prepare() {
      if (this.csrfToken && this.identityId) return this.csrfToken;
      const first = await bootstrapTourSessions();
      const second = await bootstrapTourSessions();
      if (!first.identity_id || first.identity_id !== second.identity_id) {
        const error = new Error("此浏览器未能保存匿名身份 Cookie，请允许本站使用 Cookie 后重试。");
        error.code = "TOUR_COOKIE_UNAVAILABLE";
        throw error;
      }
      this.identityId = second.identity_id;
      this.csrfToken = second.csrf_token || "";
      return this.csrfToken;
    },
    operationKey(operation, payload) {
      return getOperationKey(this.operationKeys, operation, payload, newKey);
    },
    clearOperationKey(fingerprint) {
      const next = { ...this.operationKeys };
      delete next[fingerprint];
      this.operationKeys = next;
    },
    async loadList() {
      this.error = "";
      try {
        await this.prepare();
        this.items = await fetchTourSessions();
      } catch (error) {
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : "暂时无法读取已保存的游览，请检查网络后重试。";
      }
    },
    async loadTrash() {
      await this.prepare();
      this.trash = await fetchTourTrash();
    },
    async open(id) {
      this.error = "";
      try {
        await this.prepare();
        this.current = await fetchTourSession(id);
        this.draftSnapshot = structuredClone(this.current.snapshot || {});
        this.saveState = "saved";
        return this.current;
      } catch {
        this.error = "无法打开这条游览，请刷新列表后重试。";
        return null;
      }
    },
    async create(payload) {
      this.error = "";
      this.saveState = "saving";
      this.draftSnapshot = structuredClone(payload.snapshot || {});
      const { fingerprint, key } = this.operationKey("create", payload);
      try {
        await this.prepare();
        this.current = await createTourSession(payload, this.csrfToken, key);
        this.draftSnapshot = structuredClone(this.current.snapshot || {});
        this.items = [this.current, ...this.items.filter(item => item.id !== this.current.id)];
        this.saveState = "saved";
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        this.saveState = error?.response?.status === 409 ? "conflict" : "error";
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : error?.response?.status === 409
          ? "该游览发生版本冲突，请刷新列表后重新打开。"
          : "保存失败，当前内容仍保留在页面中，可重试。";
        return null;
      }
    },
    async save(snapshot = this.draftSnapshot) {
      if (!this.current) return null;
      this.error = "";
      this.saveState = "saving";
      this.draftSnapshot = structuredClone(snapshot || {});
      const payload = { expected_version: this.current.version, snapshot: this.draftSnapshot };
      const { fingerprint, key } = this.operationKey(`save:${this.current.id}`, payload);
      try {
        await this.prepare();
        this.current = await saveTourSession(this.current.id, payload, this.csrfToken, key);
        this.draftSnapshot = structuredClone(this.current.snapshot || {});
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        this.saveState = "saved";
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        this.saveState = error?.response?.status === 409 ? "conflict" : "error";
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : error?.response?.status === 409
          ? "这条游览已在其他标签页更新。你的当前内容已保留，请重新打开后再继续。"
          : "保存失败，当前内容仍保留在页面中，可重试。";
        return null;
      }
    },
    async remove(id) {
      const item = this.items.find(entry => entry.id === id) || this.current;
      if (!item) return false;
      await this.prepare();
      await removeTourSession(id, item.version, this.csrfToken);
      this.items = this.items.filter(entry => entry.id !== id);
      if (this.current?.id === id) this.current = null;
      await this.loadTrash();
      return true;
    },
    async restoreDeleted(id) {
      await this.prepare();
      this.current = await restoreTourSession(id, this.csrfToken);
      this.items = [this.current, ...this.items.filter(item => item.id !== id)];
      await this.loadTrash();
      return this.current;
    },
    async purge(id) {
      await this.prepare();
      await purgeTourSession(id, this.csrfToken);
      this.trash = this.trash.filter(item => item.id !== id);
    },
    clearCurrent() {
      this.current = null;
      this.draftSnapshot = null;
      this.saveState = "idle";
      this.error = "";
    },
  },
});
