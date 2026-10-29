<template>
  <div class="guide-tool-content">
    <template v-if="!selectedRoute">
      <p class="tool-description">按时间与兴趣挑选路线，让导游陪你出发。</p>
      <div class="tool-chips" aria-label="路线分类"><button v-for="item in categories" :key="item" type="button" :class="{ active: category === item }" :aria-pressed="category === item" @click="category = item">{{ item }}</button></div>
      <div class="tool-chips tool-chips--secondary" aria-label="游览偏好"><span class="tool-filter-label">偏好</span><button v-for="option in preferenceOptions" :key="option.value" type="button" :class="{ active: preferences.includes(option.value) }" :aria-pressed="preferences.includes(option.value)" @click="togglePreference(option.value)">{{ option.label }}</button></div>
      <section class="tour-session-panel" aria-labelledby="my-tours-title">
        <div class="tour-session-heading"><div><h4 id="my-tours-title">我的游览</h4><p>保存后，可在同一浏览器继续查看。</p></div><button type="button" class="tour-session-secondary" :disabled="sessionLoading" @click="loadMyTours">刷新</button></div>
        <button type="button" class="tour-session-primary" :disabled="sessionSaving" @click="createBlankTour">新建空白游览</button>
        <p v-if="tourStore.error" class="tour-session-error" role="alert">{{ tourStore.error }}</p>
        <p v-if="sessionSaving" class="tour-session-status" role="status">正在保存…</p>
        <p v-else-if="tourStore.saveState === 'saved'" class="tour-session-status" role="status">已保存到此浏览器</p>
        <p v-if="tourStore.current" class="tour-session-current"><strong>当前游览：</strong>{{ tourStore.current.title }} · 第 {{ tourStore.current.version }} 版</p>
        <ol v-if="tourStore.current?.snapshot?.stops?.length" class="tour-session-stops"><li v-for="(stop, index) in tourStore.current.snapshot.stops" :key="`${stop.name}-${index}`">{{ stop.name }}</li></ol>
        <p v-else-if="tourStore.current" class="tour-session-empty">这条游览还没有保存景点。</p>
        <ul v-if="tourStore.items.length" class="tour-session-list">
          <li v-for="item in tourStore.items" :key="item.id">
            <button type="button" class="tour-session-open" @click="openTour(item.id)"><strong>{{ item.title }}</strong><small>{{ item.snapshot?.stops?.length || 0 }} 个景点 · 第 {{ item.version }} 版</small></button>
            <button type="button" class="tour-session-secondary" @click="deleteTour(item)">移入回收站</button>
          </li>
        </ul>
        <p v-else class="tour-session-empty">还没有保存的游览。</p>
        <button type="button" class="tour-session-link" @click="toggleTrash">{{ showTrash ? '收起回收站' : '查看回收站' }}</button>
        <ul v-if="showTrash && tourStore.trash.length" class="tour-session-list tour-session-list--trash">
          <li v-for="item in tourStore.trash" :key="item.id"><span><strong>{{ item.title }}</strong><small>可恢复至 {{ formatExpiry(item.deleted_until) }}</small></span><button type="button" class="tour-session-secondary" @click="recoverTour(item.id)">恢复</button><button type="button" class="tour-session-danger" @click="purgeTour(item)">永久删除</button></li>
        </ul>
        <p v-else-if="showTrash" class="tour-session-empty">回收站为空。</p>
      </section>
      <p class="tool-data-note" role="status">{{ loading ? '正在获取推荐，先显示景区预设路线。' : offline ? '推荐服务暂不可用，以下为离线预设路线。' : '结合游览偏好与可用天气信息推荐。' }}</p>
      <div class="route-list" :aria-busy="loading"><button v-for="item in routes" :key="item.id" type="button" class="route-choice" @click="selectedRoute = item"><span class="route-choice-top"><strong>{{ item.title }}</strong><span>{{ item.duration_label }}</span></span><span class="route-tags"><small v-for="tag in item.tags" :key="tag">{{ tag }}</small></span><span class="route-preview">{{ item.spots.slice(0, 4).join(' → ') }}{{ item.spots.length > 4 ? ' …' : '' }}</span></button></div>
    </template>
    <template v-else>
      <button type="button" class="tool-back" @click="selectedRoute = null"><GuideIcon name="back" /> 返回路线列表</button>
      <h4 class="route-detail-title">{{ selectedRoute.title }}</h4><p class="tool-description">{{ selectedRoute.duration_label }}</p>
      <ol class="route-stops"><li v-for="(spot, index) in selectedRoute.spots" :key="index">{{ spot }}</li></ol>
      <details class="route-detail"><summary>沿途讲解与特色体验</summary><p>{{ selectedRoute.guide }}</p><p>{{ selectedRoute.features }}</p></details>
      <button type="button" class="tour-session-primary" :disabled="sessionSaving" @click="saveSelectedRoute">{{ sessionSaving ? '正在保存…' : '保存为我的游览' }}</button>
      <button v-if="tourStore.current" type="button" class="tour-session-secondary" :disabled="sessionSaving" @click="updateCurrentTour">更新当前游览</button>
      <p v-if="tourStore.error" class="tour-session-error" role="alert">{{ tourStore.error }}</p>
      <button type="button" class="tool-primary" :disabled="busy" @click="$emit('ask', { query: '请介绍' + selectedRoute.title + '，沿途经过' + selectedRoute.spots.join('、') + '，并给出游览建议', routeId: selectedRoute.routeId })">让导游带我出发 <GuideIcon name="route" /></button>
    </template>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useTourSessionsStore } from "../../stores/tourSessions";
