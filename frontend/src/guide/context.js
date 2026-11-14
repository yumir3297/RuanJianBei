import { haversineMeters, wgs84ToGcj02 } from "../constants/narration.js";

const MAX_POSITION_AGE_MS = 30_000;
const MAX_ACCURACY_M = 80;
const MAX_NEARBY_SPOT_SUGGESTION_DISTANCE_M = 250;

function validCoordinate(value, min, max) {
  return Number.isFinite(value) && value >= min && value <= max;
}

/** Build a display-safe context snapshot. Simulation never becomes live safety evidence. */
export function buildGuideContext({ position, mode, catalog = [], preferences = {}, tour = null, nowMs = Date.now() }) {
  const simulated = mode === "sim";
  const observedAt = Number.isFinite(position?.observedAt) ? position.observedAt : position?.ts;
  const rawLocation = position?.wgs84 || position;
  const coordinatesValid = validCoordinate(rawLocation?.lat, -90, 90) && validCoordinate(rawLocation?.lng, -180, 180);
  const ageMs = Number.isFinite(observedAt) ? nowMs - observedAt : Infinity;
  const fresh = ageMs >= 0 && ageMs <= MAX_POSITION_AGE_MS;
  const accurate = Number.isFinite(position?.accuracy) && position.accuracy >= 0 && position.accuracy <= MAX_ACCURACY_M;
  const locationValid = coordinatesValid && fresh && accurate && !simulated && mode === "real";

  return {
    schemaVersion: "1.0",
    capturedAt: new Date(nowMs).toISOString(),
    location: coordinatesValid ? {
      lat: rawLocation.lat,
      lng: rawLocation.lng,
      coordinateSystem: position?.wgs84 ? "WGS84" : (position.coordinateSystem || "GCJ-02"),
      accuracyM: simulated ? null : position.accuracy,
      source: simulated ? "simulation" : "browser_geolocation",
      mode: simulated ? "sim" : mode,
      observedAt: Number.isFinite(observedAt) ? new Date(observedAt).toISOString() : null,
      validForSafety: locationValid,
    } : { mode: mode || "unavailable", validForSafety: false },
    spot: catalog.find((item) => item?.spot_code === preferences.spotCode) || null,
    visitor: {
      interests: Array.isArray(preferences.interests) ? preferences.interests.slice(0, 8) : [],
      remainingMinutes: Number.isInteger(preferences.remainingMinutes) && preferences.remainingMinutes >= 1
        ? Math.min(preferences.remainingMinutes, 720) : null,
    },
    tour: tour ? { id: tour.id || null, version: tour.version ?? null, progressVersion: tour.progressVersion ?? null } : null,
  };
}

export function isPublishedCoordinateUsable(entry) {
  return Number.isFinite(entry?.latitude) && Number.isFinite(entry?.longitude)
    && entry?.coordinate_system === "GCJ-02" && Boolean(entry?.coordinate_evidence_id);
}

export function findNearbyPublishedSpot(location, catalog, radiusM = MAX_NEARBY_SPOT_SUGGESTION_DISTANCE_M) {
  if (!location?.validForSafety || location.mode !== "real"
      || !Number.isFinite(location.accuracyM) || location.accuracyM > MAX_ACCURACY_M
      || !Array.isArray(catalog)) return null;
  const visitorPoint = location.coordinateSystem === "WGS84"
    ? wgs84ToGcj02(location.lat, location.lng)
    : location.coordinateSystem === "GCJ-02" ? { lat: location.lat, lng: location.lng } : null;
  if (!visitorPoint) return null;

  let nearest = null;
  for (const spot of catalog) {
    if (!isPublishedCoordinateUsable(spot)) continue;
    const distanceM = haversineMeters(visitorPoint, { lat: spot.latitude, lng: spot.longitude });
    if (!nearest || distanceM < nearest.distanceM) nearest = { spot, distanceM };
  }
  return nearest && nearest.distanceM <= radiusM ? nearest : null;
}

