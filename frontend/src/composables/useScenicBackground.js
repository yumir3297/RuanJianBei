import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { fetchPublicDisplayAssets, resolveDisplayAssetUrl } from "../api/display";

// A scenic photograph remains visible before configuration loads or if an upload fails.
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
    { id: "broadcast", label: "广播找人", description: "寻人广播·游客中心", number: "0510-85688631", enabled: true },
    { id: "complaint", label: "景区投诉", description: "服务投诉建议", number: "400-168-0303转5", enabled: true },
    { id: "emergency", label: "医疗急救", description: "紧急医疗救助", number: "0510-85688120", enabled: true },
  ],
};

const cachedAssetUrl = shallowRef(null);
const cachedWelcomeText = shallowRef(null);
const cachedTouristSettings = shallowRef(null);
let fetchPromise = null;
const ASSETS_VERSION_KEY = "a5-display-assets-version";

function loadBackgroundImage(url) {
  return new Promise((resolve) => {
    const image = new Image();
    const timeout = window.setTimeout(() => finish(false), 15000);
    function finish(loaded) {
      window.clearTimeout(timeout);
      image.onload = null;
      image.onerror = null;
      resolve(loaded);
    }
    image.onload = () => finish(true);
    image.onerror = () => finish(false);
    image.src = url;
  });
}

async function ensureAssets(force = false) {
  if (!force && cachedAssetUrl.value !== null) {
    return;
  }
  if (fetchPromise) {
    await fetchPromise;
    return;
  }
  fetchPromise = (async () => {
    try {
      const assets = await fetchPublicDisplayAssets();
      const bgUrl = resolveDisplayAssetUrl(assets?.tourist_background?.asset_url);
      if (!bgUrl) cachedAssetUrl.value = "";
      else if (bgUrl !== cachedAssetUrl.value) {
        cachedAssetUrl.value = await loadBackgroundImage(bgUrl) ? bgUrl : "";
      }
      cachedWelcomeText.value = assets?.welcome_text || DEFAULT_WELCOME;
      cachedTouristSettings.value = {
        ...DEFAULT_TOURIST_SETTINGS,
        ...(assets?.tourist_settings || {}),
        modules: assets?.tourist_settings?.modules || DEFAULT_TOURIST_SETTINGS.modules,
        quick_questions: assets?.tourist_settings?.quick_questions || DEFAULT_TOURIST_SETTINGS.quick_questions,
        hotlines: assets?.tourist_settings?.hotlines || DEFAULT_TOURIST_SETTINGS.hotlines,
      };
    } catch {
      if (cachedAssetUrl.value === null) {
        cachedAssetUrl.value = "";
        cachedWelcomeText.value = DEFAULT_WELCOME;
        cachedTouristSettings.value = DEFAULT_TOURIST_SETTINGS;
      }
    } finally {
      fetchPromise = null;
    }
  })();
  await fetchPromise;
}

export function invalidateScenicBackground() {
  cachedAssetUrl.value = null;
  cachedWelcomeText.value = null;
  cachedTouristSettings.value = null;
  try { window.localStorage.setItem(ASSETS_VERSION_KEY, String(Date.now())); } catch {}
}

export function useScenicBackground() {
  const loading = ref(false);

  const scenicBgUrl = computed(() => {
    const url = cachedAssetUrl.value;
    if (url === null) return DEFAULT_BG_CSS;
    if (url === "") return DEFAULT_BG_CSS;
    return `url(${JSON.stringify(url)})`;
  });
  const hasScenicBackground = computed(() => Boolean(cachedAssetUrl.value));

  const welcomeText = computed(() => {
    return cachedWelcomeText.value || DEFAULT_WELCOME;
  });

  async function refresh() {
    loading.value = true;
    try {
      await ensureAssets(true);
    } finally {
      loading.value = false;
    }
  }

  if (cachedAssetUrl.value === null) {
    ensureAssets();
  }

  function handleAssetsChange(event) {
    if (event.key === ASSETS_VERSION_KEY) refresh();
  }
  function handleVisibilityChange() {
    if (!document.hidden) refresh();
  }
  onMounted(() => {
    window.addEventListener("storage", handleAssetsChange);
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("storage", handleAssetsChange);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  return {
    scenicBgUrl,
    hasScenicBackground,
    welcomeText,
    touristSettings: computed(() => cachedTouristSettings.value || DEFAULT_TOURIST_SETTINGS),
    loading,
    refresh,
    ensureAssets,
  };
}
