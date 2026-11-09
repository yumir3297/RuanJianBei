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
