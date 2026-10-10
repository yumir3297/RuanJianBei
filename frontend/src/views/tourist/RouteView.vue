<template>
  <div class="guide-tool-content">
    <template v-if="!selectedRoute">
      <p class="tool-description">按时间与兴趣挑选路线，让导游陪你出发。</p>
      <div class="tool-chips" aria-label="路线分类"><button v-for="item in categories" :key="item" type="button" :class="{ active: category === item }" :aria-pressed="category === item" @click="category = item">{{ item }}</button></div>
      <div class="tool-chips tool-chips--secondary" aria-label="游览偏好"><span class="tool-filter-label">偏好</span><button v-for="option in preferenceOptions" :key="option.value" type="button" :class="{ active: preferences.includes(option.value) }" :aria-pressed="preferences.includes(option.value)" @click="togglePreference(option.value)">{{ option.label }}</button></div>
      <p class="tool-data-note" role="status">{{ loading ? '正在获取推荐，先显示景区预设路线。' : offline ? '推荐服务暂不可用，以下为离线预设路线。' : '结合游览偏好与可用天气信息推荐。' }}</p>
      <div class="route-list" :aria-busy="loading"><button v-for="item in routes" :key="item.id" type="button" class="route-choice" @click="selectedRoute = item"><span class="route-choice-top"><strong>{{ item.title }}</strong><span>{{ item.duration_label }}</span></span><span class="route-tags"><small v-for="tag in item.tags" :key="tag">{{ tag }}</small></span><span class="route-preview">{{ item.spots.slice(0, 4).join(' → ') }}{{ item.spots.length > 4 ? ' …' : '' }}</span></button></div>
    </template>
    <template v-else>
      <button type="button" class="tool-back" @click="selectedRoute = null"><GuideIcon name="back" /> 返回路线列表</button>
      <h4 class="route-detail-title">{{ selectedRoute.title }}</h4><p class="tool-description">{{ selectedRoute.duration_label }}</p>
      <ol class="route-stops"><li v-for="(spot, index) in selectedRoute.spots" :key="index">{{ spot }}</li></ol>
      <details class="route-detail"><summary>沿途讲解与特色体验</summary><p>{{ selectedRoute.guide }}</p><p>{{ selectedRoute.features }}</p></details>
      <button type="button" class="tool-primary" :disabled="busy" @click="$emit('ask', { query: '请介绍' + selectedRoute.title + '，沿途经过' + selectedRoute.spots.join('、') + '，并给出游览建议', routeId: selectedRoute.routeId })">让导游带我出发 <GuideIcon name="route" /></button>
    </template>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
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
const loading = ref(false);
const offline = ref(false);
let requestId = 0;
const routes = computed(() => recommendations.value.length ? recommendations.value : PRESET_ROUTES.filter(item => item.category === category.value));
function togglePreference(value) { preferences.value = preferences.value.includes(value) ? preferences.value.filter(item => item !== value) : [...preferences.value, value]; }
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
onBeforeUnmount(() => { requestId += 1; });
</script>
