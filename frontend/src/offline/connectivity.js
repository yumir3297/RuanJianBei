/**
 * 同源服务连通性状态机（主站与离线页共用）。
 *
 * 只依赖 fetch + AbortController；不读 localStorage 里可能过期的 online 标记，
 * 每个页面实例自建一份监测器，避免跨页面共享失效定时器。
 */

export const CONNECTIVITY_STATES = Object.freeze({
  UNKNOWN: "UNKNOWN",
  ONLINE: "ONLINE",
  SUSPECT: "SUSPECT",
  DEGRADED: "DEGRADED",
  RECOVERING: "RECOVERING",
});

export const DEFAULT_CONNECTIVITY_OPTIONS = Object.freeze({
  probeUrl: "/health",
  intervalMs: 5000,
  hiddenIntervalMs: 30000,
  timeoutMs: 2500,
  degradedFails: 3,
  degradedMinMs: 15000,
  recoverSuccesses: 2,
  recoverMinGapMs: 3000,
});

const STATE_LABELS = {
  UNKNOWN: "连接检测中",
  ONLINE: "网页服务正常",
  SUSPECT: "连接不稳定",
  DEGRADED: "网页服务不可达",
  RECOVERING: "正在确认恢复",
};

export function describeConnectivity(state) {
  return STATE_LABELS[state] || STATE_LABELS.UNKNOWN;
}

export function initialConnectivitySnapshot(now = 0) {
  return {
    state: CONNECTIVITY_STATES.UNKNOWN,
    failCount: 0,
    successCount: 0,
    firstFailAt: 0,
    lastOkAt: 0,
    everOnline: false,
    lastProbeAt: now,
    reason: "",
  };
}

/**
 * 纯函数：根据一次探测结果推导下一个状态快照。
 * 事件：{ type: 'probe-ok' | 'probe-fail' | 'reset', time, reason? }
 */
export function reduceConnectivity(prev, event, options = {}) {
  const policy = { ...DEFAULT_CONNECTIVITY_OPTIONS, ...options };
  const now = Number(event.time) || 0;

  if (event.type === "reset") {
    return initialConnectivitySnapshot(now);
  }

  if (event.type === "probe-ok") {
    const successCount = prev.successCount + 1;
    const previousOkAt = prev.lastOkAt;
    const gapOk = !previousOkAt || now - previousOkAt >= policy.recoverMinGapMs;
    // 只有“页面从加载起就一直正常”的首次成功才立即判为在线；
    // 已经出现过失败（例如离线时打开页面）必须走两次确认，避免单次抖动误报恢复。
    const canFastOnline = !prev.everOnline && prev.failCount === 0;
    let state;
    if (prev.state === CONNECTIVITY_STATES.ONLINE) {
      state = CONNECTIVITY_STATES.ONLINE;
    } else if (canFastOnline) {
      state = CONNECTIVITY_STATES.ONLINE;
    } else if (successCount >= policy.recoverSuccesses && gapOk) {
      state = CONNECTIVITY_STATES.ONLINE;
    } else {
      state = CONNECTIVITY_STATES.RECOVERING;
    }
    return {
      ...prev,
      state,
      failCount: 0,
      successCount,
      firstFailAt: 0,
      lastOkAt: now,
      everOnline: true,
      lastProbeAt: now,
      reason: event.reason || "ok",
    };
  }

  if (event.type === "probe-fail") {
    const failCount = prev.failCount + 1;
    const firstFailAt = prev.firstFailAt || now;
    const failingLongEnough = now - firstFailAt >= policy.degradedMinMs;
    let state;
    if (prev.state === CONNECTIVITY_STATES.DEGRADED) {
      state = CONNECTIVITY_STATES.DEGRADED;
    } else if (failCount >= policy.degradedFails && failingLongEnough) {
      state = CONNECTIVITY_STATES.DEGRADED;
    } else {
      state = CONNECTIVITY_STATES.SUSPECT;
    }
    return {
      ...prev,
      state,
      failCount,
      successCount: 0,
      firstFailAt,
      lastProbeAt: now,
      reason: event.reason || "probe-failed",
    };
  }

  return prev;
}

/**
 * 校验 /health 响应：必须是 200 + application/json + {status:'ok'}。
 * HTML 登录页、门户页、伪缓存 200、错误 JSON 一律视为失败。
 */
