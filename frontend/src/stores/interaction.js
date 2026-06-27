import { defineStore } from "pinia";

import { fetchQuickSelectBootstrap } from "../api/quickSelect";

const STORAGE_KEY = "a5-guided-selection-v1";
const VALID_MODES = new Set(["free_chat", "topic", "attraction", "route"]);

function emptyBootstrap() {
  return {
    topics: [],
    attractions: [],
    routes: [],
  };
}

export const useInteractionStore = defineStore("interaction", {
  state: () => ({
    bootstrap: emptyBootstrap(),
    loading: false,
    loaded: false,
    error: "",
    restored: false,
    mode: "free_chat",
    attractionId: null,
    topicKey: null,
    routeId: null,
  }),
  getters: {
    selectedAttraction(state) {
      return state.bootstrap.attractions.find((item) => item.id === state.attractionId) || null;
    },
    selectedTopic(state) {
      return state.bootstrap.topics.find((item) => item.key === state.topicKey) || null;
    },
    selectedRoute(state) {
      return state.bootstrap.routes.find((item) => item.id === state.routeId) || null;
    },
    breadcrumbs() {
      if (this.mode === "attraction") {
        return ["景点讲解", this.selectedAttraction?.title, this.selectedTopic?.label].filter(Boolean);
      }
      if (this.mode === "topic") {
        return ["话题探索", this.selectedTopic?.label].filter(Boolean);
      }
      if (this.mode === "route") {
        return ["路线规划", this.selectedRoute?.title].filter(Boolean);
      }
      return ["自由提问"];
    },
    selectionPayload(state) {
      return {
        mode: state.mode,
        attraction_id: state.mode === "attraction" ? state.attractionId : null,
        topic_key: ["attraction", "topic"].includes(state.mode) ? state.topicKey : null,
        route_id: state.mode === "route" ? state.routeId : null,
        interests: [],
        audience_type: null,
        available_hours: null,
        avoid_crowded: null,
      };
    },
  },
  actions: {
    getSelectionSnapshot() {
      return {
        mode: this.mode,
        attractionId: this.attractionId,
        topicKey: this.topicKey,
        routeId: this.routeId,
      };
    },
    restoreSelection(snapshot) {
      if (!snapshot || !VALID_MODES.has(snapshot.mode)) {
        return;
      }
      this.mode = snapshot.mode;
      this.attractionId = Number.isInteger(snapshot.attractionId) ? snapshot.attractionId : null;
      this.topicKey = typeof snapshot.topicKey === "string" ? snapshot.topicKey : null;
      this.routeId = typeof snapshot.routeId === "string" ? snapshot.routeId : null;
      if (this.loaded) {
        this.validateSelection();
      } else {
        this.persist();
      }
    },
    async initialize() {
      if (!this.restored) {
        this.restore();
      }
      if (!this.loaded && !this.loading) {
        await this.loadBootstrap();
      }
    },
    async loadBootstrap() {
      this.loading = true;
      this.error = "";
      try {
        const data = await fetchQuickSelectBootstrap();
        this.bootstrap = {
          topics: Array.isArray(data.topics) ? data.topics : [],
          attractions: Array.isArray(data.attractions) ? data.attractions : [],
          routes: Array.isArray(data.routes) ? data.routes : [],
        };
        this.loaded = true;
        this.validateSelection();
      } catch (error) {
        this.error = error?.message || "主动选择数据加载失败。";
      } finally {
        this.loading = false;
      }
    },
    setMode(mode) {
      if (!VALID_MODES.has(mode)) {
        return;
      }
      this.mode = mode;
      if (mode === "free_chat") {
        this.attractionId = null;
        this.topicKey = null;
        this.routeId = null;
      } else if (mode === "route") {
        this.attractionId = null;
        this.topicKey = null;
      } else {
        this.routeId = null;
        if (mode === "topic") {
          this.attractionId = null;
        }
      }
      this.persist();
    },
    selectAttraction(attractionId) {
      const normalizedId = attractionId === null || attractionId === "" ? null : Number(attractionId);
      this.mode = "attraction";
      this.attractionId = Number.isInteger(normalizedId) && normalizedId > 0 ? normalizedId : null;
      this.routeId = null;
      this.persist();
    },
    selectTopic(topicKey) {
      this.topicKey = topicKey || null;
      if (this.mode !== "attraction") {
        this.mode = "topic";
        this.attractionId = null;
      }
      this.routeId = null;
      this.persist();
    },
    selectRoute(routeId) {
      this.mode = "route";
      this.routeId = routeId || null;
      this.attractionId = null;
      this.topicKey = null;
      this.persist();
    },
    clearSelection() {
      this.setMode("free_chat");
    },
    applyResolvedSelection(selection) {
      if (!selection || !VALID_MODES.has(selection.mode)) {
        return;
      }
      this.mode = selection.mode;
      this.attractionId = Number.isInteger(selection.attraction_id) ? selection.attraction_id : null;
      this.topicKey = typeof selection.topic_key === "string" ? selection.topic_key : null;
      this.routeId = typeof selection.route_id === "string" ? selection.route_id : null;
      if (this.loaded) {
        this.validateSelection();
      } else {
        this.persist();
      }
    },
    restore() {
      this.restored = true;
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
          return;
        }
        const saved = JSON.parse(raw);
        this.mode = VALID_MODES.has(saved.mode) ? saved.mode : "free_chat";
        this.attractionId = Number.isInteger(saved.attractionId) ? saved.attractionId : null;
        this.topicKey = typeof saved.topicKey === "string" ? saved.topicKey : null;
        this.routeId = typeof saved.routeId === "string" ? saved.routeId : null;
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    },
    validateSelection() {
      const attractionExists = this.bootstrap.attractions.some((item) => item.id === this.attractionId);
      const topicExists = this.bootstrap.topics.some((item) => item.key === this.topicKey);
      const routeExists = this.bootstrap.routes.some((item) => item.id === this.routeId);

      if (!attractionExists) {
        this.attractionId = null;
      }
      if (!topicExists) {
        this.topicKey = null;
      }
      if (!routeExists) {
        this.routeId = null;
      }

      if (this.mode === "attraction" && this.attractionId === null) {
        this.mode = this.topicKey ? "topic" : "free_chat";
      }
      if (this.mode === "topic" && this.topicKey === null) {
        this.mode = "free_chat";
      }
      if (this.mode === "route" && this.routeId === null) {
        this.mode = "free_chat";
      }
      this.persist();
    },
    persist() {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          mode: this.mode,
          attractionId: this.attractionId,
          topicKey: this.topicKey,
          routeId: this.routeId,
        }),
      );
    },
  },
});