import GuideIcon from "../../components/GuideIcon.vue";
import { PRESET_ROUTES } from "../../constants/touristCatalog";
import { fetchRecommendations } from "../../api/recommend";
import { getSessionId } from "../../stores/chat";
const props = defineProps({ busy: { type: Boolean, default: false }, weather: { type: Object, default: null } });
defineEmits(["ask"]);
const categories = ["官方推荐", "半日精选", "主题体验", "特色路线"];
const category = ref("官方推荐");
const preferences = ref([]);
const preferenceOptions = [{ value: "avoid_heat", label: "避暑" }, { value: "less_walking", label: "少走路" }, { value: "family", label: "亲子 / 老人" }, { value: "rain", label: "雨天" }];
const recommendations = ref([]);
const selectedRoute = ref(null);
const tourStore = useTourSessionsStore();
const sessionLoading = ref(false);
const sessionSaving = ref(false);
const showTrash = ref(false);
const loading = ref(false);
const offline = ref(false);
let requestId = 0;
const routes = computed(() => recommendations.value.length ? recommendations.value : PRESET_ROUTES.filter(item => item.category === category.value));
function togglePreference(value) { preferences.value = preferences.value.includes(value) ? preferences.value.filter(item => item !== value) : [...preferences.value, value]; }
async function loadMyTours() { sessionLoading.value = true; try { await tourStore.loadList(); } finally { sessionLoading.value = false; } }
async function createBlankTour() { sessionSaving.value = true; try { await tourStore.create({ title: "我的游览", snapshot: { constraints: {}, stops: [], source: "manual", source_references: [] } }); } finally { sessionSaving.value = false; } }
async function saveSelectedRoute() {
  if (!selectedRoute.value) return;
  const route = selectedRoute.value;
  const snapshot = routeSnapshot(route);
  sessionSaving.value = true;
  try {
    await tourStore.create({ title: route.title || "我的游览", snapshot });
  } finally { sessionSaving.value = false; }
}
function routeSnapshot(route) {
  const routeId = route.routeId || route.id;
  const hours = Number.parseInt(String(route.duration_label || "").match(/\d+/)?.[0] || "2", 10);
  return {
    constraints: { available_minutes: Math.max(1, Math.min(720, hours * 60)), interests: [], companions: [], required_spots: [], excluded_spots: [], walking_preference: null },
    stops: (route.spots || []).slice(0, 50).map(name => ({ name, spot_id: null, resolved: false })),
    source: route.routeId ? "recommendation" : "preset",
    source_references: routeId ? [{ source_type: route.routeId ? "recommendation" : "preset_route", source_id: String(routeId), label: route.title || "" }] : [],
  };
}
async function updateCurrentTour() {
  if (!selectedRoute.value || !tourStore.current) return;
  sessionSaving.value = true;
  try {
    await tourStore.save(routeSnapshot(selectedRoute.value));
  } finally { sessionSaving.value = false; }
}
async function openTour(id) { await tourStore.open(id); }
async function deleteTour(item) { if (window.confirm(`将“${item.title}”移入 30 天回收站？`)) { try { await tourStore.remove(item.id); } catch { tourStore.error = "移入回收站失败，请刷新后重试。"; } } }
async function toggleTrash() { showTrash.value = !showTrash.value; if (showTrash.value) { try { await tourStore.loadTrash(); } catch { tourStore.error = "暂时无法读取回收站，请稍后重试。"; } } }
async function recoverTour(id) { try { await tourStore.restoreDeleted(id); } catch { tourStore.error = "恢复失败，请刷新后重试。"; } }
async function purgeTour(item) { if (window.confirm(`永久删除“${item.title}”？删除后无法恢复。`)) { try { await tourStore.purge(item.id); } catch { tourStore.error = "永久删除失败，请刷新后重试。"; } } }
function formatExpiry(value) { if (!value) return "期限未知"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "期限未知" : date.toLocaleDateString(); }
function categoryPreferences(value) {
  if (value.includes("半日")) return { interests: ["轻松", "半日"], hours: 3 };
  if (value.includes("主题")) return { interests: ["摄影", "文化"], hours: 4 };
  if (value.includes("特色")) return { interests: ["自然", "文化"], hours: 4 };
  return { interests: ["历史", "文化"], hours: 6 };
}
async function loadRecommendations() {
  const token = ++requestId;
  const preference = categoryPreferences(category.value);
  loading.value = true; offline.value = false; recommendations.value = []; selectedRoute.value = null;
  try {
    const data = await fetchRecommendations({ session_id: getSessionId(), interests: preference.interests, available_hours: preference.hours, audience_type: "general", avoid_crowded: category.value.includes("特色"), comfort_preferences: preferences.value, weather_condition: props.weather?.description || null, temperature_c: Number.isFinite(props.weather?.temp) ? props.weather.temp : null });
    if (token !== requestId) return;
    recommendations.value = (Array.isArray(data?.routes) ? data.routes : []).map(item => ({
      id: "recommended-" + item.route_id, routeId: item.route_id, title: String(item.title || "游览路线").replace(/^推荐[：:]/, ""),
      duration_label: item.duration_label || (item.duration_hours || 2) + "小时",
      tags: [...(item.comfort_tags || []), "景区资料"],
      spots: String(item.route_plan || "").split(/\s*(?:→|->|—|－)\s*/).map(spot => spot.trim()).filter(Boolean),
      guide: [item.reason, ...(item.guide_points || [])].filter(Boolean).join("\n"), features: (item.experiences || []).join("；"),
    })).filter(item => item.spots.length);
    offline.value = !recommendations.value.length;
  } catch { if (token === requestId) offline.value = true; }
  finally { if (token === requestId) loading.value = false; }
}
watch([category, preferences, () => props.weather], loadRecommendations, { immediate: true });
onMounted(loadMyTours);
onBeforeUnmount(() => { requestId += 1; });
</script>
