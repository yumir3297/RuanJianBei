<template>
  <div class="map-workspace" @keydown.esc="handleMapEscape">
    <div class="map-stage">
      <div ref="mapEl" class="map-canvas" aria-label="景区实时地图"></div>
    </div>
    <div class="map-search">
      <GuideIcon name="map" />
      <label class="sr-only" for="map-search">搜索景点</label>
      <input id="map-search" v-model="search" type="search" placeholder="搜索景点，如灵山大佛" autocomplete="off" @input="panel = 'spots'" @focus="panel = 'spots'" />
      <button v-if="search" type="button" aria-label="清除搜索" @click="search = ''">×</button>
    </div>
    <span v-if="!locationMessage && !narrateOn" class="map-data-note">{{ spots.length }}处地图参考 · {{ pendingSpots.length }}处待核验</span>
    <div class="map-position-actions">
      <button type="button" aria-label="回到我的位置" :disabled="locating" @click="locateMe">{{ locating ? '…' : '◎' }}</button>
      <button type="button" aria-label="查看整个景区" @click="fitScenic">⌖</button>
    </div>
    <p v-if="locationMessage || narrateOn" class="map-status" role="status">{{ locationMessage || `${modeLabel} · 自动讲解已开启` }}</p>

    <section v-if="panel" id="map-task-panel" class="map-task-panel" :aria-label="panelTitle">
      <header><h4>{{ panelTitle }}</h4><button type="button" aria-label="收起面板" @click="closePanel">×</button></header>
      <div class="map-panel-content">
        <template v-if="panel === 'spots'">
          <div class="map-zone-filters" aria-label="分区筛选"><button v-for="zone in zoneFilters" :key="zone.key" type="button" :aria-pressed="zoneFilter === zone.key" @click="zoneFilter = zone.key">{{ zone.label }}</button></div>
          <p class="map-help">已取得参考坐标的景点可在地图查看；待核验项目仅提供讲解。</p>
          <div class="map-results"><button v-for="spot in filteredSpots" :key="spot.name" type="button" @click="focusSpot(spot.name)"><span class="map-result-icon" v-html="markerSymbol(spot.type, spot.name)"></span><span><strong>{{ spot.name }}</strong><small>{{ spot.coordinateStatus === 'reference' ? '地图参考点' : '点位待核验 · 仅讲解' }} · {{ spot.desc }}</small></span><span class="map-result-arrow" aria-hidden="true">›</span></button></div>
          <p v-if="!filteredSpots.length" class="map-help">没有找到景点，请换个关键词或分区。</p>
        </template>
        <template v-else-if="panel === 'routes'">
          <p class="map-help">按已核对景点规划高德步行道路；显示的是路线预览，不含实时导航播报。</p>
          <label class="map-field">选择路线<select v-model="routeId"><option v-for="item in routes" :key="item.id" :value="item.id">{{ item.title }} · {{ item.duration_label }}</option></select></label>
          <ol v-if="activeRoute" class="map-stops"><li v-for="(spot,index) in activeRoute.spots" :key="index">{{ cleanName(spot) }}</li></ol>
          <p v-if="routeStatus" class="map-route-status" role="status">{{ routeStatus }}</p>
          <p v-if="routeSummary" class="map-route-summary">{{ routeSummary }}</p>
          <button type="button" class="map-primary" :disabled="routeLoading || !routeReady" @click="previewRoute">{{ routeLoading ? '正在规划步行道路…' : '规划真实步行路线' }}</button>
          <button type="button" class="map-secondary" :disabled="busy" @click="askGuide">请导游讲解路线</button>
        </template>
        <template v-else-if="panel === 'layers'">
          <p class="map-help">数字表示聚合的景点数量，点击即可放大展开；不表示客流。</p>
          <div class="map-option-row"><span>地图底图</span><div class="map-segment"><button type="button" :aria-pressed="layer === 'vec'" @click="setLayer('vec')">地图</button><button type="button" :aria-pressed="layer === 'img'" @click="setLayer('img')">卫星</button></div></div>
          <div class="map-option-row"><span>景区颜色覆盖<small>{{ colorText }}</small></span><button type="button" :aria-pressed="showColor" @click="showColor = !showColor">{{ showColor ? '关闭' : '开启' }}</button></div>
          <div class="map-option-row"><span>到点自动讲解<small>需要定位权限；模拟模式会明确提示</small></span><button type="button" :aria-pressed="narrateOn" @click="toggleNarrate">{{ narrateOn ? '关闭' : '开启' }}</button></div>
          <div v-if="narrateOn" class="map-option-row"><span>{{ modeLabel }}</span><button type="button" @click="toggleWalk">{{ walking ? '停止巡游' : '模拟巡游' }}</button></div>
          <div class="map-zones"><span v-for="zone in zoneList" :key="zone.key"><i :style="{background:zone.color}"></i>{{ zone.label }}</span></div>
        </template>
        <template v-else>
          <dl class="map-facts"><div><dt>天气</dt><dd>{{ weather ? `${weather.temp}°C ${weather.description}` : '天气暂不可用' }}</dd></div><div><dt>景区颜色</dt><dd>{{ colorText }}</dd></div><div><dt>演示客流</dt><dd>{{ crowd.total.toLocaleString() }} 人 · {{ crowd.comfort }}</dd></div></dl>
          <p class="map-help">客流与舒适度为演示数据。地图显示{{ spots.length }}处有来源的参考位置；{{ pendingSpots.length }}处待核验景点仅列清单，6处其它景区项目不在此落点。参考点不等于入口或可通行路径。</p>
        </template>
      </div>
    </section>
    <SpotNarrationCard v-else-if="narration.activeSpot.value" :spot="narration.activeSpot.value" :text="narrationText" :progress="narrationProgress" :loading="narrationLoading" :playing="narrationIsPlaying" :degraded="narrationDegraded" @replay="playNarration(narration.activeSpot.value)" @stop="stopNarration" @close="closeNarration" />
    <section v-else-if="selectedSpot" class="map-place-card" aria-label="选中景点"><div><strong>{{ selectedSpot.name }}</strong><small class="map-place-note">{{ selectedSpot.coordinateNote }}<a v-if="selectedSpot.sourceUrl" :href="selectedSpot.sourceUrl" target="_blank" rel="noopener noreferrer">查看来源</a></small><p>{{ selectedSpot.desc }}</p></div><button type="button" class="map-primary" :disabled="busy" @click="playNarration(selectedSpot)">听讲解</button><button type="button" aria-label="取消选中景点" @click="selectedName = ''">×</button></section>
    <nav class="map-task-nav" aria-label="地图任务"><button v-for="item in panelItems" :key="item.id" :id="`map-${item.id}-trigger`" type="button" :aria-expanded="panel === item.id" aria-controls="map-task-panel" @click="panel = panel === item.id ? null : item.id"><GuideIcon :name="item.icon" /><span>{{ item.label }}</span></button></nav>
  </div>
