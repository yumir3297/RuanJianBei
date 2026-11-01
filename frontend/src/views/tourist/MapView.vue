<template>
  <div class="guide-tool-content map-tool">
    <p class="tool-description">地图 × 数字人导览：查看天气与演示客流，选一条路线，让导游陪你出发。</p>

    <div class="map-stage">
      <div ref="mapEl" class="map-canvas" aria-label="景区示意地图"></div>
      <div class="map-layer-switch" role="group" aria-label="底图切换">
        <button type="button" :class="{ active: layer === 'vec' }" @click="setLayer('vec')">矢量</button>
        <button type="button" :class="{ active: layer === 'img' }" @click="setLayer('img')">影像</button>
      </div>
      <button type="button" class="map-color-toggle" :class="{ active: showColor }" :aria-pressed="showColor" @click="showColor = !showColor">
        <i :style="{ background: colorHex }"></i>景区颜色
      </button>
      <button type="button" class="map-narrate-toggle" :class="{ active: narrateOn }" :aria-pressed="narrateOn" @click="toggleNarrate">
        {{ narrateOn ? "关闭讲解设置" : "开启讲解设置" }}
      </button>
      <div class="map-geo-tip" v-if="narrateOn && geo.error">{{ geo.error }}</div>
      <SpotNarrationCard
        v-if="narration.activeSpot.value"
        :spot="narration.activeSpot.value"
        :text="narrationText"
        :progress="narrationProgress"
        :loading="narrationLoading"
        :playing="narrationIsPlaying"
        :degraded="narrationDegraded"
        @replay="playNarration(narration.activeSpot.value)"
        @stop="stopNarration"
        @close="closeNarration"
      />
      <div class="map-legend" aria-hidden="true">
        <span v-for="zone in zoneList" :key="zone.key"><i :style="{ background: zone.color }"></i>{{ zone.label }}</span>
      </div>
    </div>

    <div class="map-narrate-bar" v-if="narrateOn">
      <button type="button" @click="toggleWalk">{{ walking ? "停止巡游" : "模拟巡游" }}</button>
      <span>模式：{{ modeLabel }}</span>
    </div>
    <p v-if="narrateOn" class="map-note">自动讲解使用演示景点坐标，仅在模拟定位时触发；真实定位下可选择景点，再点击“让导游讲讲”。</p>

    <div class="map-live">
      <div class="map-live-item">
        <span class="k">天气信息</span>
        <span class="v">{{ weather ? `${weather.icon} ${weather.temp}°C ${weather.description}` : '正在获取…' }}</span>
      </div>
      <div class="map-live-item">
        <span class="k">景区颜色提示</span>
        <span class="v"><i class="live-dot" :style="{ background: colorHex }"></i>{{ colorText }}</span>
      </div>
      <div class="map-live-item">
        <span class="k">在园人数 · 演示</span>
        <span class="v">{{ crowd.total.toLocaleString() }} 人</span>
      </div>
      <div class="map-live-item">
        <span class="k">舒适度</span>
        <span class="v" :class="{ warn: crowd.comfort === '较拥挤' }">{{ crowd.comfort }}</span>
      </div>
    </div>

    <div class="map-bars">
      <div v-for="zone in crowd.zones" :key="zone.key" class="map-bar">
        <div class="map-bar-top"><span>{{ zone.label }}</span><b>{{ zone.occ.toLocaleString() }} 人 · {{ zone.pct }}%</b></div>
        <div class="map-bar-track"><div class="map-bar-fill" :class="{ warn: zone.pct >= 80 }" :style="{ width: zone.pct + '%' }"></div></div>
      </div>
    </div>

    <h4 class="map-subtitle">路线规划</h4>
    <select v-model="routeId" class="map-select" aria-label="选择游览路线">
      <option v-for="item in routes" :key="item.id" :value="item.id">{{ item.title }} · {{ item.duration_label }}</option>
    </select>
    <div v-if="activeRoute" class="map-route-steps">
      <template v-for="(spot, index) in activeRoute.spots" :key="index">
        <span class="step">{{ cleanName(spot) }}</span>
        <span v-if="index < activeRoute.spots.length - 1" class="arrow">→</span>
      </template>
    </div>

    <h4 class="map-subtitle">已确认行程</h4>
    <div v-if="confirmedStops.length" class="confirmed-itinerary">
      <div v-for="(stop, index) in confirmedStops" :key="stop.stop_id" class="confirmed-itinerary-row">
        <button type="button" :disabled="!stop.coordinate_evidence_id" @click="focusConfirmedStop(stop)">
          <strong>{{ index + 1 }}. {{ stop.name }}</strong><small>{{ stop.coordinate_evidence_id ? '已发布坐标依据' : '暂无可验证坐标' }} · {{ progressLabel(stop.stop_id) }}</small>
        </button>
        <button v-if="progressLabel(stop.stop_id) === '当前'" type="button" :disabled="busy || !stop.qa_attraction_id" @click="emit('ask', { query: `请介绍${stop.name}`, attractionId: stop.qa_attraction_id })">介绍当前点</button>
      </div>
    </div>
    <p v-else class="map-note">打开已保存的 V2 游览后，这里会显示带坐标依据的停留点。</p>

    <h4 class="map-subtitle">分区景点</h4>
    <div class="tool-chips" aria-label="按分区筛选">
      <button v-for="zone in zoneFilters" :key="zone.key" type="button" :class="{ active: zoneFilter === zone.key }" :aria-pressed="zoneFilter === zone.key" @click="zoneFilter = zone.key">{{ zone.label }}</button>
    </div>
    <div class="map-poi-list">
      <button v-for="spot in filteredSpots" :key="spot.name" type="button" class="map-poi" :class="{ active: spot.name === selectedName }" @click="focusSpot(spot.name)">
        <span class="emoji">{{ spot.emoji }}</span>
        <span class="info"><strong>{{ spot.name }}</strong><small>{{ spot.desc }}</small></span>
      </button>
    </div>

    <button type="button" class="tool-primary" :disabled="busy" @click="askGuide">{{ askLabel }} <GuideIcon name="mic" /></button>
    <p class="map-note">客流为演示数据，景点坐标包含演示值；天气信息可能不可用或有延迟，请以当地官方信息为准。</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import GuideIcon from "../../components/GuideIcon.vue";
