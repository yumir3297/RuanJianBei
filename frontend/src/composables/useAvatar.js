import { ref } from "vue";

export const GUIDE_PERSONA = {
  name: "小灵",
  greeting: "您好！我是灵山智慧导游小灵，很高兴陪您一起游览。想了解景点故事、规划路线，或认一认眼前的风景，都可以问我。",
  contextIntro: {
    general: "让我为您介绍一下：",
    photo: "让我看看您拍到了什么……",
    route: "为您规划游览路线……",
  },
};

const STATES = ["idle", "listening", "thinking", "speaking", "happy", "apology"];

export function useAvatar() {
  const currentState = ref("idle");
  const currentEmotion = ref("neutral");
  const currentViseme = ref("");

  let idleTimer = null;

  function setState(state) {
    if (!STATES.includes(state)) {
      return;
    }
    currentState.value = state;
    resetIdleTimer(state);
  }

  function handleAvatarEvent(payload) {
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
    }
    if (payload.viseme_text !== undefined) {
      currentViseme.value = payload.viseme_text || "";
      if (currentState.value !== "happy" && currentState.value !== "apology") {
        setState("speaking");
      }
    }
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
    setState,
    handleAvatarEvent,
    onAudioEnded,
  };
}