</template>
<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import GuideIcon from "../../components/GuideIcon.vue";
import SpotNarrationCard from "../../components/SpotNarrationCard.vue";
import { scenicSpots, PRESET_ROUTES } from "../../constants/touristCatalog";
import { LINGSHAN_CENTER, MAP_ZONES, ROUTE_ALIASES, SPOT_COORDS } from "../../constants/mapSpots";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { useGeolocation } from "../../composables/useGeolocation";
import { useNarration } from "../../composables/useNarration";
import { wgs84ToGcj02, speechText } from "../../constants/narration";
import { fetchSpotNarration } from "../../api/narration";
import { fetchWalkingRoute } from "../../api/mapRoutes";
import { createLatestRequest } from "../../utils/latestRequest";
import { MAP_COORDINATE_AUDIT, MAP_ROUTE_STOPS } from "../../constants/mapCoordinateAudit";
import { groupMapPoints, layoutMapLabels, markerSymbol } from "../../utils/mapMarkers";

const props = defineProps({
  busy: { type: Boolean, default: false },
  weather: { type: Object, default: null },
  scenicColor: { type: Object, default: null },
  colorLabel: { type: String, default: "" },
  speechRate: { type: Number, default: 1 },
});
const emit = defineEmits(["ask"]);
const panel = ref(null);
const search = ref("");
const locating = ref(false);
const locationMessage = ref("");
let locationRequest = 0;
const panelItems = [
  { id: "spots", label: "景点", icon: "landmark" },
  { id: "routes", label: "路线", icon: "route" },
  { id: "layers", label: "图层", icon: "settings" },
  { id: "info", label: "园区", icon: "book" },
];
const panelTitle = computed(() => panelItems.find(item => item.id === panel.value)?.label || "园区信息");
function handleMapEscape(event) {
  if (!panel.value) return;
  event.preventDefault();
  event.stopPropagation();
  closePanel();
}
function closePanel() {
  const previous = panel.value;
  panel.value = null;
  document.activeElement?.blur();
  nextTick(() => document.getElementById(`map-${previous}-trigger`)?.focus({ preventScroll: true }));
}
function fitScenic() {
  map?.fitBounds(scenicBounds, { padding: [36, 90], maxZoom: 16 });
}
async function previewRoute() {
  if (!map || !routeReady.value || routeLoading.value) return;
  routeController?.abort();
  routeController = new AbortController();
  routeLoading.value = true;
  routeStatus.value = "正在按景区道路规划，请稍候…";
  if (routeSummary.value && locationMessage.value === routeSummary.value) locationMessage.value = "";
  routeSummary.value = "";
  locationMessage.value = "";
  if (routeLine) { map?.removeLayer(routeLine); routeLine = null; }
  const request = routeRequestId;
  try {
    const result = await fetchWalkingRoute(resolvedRouteStops.value.map(spot => spot.sourcePoiId), { signal: routeController.signal });
    if (request !== routeRequestId || !mapToolActive) return;
    if (!result.available) {
      routeStatus.value = result.reason === "not_configured" ? "步行路线服务尚未配置。" : "暂时没有取得道路路线，请稍后重试。";
      return;
    }
    routeLine = L.polyline(result.coordinates, { color: "#bd6d18", weight: 6, opacity: 0.96, lineCap: "round", lineJoin: "round" }).addTo(map);
    map.fitBounds(routeLine.getBounds(), { padding: [56, 72], maxZoom: 17 });
    const distance = result.distance_m >= 1000 ? `${(result.distance_m / 1000).toFixed(1)} 公里` : `${result.distance_m} 米`;
    const duration = Math.max(1, Math.round(result.duration_s / 60));
    routeSummary.value = `${distance} · 步行约 ${duration} 分钟 · 高德道路路径`;
    locationMessage.value = routeSummary.value;
    routeStatus.value = "";
    selectedName.value = "";
    panel.value = null;
  } catch (error) {
    if (error.name !== "AbortError" && request === routeRequestId) routeStatus.value = "路线请求失败，请检查网络后重试。";
  } finally {
    if (request === routeRequestId) routeLoading.value = false;
  }
}
function locateMe() {
  if (!navigator.geolocation) { locationMessage.value = "当前浏览器无法定位，仍可搜索景点。"; return; }
  const request = ++locationRequest;
  locating.value = true;
  locationMessage.value = "正在获取你的位置…";
  navigator.geolocation.getCurrentPosition(position => {
    if (request !== locationRequest || !mapToolActive || !map) return;
    locating.value = false;
    const fixed = wgs84ToGcj02(position.coords.latitude, position.coords.longitude);
    const latlng = [fixed.lat, fixed.lng];
    if (!myLocationMarker) myLocationMarker = L.circleMarker(latlng, { radius: 8, color: "#fff", fillColor: "#176de6", fillOpacity: 1, weight: 3 }).addTo(map);
    else myLocationMarker.setLatLng(latlng);
    map.flyTo(latlng, 16);
    locationMessage.value = position.coords.accuracy > 100 ? "定位精度较低，请核对周围环境。" : "已显示真实位置，可继续浏览景区。";
  }, error => {
    if (request !== locationRequest || !mapToolActive) return;
    locating.value = false;
    locationMessage.value = error.code === 1 ? "定位未获授权，仍可搜索景点和查看路线。" : "暂时无法定位，仍可手动浏览景区。";
  }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 });
}