export function nextPublishedTourStop(tour, selectedSpot, catalog) {
  if (tour?.snapshot?.schema_version !== 2 || tour?.progress?.status !== "active"
      || !Array.isArray(tour.snapshot.stops) || !Array.isArray(catalog)) return null;
  const states = tour.progress.status_by_stop || {};
  const current = tour.snapshot.stops.findIndex(stop => stop.stop_id === tour.progress.current_stop_id && states[stop.stop_id] === "current");
  if (current < 0) return null;
  const anchor = tour.snapshot.stops[current];
  if (anchor.kind !== "visit" || anchor.spot_code !== selectedSpot?.spot_code
      || !anchor.source_revision_id || anchor.source_revision_id !== selectedSpot?.published_revision_id) return null;
  const next = tour.snapshot.stops.slice(current + 1).find(stop => states[stop.stop_id] === "pending");
  if (next?.kind !== "visit" || !next.source_revision_id) return null;
  const matches = catalog.filter(item => item.spot_code === next.spot_code && item.published_revision_id === next.source_revision_id);
  return matches.length === 1 && matches[0].title ? matches[0] : null;
}

export function buildAdaptiveNarrationRequest({ decision, spot, interests = [], remainingMinutes, simulated = false, weatherAdaptation = null, tour = null, catalog = [] }) {
  if (!spot?.title || !["short_narration", "full_narration"].includes(decision?.action)) return null;
  const style = decision.action === "short_narration" ? "约 45 秒的简短讲解" : "完整但简洁的现场讲解";
  const focus = interests.length ? `重点关注${interests.slice(0, 3).join("、")}` : "优先讲解最有代表性的内容";
  const scenarioLabel = simulated ? "演示场景中的剩余时间为模拟值" : `游客剩余游览时间约 ${remainingMinutes} 分钟`;
  const weatherHint = weatherAdaptation?.kind === "precipitation"
    ? `当前${weatherAdaptation.simulated ? "模拟天气" : "景区天气来源显示"}${weatherAdaptation.condition}；讲解保持利落，避免要求游客长时间驻足；不要推断景点室内属性、开放状态或安全状态，现场情况以景区公告为准。`
    : "";
  const nextSpot = nextPublishedTourStop(tour, spot, catalog);
  const tourHint = nextSpot
    ? `已保存行程中的下一待游览景点是${nextSpot.title}；如资料支持，可自然预告下一站，不要臆造两个景点之间的关系或声称游客已经到访。`
    : "";
  return {
    attraction: spot.title,
    query: `请依据已发布的景点资料介绍${spot.title}，生成${style}；${focus}。${scenarioLabel}。${weatherHint}${tourHint}只陈述资料支持的事实，不确定的内容明确说明。`,
  };
}

export function buildItinerarySuggestionRequest({ decision, remainingMinutes, simulated = false }) {
  if (!Number.isInteger(remainingMinutes)) return null;
  if (simulated && decision?.reason_codes?.includes("demo_crowd_pressure")) {
    return `演示情境：下一景点客流偏高（模拟数据）。请基于当前游览计划，为未完成景点生成一个可确认的避开拥挤调整提案；保留已完成景点和已有锁定约束，不要修改剩余时间预算。`;
  }
  if (decision?.action !== "short_narration") return null;
  return `我现在大约还剩 ${remainingMinutes} 分钟。请基于当前游览计划，为未完成景点生成一个更紧凑、可确认的路线调整提案；保留已完成景点和已有锁定约束，必要时保留休息安排。这个情境时间只用于提出路线建议，不要修改游览的剩余时间预算。`;
}

export function isGuideDecisionExpired(result, nowMs = Date.now()) {
  const expiresAt = Date.parse(result?.expires_at || "");
  return Number.isFinite(expiresAt) && nowMs >= expiresAt;
}
