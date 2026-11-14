<template>
    <section class="cass-panel" aria-labelledby="cass-title">
    <header><div><h3 id="cass-title">情境自适应导览</h3><small>情境感知 · 生成服务与规则协同</small></div><span :class="['cass-pill', statusClass]">{{ statusLabel }}</span></header>
    <p class="cass-copy">位置、天气、偏好和行程共同形成服务情境；安全规则独立校验来源与时效。</p>
    <p class="cass-state">定位：{{ locationLabel }}<template v-if="context.location?.observedAt"> · 采集于 {{ context.location.observedAt }}</template><template v-if="!mapActive"> · 地图未激活，定位已停止</template></p>
    <p v-if="!bootstrap?.enabled" class="cass-state">服务尚未启用。既有导览功能照常使用。</p>
    <template v-else>
      <label class="cass-budget">剩余时间
        <select v-model.number="minutes" aria-label="剩余游览时间">
          <option :value="20">约 20 分钟</option><option :value="45">约 45 分钟</option><option :value="90">约 90 分钟</option>
        </select>
      </label>
      <label v-if="bootstrap.catalog?.length" class="cass-budget">讲解景点
        <select v-model="selectedSpotCode" aria-label="选择情境讲解景点"><option v-for="spot in bootstrap.catalog" :key="spot.spot_code" :value="spot.spot_code">{{ spot.title }}</option></select>
      </label>
      <div v-if="state.status !== 'off' && nearbySpot && nearbySpot.spot.spot_code !== selectedSpotCode" class="cass-nearby">
        <button type="button" class="cass-generate" @click="selectedSpotCode = nearbySpot.spot.spot_code">按位置选择附近景点：{{ nearbySpot.spot.title }}（约 {{ Math.round(nearbySpot.distanceM) }} 米）</button>
        <small>仅使用新鲜、精度合格的真实定位和带依据的已发布坐标；这是讲解候选，不证明已经到场。</small>
      </div>
      <label class="cass-budget">兴趣主题
        <select v-model="interests" multiple aria-label="选择兴趣主题"><option value="history">历史</option><option value="nature">自然</option><option value="architecture">建筑</option><option value="culture">文化</option><option value="family">亲子</option><option value="photography">摄影</option><option value="food">饮食</option></select>
      </label>
      <div class="cass-actions">
        <button v-if="state.status === 'off'" type="button" @click="enable">开启情境导览</button>
        <button v-else type="button" :disabled="busy" @click="assess">{{ busy ? '正在核验…' : '评估当前情境' }}</button>
        <button v-if="bootstrap.demo_enabled" type="button" class="secondary" :disabled="busy || safety?.hold || Boolean(state.activeSafetyEvent)" @click="runDemo">演示预警抢占</button>
        <button v-if="bootstrap.demo_enabled" type="button" class="secondary" :disabled="busy || safety?.hold || Boolean(state.activeSafetyEvent)" @click="runCrowdDemo">演示客流变化</button>
        <button v-if="bootstrap.demo_enabled" type="button" class="secondary" :disabled="busy || safety?.hold || Boolean(state.activeSafetyEvent)" @click="runWeatherDemo">演示雨天讲解适配</button>
        <button v-if="state.status !== 'off'" type="button" class="secondary" @click="stop">停止当前输出</button>
        <button v-if="state.status !== 'off'" type="button" class="secondary" :disabled="safety?.hold" @click="disable">关闭情境导览</button>
      </div>
      <p v-if="result?.decision" class="cass-result" role="status">策略：{{ actionText }} · {{ result.reasons?.[0] || reasonText }}</p>
      <p v-if="result?.weather_adaptation" class="cass-evidence">{{ result.weather_adaptation.simulated ? '模拟天气适配' : '景区天气适配' }}：{{ result.weather_adaptation.condition }} · {{ result.weather_adaptation.source }}{{ result.weather_adaptation.simulated ? '（模拟，不作为安全证据）' : '（景区默认位置实况）' }}；仅调整讲解节奏，不推断景点环境或安全状态。</p>
      <p v-if="hasAcknowledgedSafety && result?.safety_events?.length" class="cass-state" role="status">该预警仍处于有效期内，当前不会恢复普通讲解。可稍后重新核验。</p>
      <p v-if="safety?.hold && !safety?.simulatedHold && !state.activeSafetyEvent" class="cass-state" role="status">预警结束状态尚未核实，普通讲解保持暂停，请遵循现场指引。</p>
      <button v-if="hasAcknowledgedSafety" type="button" class="cass-generate" :disabled="busy" @click="recheckAfterSafety">{{ busy ? '正在重新核验…' : '重新核验后再继续' }}</button>
      <button v-if="demoStage === 'awaiting_warning'" type="button" class="cass-generate" @click="raiseDemoWarning">继续演示：模拟预警变化</button>
      <button v-if="demoStage === 'awaiting_manual_resume'" type="button" class="cass-generate" @click="resumeDemo">继续演示（需再次确认）</button>
      <button v-if="narrationRequest" type="button" class="cass-generate" :disabled="narrationChecking || safety?.hold" @click="requestNarration">{{ narrationChecking ? '正在核对景点…' : (result?.simulated ? '按演示情境生成讲解' : '按此情境生成讲解') }}</button>
      <p v-if="narrationError" class="cass-error" role="status">{{ narrationError }}</p>
      <button v-if="itinerarySuggestionRequest" type="button" class="cass-generate" :disabled="busy || tour?.proposalLoading || safety?.hold" @click="requestProposal">生成路线调整提案</button>
      <p v-if="itinerarySuggestionRequest" class="cass-state">提案只供审核；应用前会展示路线差异并再次核对行程版本。</p>
      <p v-if="result?.evidence_status" class="cass-evidence">数据性质：{{ dataModeText }}；天气：{{ result.evidence_status.weather }}；预警：{{ result.evidence_status.alerts }}；位置：{{ result.evidence_status.location }}</p>
      <ul v-if="result?.evidence_refs?.length" class="cass-evidence-list" aria-label="决策依据"><li v-for="evidence in result.evidence_refs" :key="`${evidence.type}-${evidence.source}`">{{ evidence.source }}<template v-if="evidence.observed_at"> · {{ evidence.observed_at }}</template></li></ul>
      <p v-if="result?.rule_ids?.length" class="cass-evidence">规则：{{ result.rule_ids.join('、') }} · 建议有效至 {{ result.expires_at }}</p>
      <GuideSafetyNotice v-if="state.activeSafetyEvent" :event="state.activeSafetyEvent" @clear="clearSafety" @dismiss="clearSafety" />
      <button type="button" class="sos-link" @click="showSos = !showSos">本地求助入口</button>
      <p v-if="showSos" class="cass-state">请核对景区服务菜单中的联系电话，或联系现场工作人员。本入口不会发送位置或声称已接警。</p>
      <p v-if="error" class="cass-error" role="status">{{ error }}</p>
    </template>
    <p class="cass-foot">真实位置仅作为客户端提示；演示数据不会转为真实安全证据。</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useGuideContext } from "../../composables/useGuideContext";