const colorHex = computed(() => props.scenicColor?.hex || "#2D5A4B");
const colorText = computed(() => props.colorLabel || props.scenicColor?.label || "暂无数据");

const mapCatalog = [
  ...scenicSpots.map(spot => ({ ...spot, heat: SPOT_COORDS[spot.name]?.heat || 0, ...MAP_COORDINATE_AUDIT[spot.name] })),
  ...MAP_ROUTE_STOPS,
].filter(spot => spot.coordinateStatus !== "other-scenic");
const spots = mapCatalog.filter(spot => spot.coordinateStatus === "reference");
const pendingSpots = mapCatalog.filter(spot => spot.coordinateStatus === "pending");
const spotByName = Object.fromEntries(mapCatalog.map(spot => [spot.name, spot]));
const placedByName = Object.fromEntries(spots.map(spot => [spot.name, spot]));

const zoneList = Object.entries(MAP_ZONES).map(([key, zone]) => ({ key, ...zone }));
const zoneFilters = [{ key: "all", label: "全部" }, ...zoneList];

function resolveSpot(text) {
  const bare = String(text || "").replace(/[（(].*?[）)]/g, "").trim();
  if (!bare) return null;
  const aliased = ROUTE_ALIASES[bare] || bare;
  if (placedByName[aliased]) return placedByName[aliased];
  const contained = spots.find((spot) => aliased.includes(spot.name));
  if (contained) return contained;
  return null;
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
let resizeObserver = null;
let meMarker = null;
let myLocationMarker = null;
let markerLayer = null;
let selectedLabel = null;
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
    .addAttribution('点位参考 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>')
    .addTo(map);

  markerLayer = L.layerGroup().addTo(map);
  renderMarkers();
  map.on("zoomend moveend resize", renderMarkers);

  resizeObserver = new ResizeObserver(() => map.invalidateSize());
  resizeObserver.observe(mapEl.value);
  setTimeout(() => map.invalidateSize(), 350);
  renderColorOverlay();

  watch(() => geo.position.value, (pos) => {
    if (!map || !pos) return;
    const latlng = [pos.lat, pos.lng];
    if (!meMarker) {
      meMarker = L.circleMarker(latlng, { radius: 7, color: "#fff", weight: 2, fillColor: "#2f7d7d", fillOpacity: 0.95 }).addTo(map);
    } else {
      meMarker.setLatLng(latlng);
    }
  });
}

