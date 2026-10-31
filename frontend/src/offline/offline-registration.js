/**
 * Service Worker 注册与“离线包是否真的就绪”的校验。
 *
 * 只有全部预缓存资源都能在 Cache Storage 中查到，才返回 ready: true；
 * 注册成功本身不算就绪（首次缓存可能失败）。
 */

export const SW_URL = "/sw.js";
export const SW_SCOPE = "/";
export const CACHE_PREFIX = "a5-offline-";
export const PRECACHE_MANIFEST_URL = "/offline-precache-manifest.json";

export function serviceWorkerSupported() {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return false;
  if (typeof window !== "undefined" && !window.isSecureContext) return false;
  return true;
}

function withTimeout(promise, timeoutMs, message) {
  if (!timeoutMs) return promise;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function isValidManifest(manifest) {
  return Boolean(manifest && Array.isArray(manifest.urls) && typeof manifest.buildId === "string");
}

async function readCachedManifest() {
  if (typeof caches === "undefined") return null;
  const cached = await caches.match(PRECACHE_MANIFEST_URL, { ignoreSearch: true });
  if (!cached) return null;
  const manifest = await cached.json();
  return isValidManifest(manifest) ? manifest : null;
}

async function fetchManifest(fetchImpl, timeoutMs) {
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const response = await fetchImpl(PRECACHE_MANIFEST_URL, {
      cache: "no-store",
      signal: controller?.signal,
    });
    if (!response.ok) throw new Error(`manifest-http-${response.status}`);
    const manifest = await response.json();
    if (!isValidManifest(manifest)) throw new Error("manifest-invalid");
    return manifest;
  } catch (error) {
    // 断网时（页面未被 SW 接管的情况）退回 Cache Storage 里的清单。
    const cached = await readCachedManifest().catch(() => null);
    if (cached) return cached;
    throw error;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function waitForActivation(registration, timeoutMs) {
  if (registration.active) return Promise.resolve(registration.active);
  const worker = registration.installing || registration.waiting;
  if (!worker) return Promise.reject(new Error("service-worker-missing"));

  return withTimeout(
    new Promise((resolve) => {
      const onState = () => {
        if (worker.state === "activated") {
          worker.removeEventListener("statechange", onState);
          resolve(worker);
        } else if (worker.state === "redundant") {
          worker.removeEventListener("statechange", onState);
        }
      };
      worker.addEventListener("statechange", onState);
      if (worker.state === "installed") worker.postMessage({ type: "SKIP_WAITING" });
      onState();
    }),
    timeoutMs,
    "service-worker-activation-timeout",
  );
}

export async function inspectOfflinePackage(options = {}) {
  const fetchImpl = options.fetchImpl || fetch;
  const timeoutMs = options.timeoutMs || 8000;
  if (typeof caches === "undefined") {
    return { supported: false, ready: false, error: "cache-api-unavailable" };
  }
  let manifest;
  try {
    manifest = await fetchManifest(fetchImpl, timeoutMs);
  } catch (error) {
    return { supported: false, ready: false, error: String(error?.message || error) };
  }
  try {
    const cache = await caches.open(`${CACHE_PREFIX}${manifest.buildId}`);
    const requests = await cache.keys();
    const available = new Set(requests.map((request) => new URL(request.url).pathname));
    const missing = manifest.urls.filter((url) => !available.has(url));
    return {
      supported: true,
      ready: missing.length === 0,
      buildId: manifest.buildId,
      version: manifest.version || "",
      urls: manifest.urls,
      missing,
      error: missing.length ? "precache-incomplete" : "",
    };
  } catch (error) {
    return { supported: true, ready: false, error: String(error?.message || error) };
  }
}

/**
 * 注册 SW 并验证预缓存完整性。可重复调用（register 幂等）。
 * @returns {{supported:boolean, ready:boolean, error?:string, buildId?:string, missing?:string[]}}
 */
export async function prepareOfflinePackage(options = {}) {
  const fetchImpl = options.fetchImpl || fetch;
  const timeoutMs = options.activationTimeoutMs || 20000;

  if (!serviceWorkerSupported()) {
    return { supported: false, ready: false, error: "service-worker-unsupported" };
  }

  try {
    const registration = await navigator.serviceWorker.register(SW_URL, {
      scope: SW_SCOPE,
      updateViaCache: "none",
    });
    await waitForActivation(registration, timeoutMs);
    // 等待页面被 SW 接管，确保后续导航与静态资源都走缓存策略。
    if (!navigator.serviceWorker.controller) {
      await withTimeout(
        new Promise((resolve) => {
          navigator.serviceWorker.addEventListener("controllerchange", resolve, { once: true });
          setTimeout(resolve, 3000);
        }),
        3500,
        "service-worker-controller-timeout",
      ).catch(() => {});
    }
  } catch (error) {
    // 注册失败（例如离线且没有旧 SW）时仍然核对已有缓存，给出准确状态。
    const inspected = await inspectOfflinePackage({ fetchImpl }).catch(() => null);
    return {
      ...(inspected || { supported: true, ready: false }),
      supported: true,
      error: String(error?.message || error),
    };
  }

  return inspectOfflinePackage({ fetchImpl });
}