import { buildAdaptiveNarrationRequest, buildGuideContext, buildItinerarySuggestionRequest, findNearbyPublishedSpot, isGuideDecisionExpired } from "../../guide/context";
import { createDemoCrowdDecision, createDemoScenarioController, createDemoWeatherDecision } from "../../guide/scenario";
import GuideSafetyNotice from "./GuideSafetyNotice.vue";

const props = defineProps({
  position: { type: Object, default: null },
  locationMode: { type: String, default: "unavailable" },
  mapActive: { type: Boolean, default: false },
  tour: { type: Object, default: null },
  playbackBusy: { type: Boolean, default: false },
});
const emit = defineEmits(["interrupt", "ask", "proposal"]);
const { bootstrap, state, result, busy, error, enable: start, assess: request, stop: halt, dispatch, safety, fetchCurrentBootstrap } = useGuideContext();
const minutes = ref(45);
const selectedSpotCode = ref("");
const interests = ref([]);
const showSos = ref(false);
const hasAcknowledgedSafety = ref(false);
const demoStage = ref("idle");
const clockNow = ref(Date.now());
const narrationChecking = ref(false);
const narrationError = ref("");
let clockTimer = null;
let narrationCheckGeneration = 0;

const statusLabel = computed(() => ({ off: "未开启", idle: "已开启", deciding: "核验中", narrating: "服务就绪", interrupted: "安全优先" }[state.value.status] || "已暂停"));
const statusClass = computed(() => state.value.status === "interrupted" ? "urgent" : "");
const context = computed(() => buildGuideContext({ position: props.position, mode: props.locationMode, nowMs: clockNow.value }));
const nearbySpot = computed(() => props.mapActive && props.locationMode === "real"
  ? findNearbyPublishedSpot(context.value.location, bootstrap.value?.catalog || [])
  : null);