function renderMarkers() {
  if (!map || !markerLayer) return;
  markerLayer.clearLayers();
  if (!placedByName[selectedName.value] && selectedLabel) map.removeLayer(selectedLabel);
  Object.keys(markers).forEach(name => delete markers[name]);
  const projected = spots.map(spot => ({ ...spot, ...map.latLngToContainerPoint([spot.lat, spot.lng]) }));
  const groups = groupMapPoints(projected, map.getZoom() >= 18 ? 0 : 44, selectedName.value);
  const size = map.getSize();
  const labels = layoutMapLabels(groups, size.x, size.y, selectedName.value);
  for (const group of groups) {
    const spot = group[0];
    const selected = spot.name === selectedName.value;
    const cluster = group.length > 1 && !selected;
    const html = cluster
      ? `<span class="scenic-symbol scenic-cluster">${group.length}<small>处</small></span>`
      : `<span class="scenic-symbol">${markerSymbol(spot.type, spot.name)}</span>${selected && group.length > 1 ? `<span class="scenic-count">+${group.length - 1}</span>` : ""}`;
    const labelSide = labels.get(spot.name);
    const markerHtml = labelSide ? `${html}<span class="scenic-name name-${labelSide}">${spot.name.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}</span>` : html;
    const marker = L.marker([spot.lat, spot.lng], {
      icon: L.divIcon({ className: `scenic-marker${selected ? " is-selected" : ""}`, html: markerHtml, iconSize: [44,44], iconAnchor: [22,22] }),
      title: cluster ? `${group.length} 处景点，点击展开` : spot.name,
      alt: cluster ? `${group.length} 处景点` : spot.name,
      zIndexOffset: selected ? 1000 : cluster ? 100 : 0,
    }).addTo(markerLayer);
    const label = document.createElement("span");
    label.textContent = cluster ? `${group.length} 处景点 · 点击放大` : spot.name;
    if (selected) {
      if (!selectedLabel) selectedLabel = L.tooltip({ className: "scenic-label", permanent: true, direction: "top", offset: [0,-16] });
      selectedLabel.setLatLng([spot.lat, spot.lng]).setContent(label);
      if (!map.hasLayer(selectedLabel)) selectedLabel.addTo(map);
    }
    marker.on("click", () => {
      if (cluster) map.fitBounds(group.map(item => [item.lat,item.lng]), { padding: [65,100], maxZoom: Math.min(map.getZoom()+2,18) });
      else { selectedName.value = spot.name; panel.value = null; }
    });
    if (!cluster) markers[spot.name] = marker;
  }
}

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
  panel.value = null;
  document.activeElement?.blur();
  if (spot.coordinateStatus !== "reference") { locationMessage.value = `${name}点位待核验，仍可听讲解。`; return; }
  locationMessage.value = "";
  map.flyTo([spot.lat, spot.lng], Math.max(map.getZoom(), 16), { duration: 0.6 });
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
const resolvedRouteStops = computed(() => activeRoute.value?.spots.map(resolveSpot) || []);
const routeReady = computed(() => resolvedRouteStops.value.length >= 2 && resolvedRouteStops.value.every(spot => spot?.sourcePoiId));
const routeLoading = ref(false);
const routeStatus = ref("");
const routeSummary = ref("");
let routeController = null;
let routeRequestId = 0;

