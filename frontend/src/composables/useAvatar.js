import { ref } from "vue";
import { selectSpeakingAction } from "../components/avatar-actions.js";

export const GUIDE_PERSONA = {
  name: "小灵",
  greeting: "您好！我是灵山智慧导游小灵，很高兴陪您一起游览。想了解景点故事、规划路线，或认一认眼前的风景，都可以问我。",
  contextIntro: {
    general: "让我为您介绍一下：",
    photo: "让我看看您拍到了什么……",
    route: "为您规划游览路线……",
  },
};

const STATES = ["idle", "listening", "thinking", "speaking", "happy", "apology", "guide"];

export function useAvatar() {
  const currentState = ref("idle");
  const currentEmotion = ref("neutral");
  const currentViseme = ref("");
  const currentAction = ref("");
  const actionKey = ref(0);

  let idleTimer = null;
  let lastSpeakingGestureAt = 0;

  const SPEAKING_GESTURE_INTERVAL_MS = 9000;

  function setState(state) {
    if (!STATES.includes(state)) {
      return;
    }
    currentState.value = state;
    if (["idle", "listening", "thinking"].includes(state)) {
      currentEmotion.value = "neutral";
    }
    resetIdleTimer(state);
  }

  function handleAvatarEvent(payload) {
    if (!payload || typeof payload !== "object") return;
    if (payload.action) {
      triggerAction(payload.action);
      lastSpeakingGestureAt = Date.now();
    } else if (payload.viseme_text !== undefined) {
      const now = Date.now();
      if (now - lastSpeakingGestureAt >= SPEAKING_GESTURE_INTERVAL_MS) {
        const speakingAction = selectSpeakingAction(payload.viseme_text);
        if (speakingAction) {
          triggerAction(speakingAction);
          lastSpeakingGestureAt = now;
        }
      }
    }
    if (payload.emotion) {
      currentEmotion.value = payload.emotion;
      if (payload.emotion === "happy") {
        setState("happy");
        return;
      }
      if (payload.emotion === "apology") {
        setState("apology");
        return;
      }
      if (payload.emotion === "speaking") {
        setState("speaking");
        return;
      }
      if (payload.emotion === "guide") {
        setState("guide");
        return;
      }
    }
    if (payload.viseme_text !== undefined) {
      currentViseme.value = payload.viseme_text || "";
      if (currentState.value !== "happy" && currentState.value !== "apology" && currentState.value !== "guide") {
        setState("speaking");
      }
    }
  }

  function triggerAction(action) {
    if (typeof action !== "string" || !action.trim()) return;
    currentAction.value = action.trim();
    // 即使连续触发同名动作，递增 key 也能让 ThreeAvatar 收到新的播放请求。
    actionKey.value += 1;
  }

  function onAudioEnded() {
    if (currentState.value === "speaking") {
      setIdleWithDelay(500);
    }
  }

  function setIdleWithDelay(delayMs = 500) {
    if (idleTimer) {
      clearTimeout(idleTimer);
    }
    idleTimer = setTimeout(() => {
      if (currentState.value === "speaking") {
        setState("idle");
      }
      idleTimer = null;
    }, delayMs);
  }

  function resetIdleTimer(state) {
    if (idleTimer && state !== "speaking") {
      clearTimeout(idleTimer);
      idleTimer = null;
    }
  }

  return {
    currentState,
    currentEmotion,
    currentViseme,
    currentAction,
    actionKey,
    setState,
    triggerAction,
    handleAvatarEvent,
    onAudioEnded,
  };
}
