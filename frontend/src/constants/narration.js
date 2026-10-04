// 靠近景点自动讲解（讲解机）配置与纯几何工具。
// 坐标链路：浏览器 GPS 为 WGS84，景区坐标与高德底图均为 GCJ-02，比距离前必须纠偏。

export const TRIGGER_RADIUS_M = 80;      // 进入半径
export const EXIT_RADIUS_M = 120;        // 离开半径（滞回，防抖）
export const COOLDOWN_MS = 12000;        // 抖动冷却
export const OUT_OF_AREA_M = 4000;       // 距景区中心超出即判为不在景区
export const LOW_ACCURACY_M = 160;       // 精度差于此值不参与触发
export const SIM_TICK_MS = 1000;         // 模拟巡游插值步长
export const SIM_WALK_SPEED_MPS = 8;     // 模拟巡游速度（演示友好）
export const SIM_WALK_ON_ARRIVE = "loop"; // 到达终点：loop | stop
export const PENDING_MAX_WAIT_MS = 25000; // 忙时排队最长等待，超时则中断当前播放补播
export const BROWSER_SPEECH_MAX_CHARS = 80; // 浏览器朗读兜底只念开头，避免长时间占用播放通道

/** 浏览器朗读兜底文本：超长时截到最近句读处并省略，卡片仍展示全文。 */
export function speechText(text, maxChars = BROWSER_SPEECH_MAX_CHARS) {
  const value = String(text || "").trim();
  if (value.length <= maxChars) return value;
  const head = value.slice(0, maxChars);
  const cut = Math.max(head.lastIndexOf("。"), head.lastIndexOf("！"), head.lastIndexOf("？"), head.lastIndexOf("，"));
  return `${cut > Math.floor(maxChars / 3) ? head.slice(0, cut + 1) : head}……`;
}

const EARTH_RADIUS_M = 6371008.8;

const toRad = (deg) => (deg * Math.PI) / 180;

/** 两点球面距离（米）。 */
export function haversineMeters(a, b) {
  if (!a || !b) return Infinity;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

const GCJ_A = 6378245.0;
const GCJ_EE = 0.00669342162296594323;

function outOfChina(lat, lng) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271;
}

function transformLat(x, y) {
  let ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
  ret += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  ret += ((20 * Math.sin(y * Math.PI) + 40 * Math.sin((y / 3) * Math.PI)) * 2) / 3;
  ret += ((160 * Math.sin((y / 12) * Math.PI) + 320 * Math.sin((y * Math.PI) / 30)) * 2) / 3;
  return ret;
}

function transformLng(x, y) {
  let ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
  ret += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  ret += ((20 * Math.sin(x * Math.PI) + 40 * Math.sin((x / 3) * Math.PI)) * 2) / 3;
  ret += ((150 * Math.sin((x / 12) * Math.PI) + 300 * Math.sin((x * Math.PI) / 30)) * 2) / 3;
  return ret;
}

/** WGS84 -> GCJ-02（标准算法，中国大陆境内生效，境外原样返回）。 */
export function wgs84ToGcj02(lat, lng) {
  if (outOfChina(lat, lng)) return { lat, lng };
  let dLat = transformLat(lng - 105.0, lat - 35.0);
  let dLng = transformLng(lng - 105.0, lat - 35.0);
  const radLat = (lat / 180.0) * Math.PI;
  let magic = Math.sin(radLat);
  magic = 1 - GCJ_EE * magic * magic;
  const sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / (((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic)) * Math.PI);
  dLng = (dLng * 180.0) / ((GCJ_A / sqrtMagic) * Math.cos(radLat) * Math.PI);
  return { lat: lat + dLat, lng: lng + dLng };
}

/** 在候选中找距离最近的一个景点，返回 { spot, distance }；空候选返回 null。 */
export function findNearestSpot(position, spots) {
  if (!position || !Array.isArray(spots) || spots.length === 0) return null;
  let best = null;
  for (const spot of spots) {
    const distance = haversineMeters(position, spot);
    if (!best || distance < best.distance) best = { spot, distance };
  }
  return best;
}
