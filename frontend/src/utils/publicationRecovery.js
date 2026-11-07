const STORAGE_KEY = "guide-pending-publication-v1";
const copy = (value) => JSON.parse(JSON.stringify(value));

// Keep the exact idempotency key and selected revisions until the outcome of
// a publication is known. Nothing here retries automatically.
export function createPublicationRecovery({ storage, createKey, submit }) {
  let pending;
  let loaded = false;
  let durable = !!storage;
  let inFlight = null;

  function load() {
    if (loaded) return pending;
    loaded = true;
    try {
      const raw = storage?.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed.key !== "string" || !parsed.key || !Array.isArray(parsed.items) || !parsed.items.length) {
        throw new Error("发布记录损坏，无法安全确认原任务；请联系管理员核对。");
      }
      pending = parsed;
      return pending;
    } catch (error) {
      if (error instanceof SyntaxError || error?.message?.includes("发布记录损坏")) {
        loaded = false;
        throw new Error("发布记录损坏，无法安全确认原任务；请联系管理员核对。");
      }
      durable = false;
      return pending || null;
    }
  }

  function save(value) {
    pending = value;
    loaded = true;
    try {
      if (!storage) throw new Error("storage unavailable");
      if (value) storage.setItem(STORAGE_KEY, JSON.stringify(value));
      else storage.removeItem(STORAGE_KEY);
    } catch { durable = false; }
  }

  function getPending() {
    const value = load();
    return value ? copy(value) : null;
  }

  function begin(items) {
    if (load()) throw new Error("已有发布任务待确认，请先恢复原任务。");
    if (!Array.isArray(items) || !items.length) throw new Error("请选择需要发布的草稿。");
    const value = { key: createKey(), items: copy(items), jobId: null };
    if (!value.key) throw new Error("无法创建发布请求标识，请检查浏览器安全设置。");
    save(value);
    return getPending();
  }

  async function submitPending() {
    const value = load();
    if (!value) throw new Error("没有待确认的发布任务。");
    if (value.jobId) throw new Error("发布任务已创建，请查询原任务状态。");
    if (inFlight) return inFlight;
    inFlight = (async () => {
      const job = await submit(copy(value.items), value.key);
      if (!job || typeof job.id !== "string" || !job.id) throw new Error("发布结果无任务标识，请恢复确认。");
      save({ ...value, jobId: job.id });
      return job;
    })();
    try { return await inFlight; } finally { inFlight = null; }
  }

  return { begin, getPending, submitPending, clear: () => save(null), isDurable: () => durable };
}

export function createPublicationWorkflow({
  storage,
  createKey,
  submit,
  fetch,
  retry,
  onJob = () => {},
  onSuccess = () => {},
  setTimer = (callback, delay) => globalThis.setTimeout(callback, delay),
  clearTimer = (timer) => globalThis.clearTimeout(timer),
  pollIntervalMs = 1400,
}) {
  const recovery = createPublicationRecovery({ storage, createKey, submit });
  let pollTimer = null;
  let disposed = false;

  function stopPolling() {
    if (pollTimer !== null) clearTimer(pollTimer);
    pollTimer = null;
  }

  function showJob(job) {
    if (disposed) return;
    onJob(job);
    if (job?.state === "succeeded") {
      stopPolling();
      recovery.clear();
      onSuccess(job);
      return;
    }
    if (job?.state === "failed") {
      stopPolling();
      return;
    }
    if (["queued", "preparing"].includes(job?.state) && job.id) {
      stopPolling();
      pollTimer = setTimer(() => {
        pollTimer = null;
        if (!disposed) observe(job.id).catch(() => {});
      }, pollIntervalMs);
      return;
    }
    stopPolling();
  }

  async function observe(id) {
    stopPolling();
    try {
      const job = await fetch(id);
      showJob(job);
      return job;
    } catch (error) {
      showJob({
        id,
        state: "unknown",
        error: `暂时无法读取原发布任务状态：${error?.message || "网络错误"}`,
      });
      throw error;
    }
  }

  async function submitPending() {
    let created;
    try {
      created = await recovery.submitPending();
    } catch (error) {
      const status = Number(error?.response?.status);
      const definitiveRejection = status >= 400 && status < 500 && ![408, 425, 429].includes(status);
      if (definitiveRejection) {
        recovery.clear();
        showJob(null);
        throw error;
      }
      let pending = null;
      try { pending = recovery.getPending(); } catch { /* keep the visible recovery error */ }
      if (pending) {
        showJob({
          id: pending.jobId || undefined,
          state: "unknown",
          error: "发布请求结果尚未确认。恢复时会沿用原请求标识；不要重新创建发布任务。",
        });
      }
      throw error;
    }
    showJob(created);
    // A failed lookup does not negate the successful create response. Keep the
    // persisted job ID so a later GET can recover the publication state.
    return observe(created.id);
  }

  async function publish(items) {
    recovery.begin(items);
    if (!recovery.isDurable()) {
      recovery.clear();
      throw new Error("浏览器会话存储不可用，发布请求未发送；无法安全恢复重复请求。");
    }
    return submitPending();
  }

  async function restore() {
    let pending;
    try {
      pending = recovery.getPending();
    } catch (error) {
      showJob({ state: "unknown", error: error.message });
      throw error;
    }
    if (!pending) return null;
    if (!pending.jobId) {
      if (!recovery.isDurable()) {
        showJob({ state: "unknown", error: "无法可靠读取发布恢复记录；请勿新建发布任务。" });
        return pending;
      }
      showJob({
        state: "unknown",
        error: "上次发布请求没有收到确认。请恢复查询原任务；不会自动重发。",
      });
      return pending;
    }
    try {
      await observe(pending.jobId);
    } catch {
      // observe() already exposed an actionable unknown state to the UI.
    }
    return pending;
  }

  async function recover() {
    const pending = recovery.getPending();
    if (!pending) return null;
    if (pending.jobId) return observe(pending.jobId);
    if (!recovery.isDurable()) throw new Error("浏览器会话存储不可用，无法安全恢复发布请求。");
    return submitPending();
  }

  async function retryFailed() {
    const pending = recovery.getPending();
    if (!pending?.jobId) throw new Error("没有可重试的已知发布任务。");
    try {
      const job = await retry(pending.jobId);
      showJob(job);
      return await observe(pending.jobId);
    } catch (error) {
      try {
        // A retry may have committed even if its response was lost. Read the
        // known job before telling the operator that another retry is needed.
        return await observe(pending.jobId);
      } catch {
        throw error;
      }
    }
  }

  function dispose() {
    disposed = true;
    stopPolling();
  }

  return {
    publish,
    restore,
    recover,
    retry: retryFailed,
    getPending: () => recovery.getPending(),
    stop: dispose,
  };
}