export async function evaluateHealthResponse(response) {
  if (!response) return { ok: false, reason: "no-response" };
  if (response.redirected) return { ok: false, reason: "unexpected-redirect" };
  if (!response.ok) return { ok: false, reason: `http-${response.status ?? "error"}` };

  const contentType = String(response.headers?.get?.("content-type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    return { ok: false, reason: "non-json-response" };
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    return { ok: false, reason: "invalid-json" };
  }

  if (!payload || payload.status !== "ok") {
    return { ok: false, reason: "status-not-ok" };
  }
  return { ok: true, reason: "ok" };
}

/**
 * 只允许回到同源游客入口及其白名单工具。
 */
export const RETURN_TARGET_WHITELIST = Object.freeze(["/tourist"]);
export const RETURN_TOOL_WHITELIST = Object.freeze(["map", "explore", "route", "quiz"]);

export function normalizeReturnTarget(raw) {
  if (typeof raw !== "string") return "/tourist";
  const value = raw.trim();
  if (!value.startsWith("/") || value.startsWith("//")) return "/tourist";
  const [path, queryString = ""] = value.split("?");
  if (path !== "/tourist") return "/tourist";
  const params = new URLSearchParams(queryString);
  const tool = params.get("tool");
  if (tool && RETURN_TOOL_WHITELIST.includes(tool)) {
    return `/tourist?tool=${tool}`;
  }
  return "/tourist";
}

export function createConnectivityMonitor(options = {}) {
  const policy = { ...DEFAULT_CONNECTIVITY_OPTIONS, ...options };
  const now = options.now || (() => Date.now());
  const fetchImpl = options.fetchImpl || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
  const documentRef = options.documentRef || (typeof document !== "undefined" ? document : null);
  const setTimeoutImpl = options.setTimeoutImpl || setTimeout;
  const clearTimeoutImpl = options.clearTimeoutImpl || clearTimeout;

  let snapshot = initialConnectivitySnapshot(now());
  const listeners = new Set();
  let running = false;
  let generation = 0;
  let timerId = null;
  let inFlight = null;

  function stage(result) {
    snapshot = reduceConnectivity(
      snapshot,
      { type: result.ok ? "probe-ok" : "probe-fail", time: now(), reason: result.reason },
      policy,
    );
    for (const listener of listeners) {
      try {
        listener(snapshot.state);
      } catch {
        // 单个订阅者异常不能影响监测器
      }
    }
  }

  async function runProbe() {
    const startedGeneration = generation;
    if (!fetchImpl) return stage({ ok: false, reason: "fetch-unavailable" });

    let controller = null;
    let timer = null;
    const startedAt = now();
    try {
      if (typeof AbortController === "function") {
        controller = new AbortController();
        timer = setTimeoutImpl(() => controller.abort(), policy.timeoutMs);
      }
      const response = await fetchImpl(policy.probeUrl, {
        method: "GET",
        cache: "no-store",
        redirect: "error",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        signal: controller?.signal,
      });
      const result = await evaluateHealthResponse(response);
      if (startedGeneration !== generation) return result;
      stage(result);
      return { ...result, time: now() };
    } catch (error) {
      const aborted = controller?.signal?.aborted;
      const reason = aborted ? "timeout" : String(error?.name || error?.message || "network-error");
      const result = { ok: false, reason };
      if (startedGeneration !== generation) return result;
      stage(result);
      return { ...result, time: now(), startedAt };
    } finally {
      if (timer != null) clearTimeoutImpl(timer);
    }
  }

  function scheduleNext() {
    if (!running) return;
    const hidden = documentRef?.visibilityState === "hidden";
    const delay = hidden ? policy.hiddenIntervalMs : policy.intervalMs;
    timerId = setTimeoutImpl(async () => {
      timerId = null;
      if (!running) return;
      await probeNow();
      scheduleNext();
    }, delay);
  }

  function probeNow() {
    if (inFlight) return inFlight;
    inFlight = runProbe().finally(() => {
      inFlight = null;
    });
    return inFlight;
  }

  function handleVisibleSignal() {
    if (!running) return;
    probeNow();
  }

  function start() {
    if (running) return;
    running = true;
    generation += 1;
    documentRef?.addEventListener?.("visibilitychange", handleVisibleSignal);
    documentRef?.defaultView?.addEventListener?.("online", handleVisibleSignal);
    documentRef?.defaultView?.addEventListener?.("offline", handleVisibleSignal);
    probeNow();
    scheduleNext();
  }

  function stop() {
    if (!running) return;
    running = false;
    generation += 1;
    if (timerId != null) {
      clearTimeoutImpl(timerId);
      timerId = null;
    }
    documentRef?.removeEventListener?.("visibilitychange", handleVisibleSignal);
    documentRef?.defaultView?.removeEventListener?.("online", handleVisibleSignal);
    documentRef?.defaultView?.removeEventListener?.("offline", handleVisibleSignal);
  }

  function subscribe(listener) {
    if (typeof listener !== "function") return () => {};
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  return {
    getState: () => snapshot.state,
    getSnapshot: () => ({ ...snapshot }),
    start,
    stop,
    subscribe,
    probeNow,
  };
}
