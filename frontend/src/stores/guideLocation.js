import { defineStore } from "pinia";

// Runtime-only view of the active map's position; no location is persisted.
export const useGuideLocationStore = defineStore("guideLocation", {
  state: () => ({ mapActive: false, position: null, mode: "unavailable" }),
  actions: {
    activate(position, mode) {
      this.mapActive = true;
      this.update(position, mode);
    },
    update(position, mode) {
      if (!this.mapActive) return;
      this.position = position ? { ...position } : null;
      this.mode = mode || "unavailable";
    },
    deactivate() {
      this.mapActive = false;
      this.position = null;
      this.mode = "unavailable";
    },
  },
});
