/* eslint-env serviceworker */
/**
 * 离线伴游 Service Worker（构建期由 scripts/offline-sw-plugin.mjs 注入清单）。
 *
 * 原则：
 * - 只接管预缓存白名单内的同源 GET 请求，其余请求完全走原网络行为；
 * - /health 与 /api/** 永不读取 Cache API，避免读出伪造的旧 200；
 * - 新版必须完整缓存成功才会激活，激活后清理旧版本缓存。
 */

const BUILD_INFO = __OFFLINE_BUILD_INFO__;

const CACHE_PREFIX = "a5-offline-";
const CACHE_NAME = `${CACHE_PREFIX}${BUILD_INFO.buildId}`;
const OFFLINE_ENTRY = "/offline.html";
const PRECACHED = new Set(BUILD_INFO.urls);

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      // cache: 'reload' 绕过 HTTP 缓存，确保写入的是本次构建的真实产物。
      await cache.addAll(BUILD_INFO.urls.map((url) => new Request(url, { cache: "reload" })));
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

async function respondFromCache(request, options) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request, options);
  if (cached) return cached;
  try {
    return await fetch(request, { cache: "no-store" });
  } catch {
    return new Response("离线资源缺失，请联网后重新准备离线包。", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 健康探针与业务接口一律走网络，任何情况下都不返回缓存。
  if (url.pathname === "/health" || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    if (url.pathname === OFFLINE_ENTRY) {
      event.respondWith(respondFromCache(request, { ignoreSearch: true }));
    }
    // 其他导航请求不接管，保留主站原行为与 FastAPI 的 SPA 回落。
    return;
  }

  if (!PRECACHED.has(url.pathname)) return;
  event.respondWith(respondFromCache(request));
});