function cleanName(text) {
  return String(text).replace(/[（(].*?[）)]/g, "");
}

function clearRoute() {
  routeRequestId += 1;
  routeController?.abort();
  routeLoading.value = false;
  routeStatus.value = "";
  if (routeSummary.value && locationMessage.value === routeSummary.value) locationMessage.value = "";
  routeSummary.value = "";
  if (routeLine) { map?.removeLayer(routeLine); routeLine = null; }
}
watch(routeId, clearRoute);

/* ---------- 分区景点 ---------- */
const zoneFilter = ref("all");
const selectedName = ref("");
watch(selectedName, renderMarkers);
const selectedSpot = computed(() => spotByName[selectedName.value] || null);
const filteredSpots = computed(() =>
  mapCatalog
    .filter((spot) => zoneFilter.value === "all" || spot.zone === zoneFilter.value)
    .filter((spot) => !search.value.trim() || spot.name.includes(search.value.trim()) || spot.desc.includes(search.value.trim()))
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
  getPosition: () => geo.position.value,
  getSpots: () => spots,
  isBusy: () => props.busy || audio.isPlaying.value,
  onTrigger: (spot) => playNarration(spot),
  // 排队超时只允许中断自己的地图讲解，不能停止聊天或其他媒体源。
  onInterrupt: () => {
    if (activeNarrationSession && audio.activePlayback.value?.id === activeNarrationSession.id) {
      audio.stop(activeNarrationSession.id, "pending-timeout");
    }
  },
});

