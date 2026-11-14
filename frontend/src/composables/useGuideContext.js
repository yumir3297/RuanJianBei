import { onBeforeUnmount, onMounted, ref } from "vue";
import { fetchGuideBootstrap, requestGuideDecision } from "../api/guideContext";
import { createGuideController } from "../guide/scheduler";
import { useGuideSafetyStore } from "../stores/guideSafety";

export function useGuideContext() {
  const safety = useGuideSafetyStore();
  const bootstrap = ref(null);
  const state = ref({ status: "off", activeSafetyEvent: null });
  const result = ref(null);
  const busy = ref(false);
  const error = ref("");
  let pendingController = null;
  const controller = createGuideController({
    api: { decide: (payload) => {
      pendingController = new AbortController();
      return requestGuideDecision(payload, { signal: pendingController.signal });
    } },
    effects: { cancel_pending: () => { pendingController?.abort(); pendingController = null; } },
  });
  const unsubscribe = controller.subscribe((next) => {
    safety.observeControllerState(next);
    state.value = next;
  });

  onMounted(async () => {
    try { bootstrap.value = await fetchGuideBootstrap(); }
    catch { bootstrap.value = { available: false, enabled: false, demo_enabled: false }; }
  });
  onBeforeUnmount(() => { controller.dispatch({ type: "dispose" }); unsubscribe(); });

  async function enable() {
    if (!bootstrap.value?.enabled) return false;
    controller.dispatch({ type: "enable" });
    return true;
  }
  async function assess(payload) {
    if (busy.value || !bootstrap.value?.enabled) return null;
    busy.value = true;
    error.value = "";
    try {
      const response = await controller.evaluate(payload);
      if (response?.stale) return null;
      result.value = response;
      if (!result.value?.available) error.value = "情境决策暂不可用；现有问答与讲解不受影响。";
      return result.value;
    } finally {
      busy.value = false;
    }
  }
  function stop() { controller.dispatch({ type: "user_stop" }); }

  return { bootstrap, state, result, busy, error, enable, assess, stop, dispatch: controller.dispatch, safety, fetchCurrentBootstrap: fetchGuideBootstrap };
}
