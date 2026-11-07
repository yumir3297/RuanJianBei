export const VISITOR_CONFIG_POLL_INTERVAL_MS = 60_000;

export function createVisitorConfigRefresher({
  fetchConfig,
  clock = globalThis,
  isVisible = () => typeof document === "undefined" || !document.hidden,
  isIdle = () => true,
  onApply = () => {},
  intervalMs = VISITOR_CONFIG_POLL_INTERVAL_MS,
}) {
  let started = false;
  let disposed = false;
  let visible = null;
  let intervalId = null;
  let inFlight = null;
  let pendingConfig = null;
  let latestConfig = null;

  function applyPending() {
    if (!pendingConfig || !isIdle() || disposed) return false;
    const next = pendingConfig;
    pendingConfig = null;
    latestConfig = next;
    onApply(next);
    return true;
  }

  async function refresh() {
    if (disposed) return latestConfig;
    if (inFlight) return inFlight;
    inFlight = (async () => {
      try {
        const config = await fetchConfig();
        if (disposed) return latestConfig;
        pendingConfig = config;
        applyPending();
        return config;
      } catch {
        return latestConfig;
      } finally {
        inFlight = null;
      }
    })();
    return inFlight;
  }

  function stopPolling() {
    if (intervalId !== null) clock.clearInterval(intervalId);
    intervalId = null;
  }

  function setVisible(nextVisible) {
    if (disposed || !started || visible === Boolean(nextVisible)) return Promise.resolve(latestConfig);
    visible = Boolean(nextVisible);
    if (!visible) {
      stopPolling();
      return Promise.resolve(latestConfig);
    }
    const request = refresh();
    intervalId = clock.setInterval(() => {
      if (visible && !disposed) refresh();
    }, intervalMs);
    return request;
  }

  function start() {
    if (disposed || started) return Promise.resolve(latestConfig);
    started = true;
    return setVisible(isVisible());
  }

  function flushPending() {
    return applyPending();
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    pendingConfig = null;
    stopPolling();
  }

  return { start, refresh, flushPending, setVisible, dispose };
}