const modeLabel = computed(() => {
  const map = { real: "真实定位", sim: "模拟巡游", denied: "模拟（无权限）", unsupported: "模拟（不支持）", out_of_area: "模拟（不在景区）", low_accuracy: "精度不足", idle: "未定位" };
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

async function playNarration(spot) {
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
  narrationLoading.value = false;
  if (data && data.available) {
    // 卡片展示完整讲解词；浏览器朗读兜底只念开头，避免长时间占用播放通道
    narrationText.value = data.text || spot.desc || "";
    narrationDegraded.value = !data.base64_audio;
    audio.enqueue(
      data.base64_audio,
      data.duration_ms || 60000,
      () => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) finishNarration(); },
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
      () => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) finishNarration(); },
      speechText(fallback),
      (p) => { if (request.isCurrent() && activeNarrationSession?.id === playbackSession.id) narrationProgress.value = p; },
      { allowBrowserSpeech: true, sessionId: playbackSession.id, rate: props.speechRate },
    );
  }
}

function finishNarration() {
  narrationProgress.value = 1;
  narration.status.value = "idle";
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
  const routeSpots = activeRoute.value?.spots.map(resolveSpot);
  if (routeSpots?.some(spot => !spot)) { locationMessage.value = "该路线点位尚未完整核对，暂不模拟巡游。"; return; }
  const path = routeSpots || spots;
  geo.startWalk(path);
  walking.value = true;
}

/* ---------- 交给数字人导游 ---------- */
const askLabel = computed(() => (selectedName.value ? `让导游讲讲${selectedName.value}` : "让导游讲解这条路线"));

function askGuide() {
  if (selectedName.value && panel.value !== "routes") {
    emit("ask", { query: `请介绍${selectedName.value}，并结合当前客流与天气给出游览建议`, attraction: selectedName.value });
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
  routeRequestId += 1;
  routeController?.abort();
  routeLoading.value = false;
  routeStatus.value = "";
  locationRequest += 1;
  locating.value = false;
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

<style scoped src="../../assets/map-workspace.css"></style>

<style>
/* Leaflet creates these nodes outside Vue templates. */
.scenic-marker { display: grid !important; place-items: center; background: transparent; border: 0; }
.scenic-symbol { display: grid; place-items: center; width: 28px; height: 28px; border: 2px solid #fff; border-radius: 50%; background: #fff; color: #2a5947; box-shadow: 0 1px 6px #183c3a40; box-sizing: border-box; }
.scenic-symbol svg { width: 18px; height: 18px; }
.scenic-name { position: absolute; padding: 3px 8px; border-radius: 6px; color: #214c38; background: #fffffff0; white-space: nowrap; box-shadow: 0 1px 5px #173b2020; font: 600 12px/18px system-ui,sans-serif; }
.scenic-name.name-right { left: 41px; top: 10px; }
.scenic-name.name-left { right: 41px; top: 10px; }
.scenic-name.name-bottom { top: 43px; left: 50%; transform: translateX(-50%); }
.scenic-cluster small { font-size: 9px; }
.scenic-symbol.scenic-cluster { display: flex; gap: 1px; justify-content: center; }
.scenic-symbol.scenic-cluster { width: 32px; height: 32px; color: #fff; background: #346552; border: 3px solid #fff; font: 600 13px/1 system-ui,sans-serif; }
.scenic-marker.is-selected .scenic-symbol { width: 34px; height: 34px; background: #24563f; color: #fff; box-shadow: 0 0 0 3px #ffffffcc,0 3px 10px #183c3a66; }
.scenic-count { position: absolute; top: -2px; right: -2px; background: #fff; color: #24563f; border: 1px solid #c5d5c9; border-radius: 8px; padding: 1px 3px; font: 600 9px/1.4 system-ui,sans-serif; }
.scenic-marker:focus-visible { outline: 3px solid #24563f; border-radius: 50%; }
.leaflet-tooltip.scenic-label { padding: 5px 9px; background: #fffffff5; border: 0; color: #234838; border-radius: 7px; box-shadow: 0 2px 8px #16392e26; font: 600 12px/1.4 system-ui,sans-serif; }
</style>