import SpotNarrationCard from "../../components/SpotNarrationCard.vue";
import { scenicSpots, PRESET_ROUTES } from "../../constants/touristCatalog";
import { LINGSHAN_CENTER, MAP_ZONES, SPOT_COORDS, ROUTE_ALIASES } from "../../constants/mapSpots";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { useGeolocation, demoNarrationPosition, canFinishNarration } from "../../composables/useGeolocation";
import { useNarration } from "../../composables/useNarration";
import { speechText } from "../../constants/narration";
import { fetchSpotNarration } from "../../api/narration";
import { fetchItineraryCatalog } from "../../api/itinerary";
import { useTourSessionsStore } from "../../stores/tourSessions";
import { useInteractionStore } from "../../stores/interaction";
import { createLatestRequest } from "../../utils/latestRequest";

const props = defineProps({
  busy: { type: Boolean, default: false },
  weather: { type: Object, default: null },
  scenicColor: { type: Object, default: null },
  colorLabel: { type: String, default: "" },
  speechRate: { type: Number, default: 1 },
});
const emit = defineEmits(["ask"]);
const tourStore = useTourSessionsStore();
const interactionStore = useInteractionStore();
const itineraryCatalog = ref({ items: [] });
const confirmedStops = computed(() => {
  const snapshot = tourStore.current?.snapshot;
  if (snapshot?.schema_version !== 2) return [];
  const entries = new Map((itineraryCatalog.value.items || []).map(entry => [entry.spot_code, entry]));
  return (snapshot.stops || []).filter(stop => stop.kind === "visit").map(stop => {
    const entry = entries.get(stop.spot_code);
    const current = entry && entry.entry_id === stop.source_entry_id && entry.published_revision_id === stop.source_revision_id;
    const qaAttraction = current ? interactionStore.bootstrap.attractions.find(item => item.attraction_code === stop.spot_code) : null;
    return { ...stop, latitude: current ? entry.latitude : null, longitude: current ? entry.longitude : null,
      coordinate_evidence_id: current ? entry.coordinate_evidence_id : null, qa_attraction_id: qaAttraction?.id || null };
  });
});

