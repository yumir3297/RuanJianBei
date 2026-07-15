import { computed, onBeforeUnmount, ref } from "vue";

const OWM_API_KEY = "5017890a67e8f42c8b5a550503ffa5a1";

const LINGSHAN_LAT = 31.4285;
const LINGSHAN_LON = 120.0998;
const POLL_INTERVAL_MS = 10 * 60 * 1000;

const WEATHER_ICONS = {
  "01d": "\u2600\uFE0F",
  "01n": "\uD83C\uDF19",
  "02d": "\u26C5",
  "02n": "\uD83C\uDF24\uFE0F",
  "03d": "\uD83C\uDF25\uFE0F",
  "03n": "\uD83C\uDF25\uFE0F",
  "04d": "\u2601\uFE0F",
  "04n": "\u2601\uFE0F",
  "09d": "\uD83C\uDF27\uFE0F",
  "09n": "\uD83C\uDF27\uFE0F",
  "10d": "\uD83C\uDF26\uFE0F",
  "10n": "\uD83C\uDF27\uFE0F",
  "11d": "\u26C8\uFE0F",
  "11n": "\u26C8\uFE0F",
  "13d": "\uD83C\uDF28\uFE0F",
  "13n": "\uD83C\uDF28\uFE0F",
  "50d": "\uD83C\uDF2B\uFE0F",
  "50n": "\uD83C\uDF2B\uFE0F",
};

function buildWeatherUrl(lat, lon, apiKey) {
  return `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${apiKey}&units=metric&lang=zh_cn`;
}

async function fetchWeatherData(lat, lon, apiKey) {
  const url = buildWeatherUrl(lat, lon, apiKey);
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`OpenWeatherMap HTTP ${resp.status}`);
  }
  return resp.json();
}

export function useWeather() {
  const weather = ref(null);
  const loading = ref(false);
  const error = ref("");
  let pollTimer = null;

  function normalizeWeather(raw) {
    if (!raw || typeof raw !== "object") return null;
    const iconCode = raw.weather?.[0]?.icon || "01d";
    return {
      icon: WEATHER_ICONS[iconCode] || "\u2600\uFE0F",
      temp: Math.round(raw.main?.temp),
      feelsLike: Math.round(raw.main?.feels_like),
      description: raw.weather?.[0]?.description || "",
      humidity: raw.main?.humidity,
      windSpeed: raw.wind?.speed,
      cityName: raw.name || "\u7075\u5c71\u80dc\u5883",
    };
  }

  async function refresh() {
    if (!OWM_API_KEY) {
      error.value = "";
      weather.value = null;
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      const raw = await fetchWeatherData(LINGSHAN_LAT, LINGSHAN_LON, OWM_API_KEY);
      weather.value = normalizeWeather(raw);
    } catch (e) {
      error.value = e.message || "\u5929\u6c14\u6570\u636e\u83b7\u53d6\u5931\u8d25";
      weather.value = null;
    } finally {
      loading.value = false;
    }
  }

  const displayText = computed(() => {
    if (!weather.value) return null;
    const w = weather.value;
    return `${w.icon}\u00A0${w.temp}\u00B0C\u00A0${w.description}`;
  });

  const displayDetail = computed(() => {
    if (!weather.value) return null;
    const w = weather.value;
    const parts = [];
    parts.push(`\u4f53\u611f\u00A0${w.feelsLike}\u00B0C`);
    if (w.humidity != null) parts.push(`\u6e7f\u5ea6\u00A0${w.humidity}%`);
    if (w.windSpeed != null) parts.push(`\u98ce\u901f\u00A0${w.windSpeed}m/s`);
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
    loading,
    error,
    displayText,
    displayDetail,
    refresh,
    startPolling,
    stopPolling,
  };
}
