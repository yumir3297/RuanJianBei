import { computed, onBeforeUnmount, ref } from "vue";

import { fetchCurrentWeather } from "../api/weather";

const LINGSHAN_LAT = 31.4285;
const LINGSHAN_LON = 120.0998;
const POLL_INTERVAL_MS = 10 * 60 * 1000;

// 预警等级排序，用于从多条预警中挑出最高级别色带
const SEVERITY_ORDER = { Extreme: 4, Severe: 3, Moderate: 2, Minor: 1, Unknown: 0 };

const CALM_COLOR = {
  code: "green",
  hex: "#2D5A4B",
  label: "\u6c14\u8c61\u6761\u4ef6\u5e73\u7a33",
  level: "calm",
  severity: "",
};

/**
 * 景区实时天气 + 景区风险颜色。
 *
 * 数据源：后端 `/api/weather/current`（聚合和风天气 QWeather），密钥只保存在服务端。
 * 返回值中的 `weather` 结构与旧版保持一致，`ChatView` / `RouteView` / `MapView` 无需改动签名。
 */
export function useWeather() {
  const weather = ref(null);
  const alert = ref(null);
  const air = ref(null);
  const available = ref(false);
  const reason = ref("");
  const statusText = ref("");
  const loading = ref(false);
  const error = ref("");
  let pollTimer = null;

  function normalizeWeather(raw) {
    if (!raw || typeof raw !== "object") return null;
    return {
      icon: raw.icon || "\uD83C\uDF24\uFE0F",
      temp: raw.temp,
      feelsLike: raw.feelsLike,
      description: raw.description || "",
      humidity: raw.humidity,
      windSpeed: raw.windSpeed,
      windDir: raw.windDir || "",
      windScale: raw.windScale || "",
      precip: raw.precip,
      vis: raw.vis,
      pressure: raw.pressure,
      cityName: raw.cityName || "\u7075\u5c71\u80dc\u5883",
      obsTime: raw.obsTime || null,
    };
  }

  async function refresh() {
    loading.value = true;
    error.value = "";
    try {
      const data = await fetchCurrentWeather({ lat: LINGSHAN_LAT, lon: LINGSHAN_LON });
      available.value = Boolean(data?.available);
      reason.value = data?.reason || "";
      weather.value = normalizeWeather(data?.weather);
      alert.value = data?.alert && data.alert.hasAlert ? data.alert : null;
      air.value = data?.air || null;
      statusText.value = available.value
        ? ""
        : data?.message || "\u5929\u6c14\u6570\u636e\u6682\u4e0d\u53ef\u7528";
    } catch (e) {
      available.value = false;
      reason.value = "network_error";
      weather.value = null;
      alert.value = null;
      air.value = null;
      statusText.value = "\u5929\u6c14\u670d\u52a1\u8fde\u63a5\u5931\u8d25";
      error.value = e?.message || "\u5929\u6c14\u6570\u636e\u83b7\u53d6\u5931\u8d25";
    } finally {
      loading.value = false;
    }
  }

  // 景区颜色：优先取最高等级气象预警色，其次空气质量等级色，最后平稳绿
  const scenicColor = computed(() => {
    const items = alert.value?.items || [];
    if (items.length) {
      const top = [...items].sort(
        (a, b) => (SEVERITY_ORDER[b?.severity] || 0) - (SEVERITY_ORDER[a?.severity] || 0),
      )[0];
      return {
        code: top?.colorCode || "",
        hex: top?.color || "#FF9800",
        label: top?.eventType ? `${top.eventType}\u9884\u8b66` : "\u6c14\u8c61\u9884\u8b66",
        level: "alert",
        severity: top?.severity || "",
      };
    }
    if (air.value?.color) {
      return {
        code: "",
        hex: air.value.color,
        label: air.value.category
          ? `\u7a7a\u6c14\u8d28\u91cf ${air.value.category}`
          : "\u7a7a\u6c14\u8d28\u91cf",
        level: "air",
        severity: air.value.category || "",
      };
    }
    if (!available.value) {
      return { code: "", hex: "#9E9E9E", label: "\u6682\u65e0\u6570\u636e", level: "unknown", severity: "" };
    }
    return { ...CALM_COLOR };
  });

  const colorLabel = computed(() => scenicColor.value?.label || "");

  const displayText = computed(() => {
    if (!weather.value) return null;
    const w = weather.value;
    return `${w.icon}\u00A0${w.temp}\u00B0C\u00A0${w.description}`;
  });

  const displayDetail = computed(() => {
    if (!weather.value) return null;
    const w = weather.value;
    const parts = [];
    if (w.feelsLike != null) parts.push(`\u4f53\u611f\u00A0${w.feelsLike}\u00B0C`);
    if (w.humidity != null) parts.push(`\u6e7f\u5ea6\u00A0${w.humidity}%`);
    if (w.windSpeed != null) parts.push(`\u98ce\u901f\u00A0${w.windSpeed}km/h`);
    return parts.join("\u00A0\u00A0");
  });

  function startPolling() {
    refresh();
    pollTimer = setInterval(refresh, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    weather,
    alert,
    air,
    available,
    reason,
    statusText,
    scenicColor,
    colorLabel,
    loading,
    error,
    displayText,
    displayDetail,
    refresh,
    startPolling,
    stopPolling,
  };
}
