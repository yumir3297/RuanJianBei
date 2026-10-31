import "./offline.css";

import {
  createConnectivityMonitor,
  describeConnectivity,
  normalizeReturnTarget,
} from "./connectivity.js";
import { createRunnerGame } from "./game.js";
import { createOfflineStorage } from "./offline-storage.js";
import { createMapViewer } from "./offline-map.js";
import { CONTACTS_URL, renderContacts, sanitizeContacts } from "./offline-help.js";
import { prepareOfflinePackage } from "./offline-registration.js";

const APP_VERSION = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "dev";
const MAP_META_URL = "/offline/map/map-meta.json";

const $ = (id) => document.getElementById(id);

const dom = {
  netChip: $("net-chip"),
  cacheChip: $("cache-chip"),
  cacheDetail: $("cache-detail"),
  siteName: $("site-name"),
  score: $("score"),
  bestScore: $("best-score"),
  stage: $("game-stage"),
  overlay: $("game-overlay"),
  overlayText: $("overlay-text"),
  gameStatus: $("game-status"),
  btnStart: $("btn-start"),
  btnPause: $("btn-pause"),
  btnRestart: $("btn-restart"),
  btnJump: $("btn-jump"),
  btnOpenMap: $("open-map"),
  btnOpenHelp: $("open-help"),
  btnOpenInfo: $("open-info"),
  btnReturn: $("btn-return"),
  btnReturnRecovered: $("btn-return-recovered"),
  btnReturnInfo: $("btn-return-info"),
  btnPrepare: $("btn-prepare"),
  recoverBanner: $("recover-banner"),
  mapDialog: $("map-dialog"),
  mapWarning: $("map-warning"),
  mapEmpty: $("map-empty"),
  mapEmptyDetail: $("map-empty-detail"),
  mapViewport: $("map-viewport"),
  mapImage: $("map-image"),
  helpSheet: $("help-sheet"),
  infoSheet: $("info-sheet"),
  contacts: $("contacts"),
  toast: $("toast"),
};

const storage = createOfflineStorage({ appVersion: APP_VERSION });
let snapshot = null;
let game = null;
let mapViewer = null;
let netState = "UNKNOWN";
let sawConnectivityTrouble = false;
let toastTimer = null;
let lastFocusedElement = null;

const openSheets = new Set();

function showToast(message) {
  dom.toast.textContent = message;
  dom.toast.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    dom.toast.hidden = true;
  }, 2600);
}

function setChip(element, tone, text) {
  element.className = `chip chip--${tone}`;
  element.textContent = text;
}

/* ---------------------------------- 游戏 ---------------------------------- */

const coarsePointer = Boolean(window.matchMedia?.("(pointer: coarse)").matches);

function haptic() {
  try {
    navigator.vibrate?.(8);
  } catch {
    // 不支持震动时静默忽略
  }
}

function updateOverlayForStatus(status, state) {
  if (!dom.overlay) return;
  const running = status === "RUNNING";
  dom.overlay.hidden = running;

  if (running) {
    dom.btnPause.setAttribute("aria-label", "暂停游戏");
    dom.btnPause.title = "暂停（P）";
    return;
  }

  dom.btnPause.setAttribute("aria-label", status === "PAUSED" ? "继续游戏" : "暂停游戏");
  dom.btnPause.title = status === "PAUSED" ? "继续（P）" : "暂停（P）";

  if (status === "READY") {
    dom.overlayText.textContent = "点击开始";
    dom.btnStart.dataset.mode = "play";
    dom.btnStart.setAttribute("aria-label", "开始游戏");
  } else if (status === "PAUSED") {
    dom.overlayText.textContent = "已暂停";
    dom.btnStart.dataset.mode = "play";
    dom.btnStart.setAttribute("aria-label", "继续游戏");
  } else if (status === "GAME_OVER") {
    dom.overlayText.textContent = `本局 ${state.lastRunScore} 分`;
    dom.btnStart.dataset.mode = "replay";
    dom.btnStart.setAttribute("aria-label", "再来一次");
  }
}

