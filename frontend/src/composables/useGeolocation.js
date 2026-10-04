import { ref } from "vue";
import { LINGSHAN_CENTER } from "../constants/mapSpots";
import {
  haversineMeters,
  wgs84ToGcj02,
  OUT_OF_AREA_M,
  LOW_ACCURACY_M,
  SIM_TICK_MS,
  SIM_WALK_SPEED_MPS,
  SIM_WALK_ON_ARRIVE,
} from "../constants/narration";

const CENTER = { lat: LINGSHAN_CENTER[0], lng: LINGSHAN_CENTER[1] };

/**
 * 定位层：真实浏览器定位（WGS84 自动纠偏为 GCJ-02）+ 模拟巡游兜底。
 * mode: idle | real | sim | denied | unsupported | out_of_area | low_accuracy
 */
export function useGeolocation() {
  const position = ref(null);
  const mode = ref("idle");
  const error = ref("");
  const enabled = ref(false);
  const accuracyPoor = ref(false);

  let watchId = null;
  let walkTimer = null;
  let walkPath = [];
  let walkIndex = 0;
  let walkSegmentProgress = 0;

  function setPosition(lat, lng, accuracy = 0) {
    position.value = { lat, lng, accuracy, ts: Date.now() };
  }

  function setSimulated(lat, lng) {
    setPosition(lat, lng, 5);
  }

  function evaluate(raw) {
    const fixed = wgs84ToGcj02(raw.lat, raw.lng);
    const accuracy = Number(raw.accuracy) || 0;
    setPosition(fixed.lat, fixed.lng, accuracy);

    if (haversineMeters(fixed, CENTER) > OUT_OF_AREA_M) {
      accuracyPoor.value = false;
      mode.value = "out_of_area";
      error.value = "检测到你不在景区范围，已切换模拟巡游";
      return;
    }
    if (accuracy > LOW_ACCURACY_M) {
      accuracyPoor.value = true;
      mode.value = "low_accuracy";
      error.value = "定位精度不足，暂不触发讲解";
      return;
    }
    accuracyPoor.value = false;
    mode.value = "real";
    error.value = "";
  }

  function onSuccess(pos) {
    if (mode.value === "sim") return; // 手动切到模拟后忽略真实回调
    evaluate(pos.coords);
  }

  function onError(err) {
    if (mode.value === "sim") return;
    mode.value = err && err.code === 1 ? "denied" : "unsupported";
    error.value = mode.value === "denied" ? "定位权限被拒绝，已切换模拟巡游" : "当前环境不支持定位，已切换模拟巡游";
    startSimulated();
  }

  function startReal() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      mode.value = "unsupported";
      error.value = "当前环境不支持定位，已切换模拟巡游";
      startSimulated();
      return;
    }
    stopWalk();
    mode.value = "real";
    watchId = navigator.geolocation.watchPosition(onSuccess, onError, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000,
    });
  }

  function startSimulated(lat, lng) {
    if (watchId !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    mode.value = "sim";
    error.value = "";
    accuracyPoor.value = false;
    if (Number.isFinite(lat) && Number.isFinite(lng)) setSimulated(lat, lng);
    else if (!position.value) setSimulated(CENTER.lat, CENTER.lng);
  }

  function startWalk(spots) {
    stopWalk();
    const path = (spots || []).filter((s) => Number.isFinite(s.lat) && Number.isFinite(s.lng));
    if (path.length < 2) return;
    startSimulated(path[0].lat, path[0].lng);
    walkPath = path;
    walkIndex = 0;
    walkSegmentProgress = 0;
    walkTimer = setInterval(() => {
      const from = walkPath[walkIndex];
      const to = walkPath[walkIndex + 1];
      if (!to) { stopWalk(); return; }
      const total = haversineMeters(from, to);
      const stepMeters = SIM_WALK_SPEED_MPS * (SIM_TICK_MS / 1000);
      walkSegmentProgress += total > 0 ? stepMeters / total : 1;

      if (walkSegmentProgress >= 1) {
        walkIndex += 1;
        walkSegmentProgress = 0;
        if (walkIndex >= walkPath.length - 1) {
          if (SIM_WALK_ON_ARRIVE === "loop") walkIndex = 0;
          else { const last = walkPath[walkPath.length - 1]; setSimulated(last.lat, last.lng); stopWalk(); return; }
        }
        const nextFrom = walkPath[walkIndex];
        setSimulated(nextFrom.lat, nextFrom.lng);
        return;
      }
      setSimulated(from.lat + (to.lat - from.lat) * walkSegmentProgress, from.lng + (to.lng - from.lng) * walkSegmentProgress);
    }, SIM_TICK_MS);
  }

  function stopWalk() {
    if (walkTimer) { clearInterval(walkTimer); walkTimer = null; }
    walkPath = [];
    walkIndex = 0;
    walkSegmentProgress = 0;
  }

  function start() {
    enabled.value = true;
    startReal();
  }

  function stop() {
    enabled.value = false;
    if (watchId !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    stopWalk();
    mode.value = "idle";
  }

  return { position, mode, error, enabled, accuracyPoor, start, stop, startSimulated, setSimulated, startWalk, stopWalk };
}