const locationLabel = computed(() => {
  if (!props.mapActive) return "未采集";
  if (props.locationMode === "sim") return "演示位置（非安全证据）";
  if (props.locationMode === "real" && context.value.location?.validForSafety) return `真实设备提示，精度约 ${Math.round(context.value.location.accuracyM)} 米（非到场证明）`;
  return "不可用于安全判断";
});
const actionText = computed(() => ({ short_narration: "简短讲解", full_narration: "常规讲解", defer_narration: "稍后讲解", none: "等待条件" }[result.value?.decision?.action] || "等待条件"));
const selectedSpot = computed(() => bootstrap.value?.catalog?.find((item) => item.spot_code === selectedSpotCode.value) || bootstrap.value?.catalog?.[0] || null);
const narrationRequest = computed(() => {
  if (isGuideDecisionExpired(result.value, clockNow.value)) return null;
  if (result.value?.simulated && demoStage.value !== "complete") return null;
  return buildAdaptiveNarrationRequest({
    decision: result.value?.decision,
    spot: selectedSpot.value,
    interests: interests.value,
    remainingMinutes: minutes.value,
    simulated: result.value?.simulated,
    weatherAdaptation: result.value?.weather_adaptation,
    tour: props.tour,
    catalog: bootstrap.value?.catalog || [],
  });
});
const itinerarySuggestionRequest = computed(() => {
  if (isGuideDecisionExpired(result.value, clockNow.value)) return null;
  if (props.tour?.snapshot?.schema_version !== 2 || !props.tour?.id) return null;
  return buildItinerarySuggestionRequest({ decision: result.value?.decision, remainingMinutes: minutes.value, simulated: result.value?.simulated === true });
});
const reasonText = computed(() => ({ limited_time: "时间有限", standard_context: "按常规情境", playback_busy: "当前媒体播放中", safety_priority: "有效预警优先", demo_manual_resume: "演示流程人工恢复" }[result.value?.decision?.reason_codes?.[0]] || "情境评估完成"));
const dataModeText = computed(() => ({ demo: "演示数据", live: "含实时来源", partial: "情境数据不完整" }[result.value?.data_mode] || (result.value?.simulated ? "演示数据" : "状态未知")));

const demoScenario = createDemoScenarioController({
  dispatch,
  setDecision,
  onAcknowledged() { hasAcknowledgedSafety.value = true; },
});

watch(() => props.mapActive, (active) => dispatch({ type: "map_active", active }), { immediate: true });
watch([
  minutes,
  selectedSpotCode,
  interests,
  () => props.tour?.id,
  () => props.tour?.version,
  () => props.tour?.progress?.progress_version,
  () => props.locationMode,
  () => props.position?.observedAt ?? props.position?.ts,
  () => props.playbackBusy,
], () => {
  narrationCheckGeneration += 1;
  narrationError.value = "";
  if (result.value) result.value = null;
  if (!safety?.hold) hasAcknowledgedSafety.value = false;
  dispatch({ type: "context_changed" });
});
watch(() => state.value.status, (status, previous) => {
  if (status === "interrupted" && previous !== "interrupted") {
    narrationCheckGeneration += 1;
    emit("interrupt");
  }
});
watch(clockNow, (now) => {
  if (isGuideDecisionExpired(result.value, now)) {
    result.value = null;
    if (!safety?.hold) hasAcknowledgedSafety.value = false;
  }
});
onMounted(() => { clockTimer = setInterval(() => { clockNow.value = Date.now(); }, 1000); });
onBeforeUnmount(() => { narrationCheckGeneration += 1; if (clockTimer) clearInterval(clockTimer); });

async function requestNarration() {
  if (narrationChecking.value || safety?.hold || !narrationRequest.value) return;
  const generation = ++narrationCheckGeneration;
  const originalResult = result.value;
  const originalRequest = JSON.stringify(narrationRequest.value);
  const digest = bootstrap.value?.catalog_digest;
  const siteId = bootstrap.value?.site_id;
  narrationChecking.value = true;
  narrationError.value = "";
  try {
    const current = await fetchCurrentBootstrap();
    if (generation !== narrationCheckGeneration || safety?.hold || result.value !== originalResult
        || isGuideDecisionExpired(result.value, Date.now()) || JSON.stringify(narrationRequest.value) !== originalRequest) return;
    if (!current?.enabled || !siteId || !digest || !current.catalog_digest || current.catalog_digest !== digest || current.site_id !== siteId) {
      bootstrap.value = current;
      result.value = null;
      narrationError.value = "景点资料已更新，请重新评估当前情境。";
      return;
    }
    emit("ask", narrationRequest.value);
  } catch {
    if (generation === narrationCheckGeneration) narrationError.value = "暂时无法核对景点资料，请稍后重试。";
  } finally {
    narrationChecking.value = false;
  }
}