const colorHex = computed(() => props.scenicColor?.hex || "#2D5A4B");
const colorText = computed(() => props.colorLabel || props.scenicColor?.label || "暂无数据");

const spots = scenicSpots
  .filter((spot) => SPOT_COORDS[spot.name])
  .map((spot) => ({ ...spot, ...SPOT_COORDS[spot.name] }));
const spotByName = Object.fromEntries(spots.map((spot) => [spot.name, spot]));

const zoneList = Object.entries(MAP_ZONES).map(([key, zone]) => ({ key, ...zone }));
const zoneFilters = [{ key: "all", label: "全部" }, ...zoneList];

function resolveSpot(text) {
  const bare = String(text || "").replace(/[（(].*?[）)]/g, "").trim();
  if (!bare) return null;
  if (spotByName[bare]) return spotByName[bare];
  const contained = spots.find((spot) => bare.includes(spot.name));
  if (contained) return contained;
  return ROUTE_ALIASES[bare] ? spotByName[ROUTE_ALIASES[bare]] || null : null;
}

/* ---------- 地图 ---------- */
const mapEl = ref(null);
const layer = ref("vec");
const showColor = ref(false);
let map = null;
let vecLayer = null;
let imgLayer = null;
let colorOverlay = null;
let routeLine = null;
let itineraryLayer = null;
let resizeObserver = null;
let meMarker = null;
const markers = {};

// 景区颜色覆盖范围：由景点演示坐标外扩生成（非测绘边界，仅用于风险着色示意）
const scenicBounds = L.latLngBounds(spots.map((spot) => [spot.lat, spot.lng])).pad(0.14);

function renderColorOverlay() {
  if (!map) return;
  if (colorOverlay) { map.removeLayer(colorOverlay); colorOverlay = null; }
  if (!showColor.value) return;
  colorOverlay = L.rectangle(scenicBounds, {
    color: colorHex.value,
    weight: 1.5,
    opacity: 0.7,
    fillColor: colorHex.value,
    fillOpacity: 0.24,
    dashArray: "5 6",
  }).addTo(map);
  colorOverlay.bindTooltip(colorText.value, { className: "map-tip", sticky: true });
}

watch([showColor, colorHex, colorText], renderColorOverlay);

