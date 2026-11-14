import { defineStore } from "pinia";

// Demo map names are not K01 IDs or tour stop IDs. This is runtime-only playback evidence.
export const useGuidePlaybackStore = defineStore("guidePlayback", {
  state: () => ({ completedDemoSpots: [] }),
  actions: {
    recordCompletedDemoSpot(name) {
      if (typeof name !== "string" || !name.trim()) return false;
      if (!this.completedDemoSpots.includes(name)) this.completedDemoSpots.push(name);
      return true;
    },
    clearDemoPlayback() { this.completedDemoSpots = []; },
  },
});
