import { computed, ref, shallowRef } from "vue";
import { fetchDisplayAssets } from "../api/admin";
import { API_BASE_URL } from "../api/http";

const DEFAULT_BG_CSS = "var(--lingshan-scenic-bg)";
const DEFAULT_WELCOME = "欢迎来到灵山胜境，愿您在此感受千年佛韵，尽享山水之美。";

const cachedAssetUrl = shallowRef(null);
const cachedWelcomeText = shallowRef(null);
let fetchPromise = null;

function resolveAssetUrl(assetUrl) {
  if (!assetUrl) return "";
  if (/^https?:\/\//i.test(assetUrl)) return assetUrl;
  return new URL(assetUrl, `${API_BASE_URL}/`).href;
}

async function ensureAssets() {
  if (cachedAssetUrl.value !== null) {
    return;
  }
  if (fetchPromise) {
    await fetchPromise;
    return;
  }
  fetchPromise = (async () => {
    try {
      const assets = await fetchDisplayAssets();
      const bgUrl = assets?.tourist_background?.asset_url || "";
      cachedAssetUrl.value = bgUrl ? resolveAssetUrl(bgUrl) : "";
      cachedWelcomeText.value = assets?.welcome_text || DEFAULT_WELCOME;
    } catch {
      if (cachedAssetUrl.value === null) {
        cachedAssetUrl.value = "";
        cachedWelcomeText.value = DEFAULT_WELCOME;
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
}

export function useScenicBackground() {
  const loading = ref(false);

  const scenicBgUrl = computed(() => {
    const url = cachedAssetUrl.value;
    if (url === null) return DEFAULT_BG_CSS;
    if (url === "") return DEFAULT_BG_CSS;
    return `url(${url})`;
  });

  const welcomeText = computed(() => {
    return cachedWelcomeText.value || DEFAULT_WELCOME;
  });

  async function refresh() {
    cachedAssetUrl.value = null;
    cachedWelcomeText.value = null;
    loading.value = true;
    try {
      await ensureAssets();
    } finally {
      loading.value = false;
    }
  }

  if (cachedAssetUrl.value === null) {
    ensureAssets();
  }

  return {
    scenicBgUrl,
    welcomeText,
    loading,
    refresh,
    ensureAssets,
  };
}
