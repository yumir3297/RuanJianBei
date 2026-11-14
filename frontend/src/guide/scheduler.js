export const initialGuideState = () => ({
  status: "off",
  generation: 0,
  activeSafetyEvent: null,
  dismissedEventIds: [],
  mapActive: false,
  userStopped: false,
});

export function reduceGuideState(state, event) {
  const current = state || initialGuideState();
  switch (event?.type) {
    case "enable":
      return { state: { ...current, status: "idle", userStopped: false }, effects: [] };
    case "disable":
    case "dispose":
      return { state: { ...current, status: "off", generation: current.generation + 1, activeSafetyEvent: null }, effects: ["cancel_pending"] };
    case "map_active":
      return { state: { ...current, mapActive: Boolean(event.active), generation: event.active ? current.generation : current.generation + 1, status: event.active && current.status === "suspended" ? "idle" : (!event.active && current.status !== "off" ? "suspended" : current.status) }, effects: event.active ? [] : ["stop_location", "cancel_pending"] };
    case "decision_started":
      return { state: { ...current, status: "deciding", generation: current.generation + 1 }, effects: ["cancel_pending"] };
    case "context_changed":
      return {
        state: {
          ...current,
          status: ["deciding", "narrating"].includes(current.status) ? "idle" : current.status,
          generation: current.generation + 1,
        },
        effects: ["cancel_pending"],
      };
    case "decision_received":
      if (event.generation !== current.generation || current.status === "off") return { state: current, effects: [] };
      return { state: { ...current, status: event.action === "none" ? "idle" : "narrating" }, effects: event.action === "none" ? [] : ["narrate"] };
    case "safety_raised": {
      const safety = event.safetyEvent;
      if (!safety?.event_id) return { state: current, effects: [] };
      if (current.activeSafetyEvent?.event_id === safety.event_id) {
        const updated = { ...current.activeSafetyEvent, ...safety };
        if (JSON.stringify(updated) === JSON.stringify(current.activeSafetyEvent)) return { state: current, effects: [] };
        return { state: { ...current, status: "interrupted", activeSafetyEvent: updated }, effects: ["show_safety"] };
      }
      if (current.activeSafetyEvent && Number(safety.priority || 0) <= Number(current.activeSafetyEvent.priority || 0)) return { state: current, effects: [] };
      return { state: { ...current, status: "interrupted", generation: current.generation + 1, activeSafetyEvent: safety, userStopped: false }, effects: ["cancel_pending", "stop_audio", "show_safety"] };
    }
    case "safety_cleared":
      if (!current.activeSafetyEvent || (event.eventId && event.eventId !== current.activeSafetyEvent.event_id)) return { state: current, effects: [] };
      return { state: { ...current, status: "idle", activeSafetyEvent: null }, effects: ["offer_manual_resume"] };
    case "user_stop":
      return { state: { ...current, status: "idle", generation: current.generation + 1, userStopped: true }, effects: ["cancel_pending", "stop_audio"] };
    case "user_activity":
      return { state: { ...current, generation: current.generation + 1, userStopped: true }, effects: ["cancel_resume"] };
    default:
      return { state: current, effects: [] };
  }
}

export function createGuideController(dependencies = {}) {
  let state = initialGuideState();
  const listeners = new Set();
  function dispatch(event) {
    const result = reduceGuideState(state, event);
    state = result.state;
    for (const effect of result.effects) dependencies.effects?.[effect]?.(state, event);
    for (const listener of listeners) listener(state, event);
    return state;
  }
  return {
    dispatch,
    getState: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    async evaluate(payload) {
      dispatch({ type: "decision_started" });
      const generation = state.generation;
      try {
        const response = await dependencies.api?.decide?.(payload);
        if (generation !== state.generation || state.status === "off" || state.status === "suspended") return { available: false, reason: "stale_response", stale: true };
        if (response?.available === false) return response;
        if (response?.safety_events?.length) {
          [...response.safety_events]
            .sort((a, b) => Number(b?.priority || 0) - Number(a?.priority || 0))
            .forEach((safetyEvent) => dispatch({ type: "safety_raised", safetyEvent }));
          if (state.status === "deciding") dispatch({ type: "decision_received", generation, action: "none" });
        } else dispatch({ type: "decision_received", generation, action: response?.decision?.action || "none" });
        return response;
      } catch (error) {
        if (generation !== state.generation || state.status === "off" || state.status === "suspended") return { available: false, reason: "stale_response", stale: true };
        if (generation === state.generation) dispatch({ type: "decision_received", generation, action: "none" });
        return { available: false, reason: "network_error", error };
      }
    },
  };
}