function initGame(initialBestScore) {
  game = createRunnerGame({
    canvas: $("game-canvas"),
    bestScore: initialBestScore,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    onStatusChange: (status, state) => {
      updateOverlayForStatus(status, state);
      dom.gameStatus.textContent =
        status === "RUNNING"
          ? coarsePointer
            ? "点击画面或按右下角按钮跳跃"
            : "空格 / ↑ 跳跃 · P 暂停 · R 重开"
          : status === "GAME_OVER"
            ? `已结束，本局 ${state.lastRunScore} 分`
            : status === "PAUSED"
              ? "游戏已暂停，地图与求助仍可使用"
              : "点击画面或按空格跳跃";
    },
    onScore: (score, best) => {
      dom.score.textContent = String(score);
      dom.bestScore.textContent = String(best);
    },
    onGameOver: (score, best) => {
      dom.bestScore.textContent = String(best);
      void saveSnapshot({ lastScore: score, bestScore: best });
    },
  });

  const startOrResume = () => {
    const status = game.getState().status;
    if (status === "PAUSED") game.resume();
    else if (status === "GAME_OVER") game.restart();
    else if (status === "READY") game.start();
  };

  dom.stage.addEventListener("click", () => {
    const status = game.getState().status;
    if (status === "RUNNING") {
      haptic();
      game.jump();
    } else if (status === "PAUSED") {
      game.resume();
    } else {
      startOrResume();
    }
  });

  dom.btnStart.addEventListener("click", (event) => {
    event.stopPropagation();
    startOrResume();
  });

  dom.btnPause.addEventListener("click", (event) => {
    event.stopPropagation();
    const status = game.getState().status;
    if (status === "RUNNING") game.pause();
    else if (status === "PAUSED") game.resume();
  });

  dom.btnRestart.addEventListener("click", (event) => {
    event.stopPropagation();
    game.restart();
  });

  dom.btnJump.addEventListener("click", (event) => {
    event.stopPropagation();
    haptic();
    game.jump();
  });

  document.addEventListener("keydown", (event) => {
    const active = document.activeElement;
    const inForm = active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA");
    if (inForm) return;

    if (event.key === "p" || event.key === "P") {
      const status = game.getState().status;
      if (status === "RUNNING") game.pause();
      else if (status === "PAUSED") game.resume();
      return;
    }
    if (event.key === "r" || event.key === "R") {
      game.restart();
      return;
    }
    if (event.key !== " " && event.key !== "Spacebar" && event.key !== "ArrowUp" && event.key !== "w") return;
    if (active && active.tagName === "BUTTON") return;
    event.preventDefault();
    haptic();
    game.jump();
  });

  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  motionQuery.addEventListener?.("change", (event) => game.setReducedMotion(event.matches));

  dom.score.textContent = "0";
  dom.bestScore.textContent = String(initialBestScore);
}

/* --------------------------------- 地图 --------------------------------- */

const MAP_WARNING_TEXT = {
  verified: "景区示意图，实际以现场指示及工作人员为准。",
  unverified: "该图为未核验占位示意图，不含经核验的出入口、服务点与救援路线，不可用于救援导航。",
  missing: "尚未获得可离线分发的景区简图。",
};

function ensureMapViewer() {
  if (mapViewer) return mapViewer;
  mapViewer = createMapViewer({ viewport: dom.mapViewport, image: dom.mapImage });
  $("map-zoom-in").addEventListener("click", () => mapViewer.zoomIn());
  $("map-zoom-out").addEventListener("click", () => mapViewer.zoomOut());
  $("map-reset").addEventListener("click", () => mapViewer.reset());
  return mapViewer;
}

function showMapEmpty(detail) {
  dom.mapEmpty.hidden = false;
  dom.mapViewport.hidden = true;
  dom.mapEmptyDetail.textContent = detail;
}

