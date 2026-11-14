export const GUIDE_DEMO_SCENARIO = Object.freeze({
  id: "weather-interruption-v1",
  label: "预警抢占与人工恢复",
  mode: "simulated",
  steps: Object.freeze([
    { type: "context", remaining_minutes: 20 },
    { type: "safety", event_id: "demo-thunderstorm", severity: "Severe", headline: "演示：雷电预警变化", instruction: "此为模拟事件，请留意现场公告；真实服务不依据演示信息采取行动。" },
    { type: "acknowledge", requires_user_action: true },
    { type: "resume", requires_user_action: true, action: "short_narration" },
  ]),
});

export function createDemoCrowdDecision(now = new Date()) {
  return {
    action: "review_itinerary",
    reason_codes: ["demo_crowd_pressure"],
    simulated: true,
    data_mode: "demo",
    expires_at: new Date(now.getTime() + 5 * 60_000).toISOString(),
    reasons: ["演示情境显示下一景点客流偏高；这是模拟数据，不代表实时人数。"],
    rule_ids: ["DEMO_CROWD_PRESSURE"],
    suggestions: [{ suggestion_id: "demo_avoid_crowd", action: "review_itinerary", requires_confirmation: true }],
    evidence_refs: [{ type: "simulated_crowd_level", source: "内置演示场景", observed_at: now.toISOString() }],
    evidence_status: { weather: "unknown", alerts: "none_verified", location: "demo_only", crowd: "simulated" },
  };
}

export function createDemoWeatherDecision(now = new Date()) {
  const observedAt = now.toISOString();
  return {
    action: "full_narration",
    reason_codes: ["standard_context"],
    simulated: true,
    data_mode: "demo",
    expires_at: new Date(now.getTime() + 5 * 60_000).toISOString(),
    reasons: ["演示情境显示小雨；讲解将避免要求游客长时间驻足，不触发安全预警。"],
    rule_ids: ["DEMO_WEATHER_PRECIPITATION_ADAPTATION"],
    weather_adaptation: { kind: "precipitation", condition: "小雨", source: "内置演示场景", observed_at: observedAt, simulated: true },
    evidence_refs: [{ type: "simulated_weather", source: "内置演示场景", observed_at: observedAt }],
    evidence_status: { weather: "simulated", alerts: "none_verified", location: "demo_only" },
    safety_events: [],
    suggestions: [],
  };
}

export function createDemoSafetyEvent(scenario = GUIDE_DEMO_SCENARIO) {
  const warning = scenario.steps.find((step) => step.type === "safety");
  return {
    event_id: warning.event_id,
    type: "demo_warning",
    priority: 80,
    severity: warning.severity,
    headline: warning.headline,
    instruction: warning.instruction,
    source: "simulated_scenario",
    simulated: true,
  };
}

export function createDemoScenarioController({ dispatch, setDecision, onAcknowledged } = {}) {
  let stage = "idle";
  return {
    getStage: () => stage,
    reset() { stage = "idle"; },
    start() {
      if (stage !== "idle" && stage !== "complete") return false;
      dispatch?.({ type: "enable" });
      setDecision?.({ action: "short_narration", reason_codes: ["demo_time_budget"] }, { simulated: true });
      stage = "awaiting_warning";
      return true;
    },
    raiseWarning() {
      if (stage !== "awaiting_warning") return false;
      setDecision?.({ action: "none", reason_codes: ["demo_safety_priority"] }, { simulated: true });
      dispatch?.({ type: "safety_raised", safetyEvent: createDemoSafetyEvent() });
      stage = "awaiting_acknowledgement";
      return true;
    },
    acknowledge() {
      if (stage !== "awaiting_acknowledgement") return false;
      dispatch?.({ type: "safety_cleared", eventId: "demo-thunderstorm" });
      onAcknowledged?.();
      stage = "awaiting_manual_resume";
      return true;
    },
    resume() {
      if (stage !== "awaiting_manual_resume") return false;
      setDecision?.({ action: "short_narration", reason_codes: ["demo_manual_resume"] }, { simulated: true });
      stage = "complete";
      return true;
    },
  };
}