async function enable() {
  selectedSpotCode.value = bootstrap.value?.catalog?.[0]?.spot_code || "";
  const ok = await start();
  if (!ok) return;
  await assess();
}
async function assess() {
  await request({
    preferences: { remaining_minutes: minutes.value, proactive_enabled: true, interests: interests.value },
    spot_code: selectedSpot.value?.spot_code || null,
    published_revision_id: selectedSpot.value?.published_revision_id || null,
    catalog_digest: bootstrap.value?.catalog_digest || null,
    tour_session_id: props.tour?.id || null,
    expected_tour_version: props.tour?.version || null,
    progress_version: props.tour?.progress?.progress_version || null,
    playback_busy: props.playbackBusy,
  });
}
function stop() { narrationCheckGeneration += 1; halt(); emit("interrupt"); }
function requestProposal() { if (!safety?.hold && itinerarySuggestionRequest.value) emit("proposal", itinerarySuggestionRequest.value); }
function disable() { narrationCheckGeneration += 1; dispatch({ type: "disable" }); demoScenario.reset(); demoStage.value = "idle"; hasAcknowledgedSafety.value = false; emit("interrupt"); }
function setDecision(decision, metadata = {}) {
  result.value = { available: true, decision, safety_events: [], data_mode: "demo", evidence_status: { weather: "unknown", alerts: "simulated", location: "demo_only" }, ...metadata };
}
function clearSafety() {
  if (state.value.activeSafetyEvent?.simulated) {
    demoScenario.acknowledge();
    demoStage.value = demoScenario.getStage();
  } else {
    dispatch({ type: "safety_cleared" });
    hasAcknowledgedSafety.value = true;
  }
}
async function recheckAfterSafety() {
  await assess();
  // "none_verified" can also mean that the source is unavailable; it is not
  // proof that a real warning has cleared.
  if (!safety?.hold && !result.value?.safety_events?.length) hasAcknowledgedSafety.value = false;
}
function runDemo() {
  hasAcknowledgedSafety.value = false;
  minutes.value = 20;
  if (demoScenario.start()) demoStage.value = demoScenario.getStage();
}
function runCrowdDemo() {
  if (!bootstrap.value?.demo_enabled) return;
  dispatch({ type: "enable" });
  demoStage.value = "complete";
  const decision = createDemoCrowdDecision();
  setDecision(decision, { simulated: true, ...decision });
}
function runWeatherDemo() {
  if (!bootstrap.value?.demo_enabled) return;
  dispatch({ type: "enable" });
  demoStage.value = "complete";
  const decision = createDemoWeatherDecision();
  setDecision(decision, { simulated: true, ...decision });
}
function raiseDemoWarning() { if (demoScenario.raiseWarning()) demoStage.value = demoScenario.getStage(); }
function resumeDemo() {
  if (demoScenario.resume()) {
    safety?.resumeDemo();
    demoStage.value = demoScenario.getStage();
    hasAcknowledgedSafety.value = false;
  }
}
</script>

<style scoped>
.cass-panel{display:grid;gap:.6rem;padding:.85rem;border:1px solid #cfd9e3;border-radius:14px;background:rgba(255,255,255,.92);box-shadow:0 8px 24px #18304412}.cass-panel header{display:flex;justify-content:space-between;gap:.5rem;align-items:center}.cass-panel h3{font-size:1rem;margin:0}.cass-panel small,.cass-foot,.cass-evidence{font-size:.76rem;color:#687586}.cass-copy,.cass-state,.cass-result{margin:0;font-size:.86rem;line-height:1.5}.cass-budget{display:flex;align-items:center;justify-content:space-between;font-size:.83rem}.cass-budget select{padding:.35rem;border-radius:7px;border:1px solid #ccd3db}.cass-actions{display:flex;gap:.4rem;flex-wrap:wrap}.cass-nearby{display:grid;gap:.3rem}.cass-actions button,.sos-link,.cass-generate{padding:.45rem .65rem;border:0;border-radius:8px;background:#155e75;color:white}.cass-actions .secondary{background:#e9eef2;color:#243340}.cass-pill{font-size:.72rem;padding:.2rem .45rem;background:#e6edf0;border-radius:999px}.cass-pill.urgent{background:#ffe5da;color:#a02b12}.cass-error{color:#9d351e;margin:0;font-size:.82rem}.sos-link{justify-self:start;background:transparent;color:#315a70;padding-left:0;text-decoration:underline}.cass-foot{margin:0}
</style>