function initMap() {
  map = L.map(mapEl.value, { zoomControl: true, attributionControl: false }).setView(LINGSHAN_CENTER, 15);
  vecLayer = L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}", { subdomains: ["1", "2", "3", "4"], maxZoom: 18 });
  imgLayer = L.tileLayer("https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}", { subdomains: ["1", "2", "3", "4"], maxZoom: 18 });
  vecLayer.addTo(map);
  L.control.attribution({ prefix: false })
    .addAttribution("底图 © 高德地图（测试用途）")
    .addAttribution("天气数据 © 和风天气")
    .addTo(map);

  spots.forEach((spot) => {
    const icon = L.divIcon({
      className: "",
      html: `<div class="map-pin zone-${spot.zone}"><span>${spot.emoji}</span></div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 24],
    });
    const marker = L.marker([spot.lat, spot.lng], { icon, riseOnHover: true }).addTo(map);
    marker.bindTooltip(spot.name, { className: "map-tip", direction: "top", offset: [0, -18] });
    marker.on("click", () => { selectedName.value = spot.name; });
    markers[spot.name] = marker;
  });
  itineraryLayer = L.layerGroup().addTo(map);
  renderConfirmedItinerary();

  resizeObserver = new ResizeObserver(() => map.invalidateSize());
  resizeObserver.observe(mapEl.value);
  setTimeout(() => map.invalidateSize(), 350);
  renderColorOverlay();

  watch(() => geo.position.value, (pos) => {
    if (!map) return;
    if (!pos) {
      if (meMarker) { map.removeLayer(meMarker); meMarker = null; }
      return;
    }
    const latlng = [pos.lat, pos.lng];
    if (!meMarker) {
      meMarker = L.circleMarker(latlng, { radius: 7, color: "#fff", weight: 2, fillColor: "#2f7d7d", fillOpacity: 0.95 }).addTo(map);
    } else {
      meMarker.setLatLng(latlng);
    }
  });
}

function renderConfirmedItinerary() {
  if (!map || !itineraryLayer) return;
  itineraryLayer.clearLayers();
  confirmedStops.value.forEach((stop, index) => {
    if (!stop.coordinate_evidence_id || !Number.isFinite(stop.latitude) || !Number.isFinite(stop.longitude)) return;
    const tooltip = document.createElement("span");
    tooltip.textContent = `${index + 1}. ${stop.name}`;
    L.marker([stop.latitude, stop.longitude], { icon: L.divIcon({ className: "", html: `<div class="itinerary-pin">${index + 1}</div>`, iconSize: [26, 26], iconAnchor: [13, 13] }), zIndexOffset: 900 })
      .bindTooltip(tooltip, { className: "map-tip" }).addTo(itineraryLayer);
  });
}
function progressLabel(id) { return ({ current: "当前", completed: "已完成", skipped: "已跳过", pending: "待游览" }[tourStore.progress?.status_by_stop?.[id]] || "待游览"); }
function focusConfirmedStop(stop) { if (map && stop.coordinate_evidence_id) map.flyTo([stop.latitude, stop.longitude], Math.max(map.getZoom(), 16), { duration: 0.6 }); }
watch(confirmedStops, renderConfirmedItinerary, { deep: true });

function setLayer(next) {
  layer.value = next;
  if (!map) return;
  if (next === "img") { map.removeLayer(vecLayer); imgLayer.addTo(map); }
  else { map.removeLayer(imgLayer); vecLayer.addTo(map); }
}

function focusSpot(name) {
  const spot = spotByName[name];
  if (!spot || !map) return;
  selectedName.value = name;
  map.flyTo([spot.lat, spot.lng], Math.max(map.getZoom(), 16), { duration: 0.6 });
  markers[name]?.openTooltip();
}

/* ---------- 客流（热度模型演示） ---------- */
function hourFactor() {
  const hour = new Date().getHours();
  if (hour < 8) return 0.12;
  if (hour < 10) return 0.5;
  if (hour < 12) return 0.82;
  if (hour < 14) return 1.0;
  if (hour < 16) return 0.86;
  if (hour < 18) return 0.5;
  return 0.16;
}

const crowd = computed(() => {
  const factor = hourFactor();
  const zones = zoneList.map((zone) => {
    const occ = Math.round(spots.filter((spot) => spot.zone === zone.key).reduce((sum, spot) => sum + spot.heat * 5.2 * factor, 0));
    return { key: zone.key, label: zone.label, occ, pct: Math.min(100, Math.round((occ / zone.capacity) * 100)) };
  });
  const total = zones.reduce((sum, zone) => sum + zone.occ, 0);
  const maxRatio = Math.max(...zones.map((zone) => zone.occ / (MAP_ZONES[zone.key]?.capacity || 1)));
  const comfort = maxRatio > 0.82 ? "较拥挤" : maxRatio > 0.6 ? "舒适" : "宽松";
  return { zones, total, comfort };
});

/* ---------- 路线 ---------- */
const routes = PRESET_ROUTES;
const routeId = ref(routes[0].id);
const activeRoute = computed(() => routes.find((item) => item.id === routeId.value) || null);

function cleanName(text) {
  return String(text).replace(/[（(].*?[）)]/g, "");
}

watch([routeId, () => map], () => {
  if (!map || !activeRoute.value) return;
  const points = activeRoute.value.spots.map(resolveSpot).filter(Boolean).map((spot) => [spot.lat, spot.lng]);
  if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
  if (points.length > 1) {
    routeLine = L.polyline(points, { color: "#c49b4c", weight: 4, opacity: 0.9, dashArray: "2 8", lineCap: "round" }).addTo(map);
    map.fitBounds(routeLine.getBounds(), { padding: [40, 40], maxZoom: 16 });
  }
});

/* ---------- 分区景点 ---------- */
const zoneFilter = ref("all");
const selectedName = ref("");
const filteredSpots = computed(() =>
  spots
    .filter((spot) => zoneFilter.value === "all" || spot.zone === zoneFilter.value)
    .slice()
    .sort((a, b) => b.heat - a.heat),
);

/* ---------- 自动讲解（讲解机） ---------- */
const audio = useAudioPlayer();
const geo = useGeolocation();
const narrateOn = ref(false);
const narrationText = ref("");
const narrationProgress = ref(0);
const narrationLoading = ref(false);
const narrationDegraded = ref(false);
const walking = ref(false);
let narrateTimer = null;
let mapToolActive = false;
let activeNarrationSession = null;

const narration = useNarration({
  getPosition: () => demoNarrationPosition(geo.mode.value, geo.position.value),
  getSpots: () => spots,
  isBusy: () => props.busy || audio.isPlaying.value,
  onTrigger: (spot) => playNarration(spot, { automatic: true }),
  // 排队超时只允许中断自己的地图讲解，不能停止聊天或其他媒体源。
  onInterrupt: () => {
    if (!props.busy && activeNarrationSession && audio.activePlayback.value?.id === activeNarrationSession.id) {
      audio.stop(activeNarrationSession.id, "pending-timeout");
      return true;
    }
    return false;
  },
});

const modeLabel = computed(() => {
  const map = { real: "真实定位", sim: "模拟巡游", denied: "定位无权限", unsupported: "定位不可用", out_of_area: "不在景区范围", low_accuracy: "精度不足", idle: "未定位" };
  return map[geo.mode.value] || geo.mode.value;
});

const narrationRequests = createLatestRequest();
const narrationIsPlaying = computed(() => Boolean(
  activeNarrationSession
  && audio.activePlayback.value?.id === activeNarrationSession.id
  && audio.isPlaying.value,
));

function claimNarrationSession() {
  let session;
  session = audio.claimPlayback("map-narration", () => {
    if (activeNarrationSession?.id !== session.id) return;
    activeNarrationSession = null;
    narrationLoading.value = false;
    narrationProgress.value = 0;
    narration.status.value = "idle";
  });
  activeNarrationSession = session;
  return session;
}

watch(() => props.busy, (busy) => {
  if (busy) {
    narrationRequests.cancel();
    narrationLoading.value = false;
    if (activeNarrationSession && audio.activePlayback.value?.id === activeNarrationSession.id) {
      audio.stop(activeNarrationSession.id, "visitor-input");
    }
  }
});

async function playNarration(spot, { automatic = false } = {}) {
  if (!spot || props.busy || !mapToolActive) return;
  const request = narrationRequests.begin();
  const playbackSession = claimNarrationSession();
  narrationLoading.value = true;
  narrationDegraded.value = false;
  narrationText.value = spot.desc || "";
  narrationProgress.value = 0;

  let data = null;
  try {
    data = await fetchSpotNarration(spot.name, undefined, { signal: request.signal });
  } catch {
    data = null;
  }

  if (!request.isCurrent() || activeNarrationSession?.id !== playbackSession.id) return;
  if (automatic && (geo.mode.value !== "sim" || !canFinishNarration(geo.mode.value, geo.position.value, spot))) {
    stopNarration();
    throw new Error("自动讲解位置已失效");
  }
  narrationLoading.value = false;
  if (!audio.isCurrentPlaybackSession(playbackSession.id)) return;
  if (data && data.available) {
    // 卡片展示完整讲解词；浏览器朗读兜底只念开头，避免长时间占用播放通道
    narrationText.value = data.text || spot.desc || "";
    narrationDegraded.value = !data.base64_audio;
    audio.enqueue(
      data.base64_audio,
      data.duration_ms || 60000,
      () => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) finishNarration(playbackSession.id); },
      speechText(data.text),
      (p) => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) narrationProgress.value = p; },
      { allowBrowserSpeech: true, sessionId: playbackSession.id, rate: props.speechRate },
    );
  } else {
    narrationDegraded.value = true;
    const fallback = spot.desc || `${spot.name}`;
    narrationText.value = fallback;
    audio.enqueue(
      "",
      Math.max(fallback.length * 180, 1200),
      () => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) finishNarration(playbackSession.id); },
      speechText(fallback),
      (p) => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) narrationProgress.value = p; },
      { allowBrowserSpeech: true, sessionId: playbackSession.id, rate: props.speechRate },
    );
  }
}

function finishNarration(sessionId) {
  if (!audio.isCurrentPlaybackSession(sessionId) || activeNarrationSession?.id !== sessionId) return;
  activeNarrationSession = null;
  narrationProgress.value = 1;
  narration.status.value = "idle";
  audio.stop(sessionId, "completed");
  narration.drainPending();
}

function stopNarration() {
  narrationRequests.cancel();
  narrationLoading.value = false;
  const session = activeNarrationSession;
  activeNarrationSession = null;
  if (session) audio.stop(session.id);
  narrationProgress.value = 0;
  narration.status.value = "idle";
}

function closeNarration() {
  stopNarration();
  narration.activeSpot.value = null;
}

async function toggleNarrate() {
  narrateOn.value = !narrateOn.value;
  if (narrateOn.value) {
    // 用户手势内同步解锁 AudioContext，保证后续自动播放不被拦截
    await audio.unlock();
    // KeepAlive deactivation or a second toggle may happen while unlock awaits.
    if (mapToolActive && narrateOn.value) geo.start();
  } else {
    geo.stop();
    closeNarration();
    narration.reset();
    walking.value = false;
  }
}

function toggleWalk() {
  if (walking.value) { geo.stopWalk(); walking.value = false; return; }
  const path = activeRoute.value ? activeRoute.value.spots.map(resolveSpot).filter(Boolean) : spots;
  geo.startWalk(path);
  walking.value = true;
}

/* ---------- 交给数字人导游 ---------- */
const askLabel = computed(() => (selectedName.value ? `让导游讲讲${selectedName.value}` : "让导游带我走这条路线"));

function askGuide() {
  if (selectedName.value) {
    emit("ask", { query: `请介绍${selectedName.value}，并根据已发布资料给出游览建议`, attraction: selectedName.value });
    return;
  }
  const route = activeRoute.value;
  if (!route) return;
  emit("ask", { query: `请介绍${route.title}，沿途经过${route.spots.map(cleanName).join("、")}，并给出游览建议` });
}

function startNarrationTimer() {
  if (narrateTimer !== null) return;
  narrateTimer = setInterval(() => {
    if (!mapToolActive || !narrateOn.value) return;
    narration.update();
    narration.drainPending();
  }, 900);
}

function stopNarrationTimer() {
  if (narrateTimer === null) return;
  clearInterval(narrateTimer);
  narrateTimer = null;
}

function activateMapTool() {
  if (mapToolActive) return;
  mapToolActive = true;
  startNarrationTimer();
  nextTick(() => map?.invalidateSize());
}

function deactivateMapTool() {
  if (!mapToolActive && narrateTimer === null) return;
  mapToolActive = false;
  stopNarrationTimer();
  narrationRequests.cancel();
  narrationLoading.value = false;
  const session = activeNarrationSession;
  activeNarrationSession = null;
  if (session) audio.stop(session.id, "map-hidden");
  narrateOn.value = false;
  geo.stopWalk();
  geo.stop();
  walking.value = false;
  narration.reset();
}

onMounted(() => {
  if (!tourStore.current && tourStore.currentId) tourStore.open(tourStore.currentId);
  fetchItineraryCatalog().then(data => { itineraryCatalog.value = data; }).catch(() => {});
  nextTick(initMap);
  activateMapTool();
});
onActivated(activateMapTool);
onDeactivated(deactivateMapTool);

onBeforeUnmount(() => {
  deactivateMapTool();
  if (resizeObserver) resizeObserver.disconnect();
  if (map) { map.remove(); map = null; }
});
</script>

<style scoped>
.map-tool { display: flex; flex-direction: column; }
.map-stage { position: relative; height: 300px; border-radius: 10px; overflow: hidden; border: 1px solid var(--guide-line, #e3e8df); margin-bottom: 12px; background: #e7e4dc; }
.map-canvas { position: absolute; inset: 0; }
.map-layer-switch { position: absolute; top: 8px; right: 8px; z-index: 400; display: flex; overflow: hidden; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.94); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); }
.map-layer-switch button { min-height: 32px; padding: 4px 12px; border: 0; background: transparent; font-size: 12px; color: #6b7a72; }
.map-layer-switch button + button { border-left: 1px solid rgba(45, 90, 75, 0.14); }
.map-layer-switch button.active { background: #2d5a4b; color: #f3f7f4; font-weight: 600; }
.map-legend { position: absolute; left: 8px; bottom: 8px; z-index: 400; display: flex; flex-wrap: wrap; gap: 4px 10px; max-width: 70%; padding: 5px 9px; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.14); background: rgba(255, 255, 255, 0.92); font-size: 11px; color: #6b7a72; }
.map-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 4px; }
.map-color-toggle { position: absolute; top: 8px; left: 8px; z-index: 400; display: inline-flex; align-items: center; gap: 6px; min-height: 32px; padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.94); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); font-size: 12px; color: #6b7a72; }
.map-color-toggle i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.16); }
.map-color-toggle.active { background: #2d5a4b; border-color: #2d5a4b; color: #f3f7f4; font-weight: 600; }

.map-live { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }
.map-live-item { padding: 8px 9px; border-radius: 8px; border: 1px solid rgba(45, 90, 75, 0.1); background: #f7f9f3; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.map-live-item .k { font-size: 11px; color: #6b7a72; white-space: nowrap; }
.map-live-item .v { font-size: 13px; font-weight: 600; color: #2c3a33; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.map-live-item .v.warn { color: #b4552d; }
.map-live-item .live-dot { display: inline-block; width: 9px; height: 9px; margin-right: 5px; border-radius: 50%; vertical-align: middle; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.14); }

.map-bars { display: flex; flex-direction: column; gap: 7px; margin-bottom: 14px; }
.map-bar { font-size: 12px; }
.map-bar-top { display: flex; justify-content: space-between; color: #6b7a72; margin-bottom: 3px; }
.map-bar-top b { color: #2c3a33; }
.map-bar-track { height: 6px; border-radius: 999px; background: #eaf0eb; overflow: hidden; }
.map-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #4d7565, #2d5a4b); }
.map-bar-fill.warn { background: linear-gradient(90deg, #d99a4e, #b4552d); }

.map-subtitle { margin: 4px 0 8px; font-size: 13px; font-weight: 600; color: #2c3a33; }
.map-select { width: 100%; padding: 9px 10px; border: 1px solid rgba(45, 90, 75, 0.18); border-radius: 8px; background: #fff; color: #2c3a33; font-size: 13px; margin-bottom: 8px; }
.map-route-steps { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; font-size: 12px; color: #2c3a33; margin-bottom: 14px; line-height: 1.9; }
.map-route-steps .arrow { color: #94a39c; font-size: 11px; }
.confirmed-itinerary { display: grid; gap: 6px; margin-bottom: 14px; }
.confirmed-itinerary-row { display: flex; align-items: center; gap: 6px; padding: 7px 8px; border: 1px solid rgba(45, 90, 75, .12); border-radius: 8px; background: #f7f9f3; }
.confirmed-itinerary-row button:first-child { display: grid; flex: 1; min-width: 0; gap: 2px; padding: 0; border: 0; background: transparent; text-align: left; color: #2c3a33; }
.confirmed-itinerary-row strong { font-size: 12px; }
.confirmed-itinerary-row small { font-size: 10px; color: #7e8c82; }
.confirmed-itinerary-row button:last-child:not(:first-child) { padding: 5px 8px; border: 1px solid #cbd9ce; border-radius: 7px; background: white; color: #315b48; font-size: 11px; }

.map-poi-list { display: flex; flex-direction: column; gap: 6px; max-height: 220px; overflow-y: auto; margin-bottom: 14px; scrollbar-width: thin; }
.map-poi { display: flex; gap: 9px; align-items: flex-start; text-align: left; padding: 8px 9px; border: 1px solid rgba(45, 90, 75, 0.08); border-radius: 8px; background: #f7f9f3; }
.map-poi:hover { border-color: #2d5a4b; background: #eaf0eb; }
.map-poi.active { border-color: #c49b4c; background: #f5ecd8; }
.map-poi .emoji { font-size: 17px; line-height: 1.3; }
.map-poi .info { min-width: 0; display: flex; flex-direction: column; }
.map-poi .info strong { font-size: 13px; color: #2c3a33; }
.map-poi .info small { font-size: 11px; color: #94a39c; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }

.map-note { margin-top: 10px; font-size: 11px; line-height: 1.7; color: #94a39c; }

.map-narrate-toggle { position: absolute; top: 48px; left: 8px; z-index: 400; min-height: 32px; padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.94); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); font-size: 12px; color: #6b7a72; }
.map-narrate-toggle.active { background: #c49b4c; border-color: #c49b4c; color: #fff; font-weight: 600; }
.map-geo-tip { position: absolute; top: 84px; left: 8px; z-index: 400; max-width: 60%; padding: 4px 9px; border-radius: 6px; background: rgba(180, 85, 45, 0.92); color: #fff; font-size: 11px; }
.map-narrate-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 12px; color: #6b7a72; }
.map-narrate-bar button { min-height: 28px; padding: 3px 12px; border-radius: 7px; border: 1px solid #2d5a4b; background: #fff; color: #2d5a4b; font-size: 12px; }
</style>

<style>
/* Leaflet 自定义标记（非 scoped，标记由 Leaflet 注入 DOM） */
.map-pin { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50% 50% 50% 2px; transform: rotate(-45deg); background: #2d5a4b; border: 2px solid #fff; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3); font-size: 12px; }
.map-pin span { transform: rotate(45deg); line-height: 1; }
.map-pin.zone-houshan { background: #7a5230; }
.map-pin.zone-huqu { background: #2f7d7d; }
.map-pin.zone-guangchang { background: #8b6d2b; }
.itinerary-pin { display: grid; place-items: center; width: 26px; height: 26px; border: 2px solid #fff; border-radius: 50%; background: #b45f35; color: white; font-size: 12px; font-weight: 700; box-shadow: 0 1px 5px #0005; }
.leaflet-tooltip.map-tip { font-size: 11.5px; padding: 3px 7px; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.14); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); }
</style>