function applyMapMeta(meta) {
  const status = meta && ["verified", "unverified", "missing"].includes(meta.status) ? meta.status : "missing";
  dom.mapWarning.hidden = false;
  dom.mapWarning.textContent = MAP_WARNING_TEXT[status] || MAP_WARNING_TEXT.missing;
  if (meta?.regionName) dom.siteName.textContent = meta.regionName;

  if (status === "missing" || !meta?.file) {
    showMapEmpty("尚未获得经核验的可离线地图资源，请以现场指示牌与工作人员指引为准。");
    return;
  }
  dom.mapEmpty.hidden = true;
  dom.mapViewport.hidden = false;
  dom.mapImage.onload = () => {
    dom.mapEmpty.hidden = true;
    dom.mapViewport.hidden = false;
  };
  dom.mapImage.onerror = () => {
    showMapEmpty("地图文件缺失或损坏，请以现场指示牌与工作人员指引为准。");
  };
  dom.mapImage.src = meta.file;
}

async function loadMap() {
  try {
    const response = await fetch(MAP_META_URL, { cache: "no-cache" });
    if (!response.ok) throw new Error(`map-meta-http-${response.status}`);
    applyMapMeta(await response.json());
  } catch (error) {
    dom.mapWarning.hidden = false;
    dom.mapWarning.textContent = MAP_WARNING_TEXT.missing;
    showMapEmpty(`地图配置不可用（${String(error?.message || error)}），请以现场指示牌为准。`);
  }
}

/* --------------------------------- 求助 --------------------------------- */

async function loadContactsPanel() {
  dom.contacts.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "contact-empty";
  loading.textContent = "正在读取景区联系电话…";
  dom.contacts.appendChild(loading);
  try {
    const response = await fetch(CONTACTS_URL, { cache: "no-cache" });
    if (!response.ok) throw new Error(`contacts-http-${response.status}`);
    const data = sanitizeContacts(await response.json());
    renderContacts(dom.contacts, data, showToast);
    if (data.regionName && dom.siteName.textContent === "景区离线应急页") {
      dom.siteName.textContent = data.regionName;
    }
    void saveSnapshot({ contactsVersion: data.contactsVersion });
  } catch (error) {
    dom.contacts.replaceChildren();
    const empty = document.createElement("p");
    empty.className = "contact-empty";
    empty.textContent = `景区联系电话暂不可用（${String(error?.message || error)}）。请向附近工作人员求助。`;
    dom.contacts.appendChild(empty);
  }
}

/* ------------------------------- 浮层管理 ------------------------------- */

function openSheet(element) {
  lastFocusedElement = document.activeElement;
  element.hidden = false;
  openSheets.add(element);
  document.body.classList.add("has-sheet");
  game?.setOverlayPaused(true);
  element.querySelector("button, a, [tabindex]")?.focus({ preventScroll: true });
}

function closeSheet(element) {
  element.hidden = true;
  openSheets.delete(element);
  if (!openSheets.size) {
    document.body.classList.remove("has-sheet");
    game?.setOverlayPaused(false);
  }
  lastFocusedElement?.focus?.({ preventScroll: true });
}

function openMap() {
  ensureMapViewer();
  openSheet(dom.mapDialog);
  mapViewer.reset();
}

function openHelp() {
  openSheet(dom.helpSheet);
}

function openInfo() {
  openSheet(dom.infoSheet);
}

/* ------------------------------- 连通性 -------------------------------- */

const NET_CHIP_TONE = {
  UNKNOWN: "unknown",
  ONLINE: "online",
  SUSPECT: "suspect",
  DEGRADED: "offline",
  RECOVERING: "suspect",
};

function renderNetChip(state) {
  const deviceOffline = navigator.onLine === false;
  const text = deviceOffline && state !== "ONLINE" ? "设备离线 · 检测中" : describeConnectivity(state);
  setChip(dom.netChip, NET_CHIP_TONE[state] || "unknown", text);
}

function initConnectivity() {
  const monitor = createConnectivityMonitor({ intervalMs: 10000, hiddenIntervalMs: 30000 });
  monitor.subscribe((state) => {
    netState = state;
    renderNetChip(state);
    if (state === "SUSPECT" || state === "DEGRADED") sawConnectivityTrouble = true;
    if (state === "ONLINE" && sawConnectivityTrouble) {
      dom.recoverBanner.hidden = false;
      dom.gameStatus.textContent = "网页服务已恢复，可随时返回数字人导游";
    }
    dom.btnReturn.title =
      state === "ONLINE" ? "返回数字人导游" : "返回数字人导游（可能无法加载）";
    dom.btnReturn.setAttribute("aria-label", dom.btnReturn.title);
  });
  window.addEventListener("online", () => renderNetChip(netState));
  window.addEventListener("offline", () => renderNetChip(netState));
  monitor.start();
}

