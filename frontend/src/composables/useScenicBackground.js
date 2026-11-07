import { computed, onBeforeUnmount, ref, watch } from "vue";
import { resolveDisplayAssetUrl } from "../api/display.js";
import { createBackgroundAssetLoader } from "../utils/backgroundAssetLoader.js";

const DEFAULT_BG_CSS = 'url("/assets/bg-scenic.png")';
const DEFAULT_WELCOME = "你好，我是你的数字人导游。可以向我了解景点、游览路线和景区服务。";
const DEFAULT_TOURIST_SETTINGS = {
  brand_name: "数字人导览",
  landing_tagline: "走进风景，听见这里的故事。",
  footer_text: "",
  guide_name: "",
  guide_subtitle: "数字人导游",
  primary_color: "#dce7d7",
  background_tint: "#18352b",
  background_tint_opacity: 0.72,
  edge_fade_width: 36,
  edge_blur: 20,
  font_style: "serif",
  modules: [
    { id: "explore", title: "景点探索", enabled: true, order: 10 },
    { id: "map", title: "实时地图", enabled: true, order: 20 },
    { id: "route", title: "智能路线", enabled: true, order: 30 },
    { id: "quiz", title: "文化故事", enabled: true, order: 40 },
  ],
  quick_questions: [
    "有哪些值得看的景点？",
    "推荐一条游览路线",
    "这里有什么代表性的故事？",
    "附近适合拍照的景点有哪些？",
  ],
  hotlines: [
    { id: "broadcast", label: "广播找人", description: "寻人广播·游客中心", number: "0510-85688631", enabled: false },
    { id: "complaint", label: "景区投诉", description: "服务投诉建议", number: "400-168-0303转5", enabled: false },
    { id: "emergency", label: "医疗急救", description: "紧急医疗救助", number: "0510-85688120", enabled: false },
  ],
};

function normalizeTouristSettings(settings) {
  return {
    ...DEFAULT_TOURIST_SETTINGS,
    ...(settings || {}),
    modules: settings?.modules || DEFAULT_TOURIST_SETTINGS.modules,
    quick_questions: settings?.quick_questions || DEFAULT_TOURIST_SETTINGS.quick_questions,
    hotlines: settings?.hotlines || DEFAULT_TOURIST_SETTINGS.hotlines,
  };
}

export function invalidateScenicBackground() {
  // Legacy same-page API retained. Cross-origin updates use visitor-config polling.
}

export function useScenicBackground({ display, refresh: refreshConfig } = {}) {
  const cachedAssetUrl = ref(null);
  const cachedWelcomeText = ref(null);
  const cachedTouristSettings = ref(null);
  const loading = ref(false);
  const backgroundLoader = createBackgroundAssetLoader({
    resolveUrl: resolveDisplayAssetUrl,
    onChange({ url, loading: isLoading }) {
      cachedAssetUrl.value = url;
      loading.value = isLoading;
    },
  });

  const scenicBgUrl = computed(() => {
    if (!cachedAssetUrl.value) return DEFAULT_BG_CSS;
    return `url(${JSON.stringify(cachedAssetUrl.value)})`;
  });
  const hasScenicBackground = computed(() => Boolean(cachedAssetUrl.value));
  const welcomeText = computed(() => cachedWelcomeText.value || DEFAULT_WELCOME);

  async function applyDisplay(assets) {
    if (!assets) return;
    cachedWelcomeText.value = assets.welcome_text || DEFAULT_WELCOME;
    cachedTouristSettings.value = normalizeTouristSettings(assets.tourist_settings);
    await backgroundLoader.load(assets.tourist_background?.asset_url);
  }

  const stopDisplayWatch = watch(display || (() => null), applyDisplay, { immediate: true });
  onBeforeUnmount(() => {
    stopDisplayWatch();
    backgroundLoader.dispose();
  });

  return {
    scenicBgUrl,
    hasScenicBackground,
    welcomeText,
    touristSettings: computed(() => cachedTouristSettings.value || DEFAULT_TOURIST_SETTINGS),
    loading,
    refresh: () => refreshConfig?.(),
    ensureAssets: () => refreshConfig?.(),
  };
}
