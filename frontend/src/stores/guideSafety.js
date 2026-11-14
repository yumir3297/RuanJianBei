import { defineStore } from "pinia";

const REAL_HOLD_KEY = "a5-guide-real-safety-hold-v1";
function readRealHold() {
  try { return globalThis.sessionStorage?.getItem(REAL_HOLD_KEY) === "1"; }
  catch { return false; }
}
function persistRealHold() {
  try { globalThis.sessionStorage?.setItem(REAL_HOLD_KEY, "1"); }
  catch { /* Current page remains held even when storage is unavailable. */ }
}

// Acknowledgement is not clearance. Persist only the real hold, not event data.
export const useGuideSafetyStore = defineStore("guideSafety", {
  state: () => ({ hold: readRealHold(), activeEvent: null, simulatedHold: false }),
  actions: {
    observeControllerState(state) {
      if (state?.activeSafetyEvent) {
        const wasRealHold = this.hold && !this.simulatedHold;
        this.activeEvent = { ...state.activeSafetyEvent };
        this.hold = true;
        this.simulatedHold = !wasRealHold && state.activeSafetyEvent.simulated === true;
        if (!this.simulatedHold) persistRealHold();
      } else if (this.hold) {
        this.activeEvent = null;
      }
    },
    resumeDemo() {
      if (!this.hold || !this.simulatedHold || this.activeEvent) return false;
      this.activeEvent = null;
      this.hold = false;
      this.simulatedHold = false;
      return true;
    },
  },
});