/* ------------------------------- 离线包 -------------------------------- */

async function checkOfflinePackage() {
  setChip(dom.cacheChip, "warn", "离线包检查中");
  const result = await prepareOfflinePackage();
  if (result.ready) {
    setChip(dom.cacheChip, "ok", "离线已就绪");
    dom.cacheDetail.textContent = `离线资源 ${result.buildId} · 已缓存 ${result.urls?.length || 0} 个文件 · 可断网使用`;
    dom.btnPrepare.hidden = true;
  } else if (!result.supported) {
    setChip(dom.cacheChip, "warn", "离线包不可用");
    dom.cacheDetail.textContent = `离线包不可用（${result.error || "需要 HTTPS 或 localhost"}）。在线功能不受影响。`;
    dom.btnPrepare.hidden = false;
  } else {
    setChip(dom.cacheChip, "warn", "离线包未就绪");
    dom.cacheDetail.textContent = `离线包未就绪（${result.error || "资源未全部缓存"}）。请保持联网后点击重试。`;
    dom.btnPrepare.hidden = false;
  }
  return result;
}

/* ------------------------------- 返回主站 ------------------------------- */

function getReturnTarget() {
  return normalizeReturnTarget(snapshot?.returnTarget || "/tourist");
}

async function saveSnapshot(patch) {
  const result = await storage.save(patch);
  if (result.snapshot) snapshot = result.snapshot;
  if (!result.ok) showToast("本地存储不可用，本次成绩不会被保存。");
}

function goBackToGuide() {
  if (netState !== "ONLINE") {
    const confirmed = window.confirm(
      "当前网页服务可能仍不可达，返回后页面可能无法正常加载。仍要返回数字人导游吗？",
    );
    if (!confirmed) return;
  }
  const target = getReturnTarget();
  void storage.save({
    returnTarget: target,
    lastScore: game?.getState().score || 0,
    bestScore: game?.getState().bestScore || 0,
    returnConsumedAt: new Date().toISOString(),
  });
  window.location.assign(target);
}

/* --------------------------------- 启动 -------------------------------- */

function wireStaticControls() {
  dom.btnOpenMap.addEventListener("click", openMap);
  dom.btnOpenHelp.addEventListener("click", openHelp);
  dom.btnOpenInfo.addEventListener("click", openInfo);
  document.querySelectorAll("[data-close-map]").forEach((button) =>
    button.addEventListener("click", () => closeSheet(dom.mapDialog)),
  );
  document.querySelectorAll("[data-close-help]").forEach((button) =>
    button.addEventListener("click", () => closeSheet(dom.helpSheet)),
  );
  document.querySelectorAll("[data-close-info]").forEach((button) =>
    button.addEventListener("click", () => closeSheet(dom.infoSheet)),
  );
  dom.btnReturn.addEventListener("click", goBackToGuide);
  dom.btnReturnInfo.addEventListener("click", goBackToGuide);
  dom.btnReturnRecovered.addEventListener("click", goBackToGuide);
  dom.btnPrepare.addEventListener("click", () => void checkOfflinePackage());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && openSheets.size) {
      closeSheet([...openSheets][openSheets.size - 1]);
    }
  });
}

async function boot() {
  wireStaticControls();
  snapshot = await storage.load();
  dom.bestScore.textContent = String(snapshot.bestScore);
  initGame(snapshot.bestScore);
  initConnectivity();

  void loadMap();
  void loadContactsPanel();
  void checkOfflinePackage();

  if (navigator.storage?.persist) {
    navigator.storage.persist().catch(() => {});
  }
  void saveSnapshot({ appVersion: APP_VERSION });
}

boot();
