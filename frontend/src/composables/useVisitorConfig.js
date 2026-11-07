import { onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { fetchVisitorConfig } from "../api/visitorConfig.js";
import { createVisitorConfigRefresher } from "../utils/visitorConfigRefresh.js";

const DEFAULT_AVATAR = Object.freeze({ model_key: "hanfu", voice_type: "gentle-female" });

function sameAvatar(left, right) {
  return left?.model_key === right?.model_key && left?.voice_type === right?.voice_type;
}

export function useVisitorConfig({
  isIdle = () => true,
  fetchConfig = fetchVisitorConfig,
  clock = globalThis,
  isVisible = () => typeof document === "undefined" || !document.hidden,
} = {}) {
  const avatar = shallowRef({ ...DEFAULT_AVATAR });
  const display = shallowRef(null);
  const loading = ref(true);

  const refresher = createVisitorConfigRefresher({
    fetchConfig,
    clock,
    isVisible,
    isIdle,
    onApply(config) {
      if (config?.display) display.value = config.display;
      if (config?.avatar && !sameAvatar(avatar.value, config.avatar)) {
        avatar.value = { model_key: config.avatar.model_key, voice_type: config.avatar.voice_type };
      }
      loading.value = false;
    },
  });

  const stopIdleWatch = watch(isIdle, (idle) => {
    if (idle) refresher.flushPending();
  });
  let removeVisibilityListener = null;
  if (typeof document !== "undefined") {
    const onVisibilityChange = () => refresher.setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVisibilityChange);
    removeVisibilityListener = () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }

  const initialRefresh = refresher.start();
  initialRefresh.finally(() => { loading.value = false; });
  function refresh() {
    return refresher.refresh().finally(() => { loading.value = false; });
  }

  onBeforeUnmount(() => {
    stopIdleWatch();
    removeVisibilityListener?.();
    refresher.dispose();
  });

  return {
    avatar,
    display,
    loading,
    refresh,
  };
}
