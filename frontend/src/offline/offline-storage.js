/**
 * 离线伴游本地快照存储。
 *
 * 优先级：IndexedDB → localStorage → 内存。
 * 任何一层失败都不阻塞游戏/地图/求助，只是如实返回降级状态。
 * 只存非敏感数据：分数、离线页版本、白名单返回路径。
 */

import { normalizeReturnTarget } from "./connectivity.js";

export const SNAPSHOT_SCHEMA_VERSION = 1;
export const STORAGE_DB_NAME = "a5-offline-companion";
export const STORAGE_DB_VERSION = 1;
export const STORAGE_STORE_NAME = "snapshot";
export const STORAGE_RECORD_KEY = "current";
export const STORAGE_FALLBACK_KEY = "a5-offline-snapshot";

function safeUuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function toFiniteScore(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) return 0;
  return Math.min(Math.floor(number), 9_999_999);
}

export function createEmptySnapshot(appVersion = "0.0.0", now = Date.now()) {
  return {
    schemaVersion: SNAPSHOT_SCHEMA_VERSION,
    appVersion: String(appVersion || "0.0.0"),
    sessionId: safeUuid(),
    bestScore: 0,
    lastScore: 0,
    returnTarget: "/tourist",
    returnConsumedAt: null,
    mapVersion: "",
    contactsVersion: "",
    updatedAt: new Date(now).toISOString(),
  };
}

/** 校验并归一化任意来源的快照；未知字段一律丢弃。 */
export function sanitizeSnapshot(raw, fallback) {
  const base = fallback || createEmptySnapshot();
  if (!raw || typeof raw !== "object") return { ...base };
  const updatedAt =
    typeof raw.updatedAt === "string" && !Number.isNaN(Date.parse(raw.updatedAt))
      ? raw.updatedAt
      : base.updatedAt;
  return {
    schemaVersion: SNAPSHOT_SCHEMA_VERSION,
    appVersion: typeof raw.appVersion === "string" ? raw.appVersion.slice(0, 32) : base.appVersion,
    sessionId: typeof raw.sessionId === "string" && raw.sessionId.length <= 64 ? raw.sessionId : base.sessionId,
    bestScore: toFiniteScore(raw.bestScore),
    lastScore: toFiniteScore(raw.lastScore),
    returnTarget: normalizeReturnTarget(raw.returnTarget),
    returnConsumedAt:
      typeof raw.returnConsumedAt === "string" && !Number.isNaN(Date.parse(raw.returnConsumedAt))
        ? raw.returnConsumedAt
        : null,
    mapVersion: typeof raw.mapVersion === "string" ? raw.mapVersion.slice(0, 32) : "",
    contactsVersion: typeof raw.contactsVersion === "string" ? raw.contactsVersion.slice(0, 32) : "",
    updatedAt,
  };
}

function openIndexedDb(indexedDbImpl) {
  return new Promise((resolve, reject) => {
    if (!indexedDbImpl) {
      reject(new Error("indexeddb-unavailable"));
      return;
    }
    let request;
    try {
      request = indexedDbImpl.open(STORAGE_DB_NAME, STORAGE_DB_VERSION);
    } catch (error) {
      reject(error);
      return;
    }
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORAGE_STORE_NAME)) {
        db.createObjectStore(STORAGE_STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("indexeddb-open-failed"));
    request.onblocked = () => reject(new Error("indexeddb-blocked"));
  });
}

function idbGet(db, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORAGE_STORE_NAME, "readonly");
    const request = tx.objectStore(STORAGE_STORE_NAME).get(key);
    request.onsuccess = () => resolve(request.result ?? null);
    request.onerror = () => reject(request.error || new Error("indexeddb-read-failed"));
  });
}

function idbPut(db, key, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORAGE_STORE_NAME, "readwrite");
    tx.objectStore(STORAGE_STORE_NAME).put(value, key);
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error || new Error("indexeddb-write-failed"));
    tx.onabort = () => reject(tx.error || new Error("indexeddb-write-aborted"));
  });
}

export function createOfflineStorage(options = {}) {
  const now = options.now || (() => Date.now());
  const appVersion = options.appVersion || "0.0.0";
  const indexedDbImpl =
    options.indexedDbImpl !== undefined
      ? options.indexedDbImpl
      : typeof indexedDB !== "undefined"
        ? indexedDB
        : null;
  const localStorageImpl =
    options.localStorageImpl !== undefined
      ? options.localStorageImpl
      : typeof localStorage !== "undefined"
        ? localStorage
        : null;

  let mode = "memory";
  let dbPromise = null;
  let memorySnapshot = null;
  let lastError = "";
  let initialized = false;

  function reportError(error) {
    lastError = String(error?.message || error || "storage-error");
  }

  async function ensureBackend() {
    if (initialized) return;
    initialized = true;
    try {
      const db = await openIndexedDb(indexedDbImpl);
      dbPromise = Promise.resolve(db);
      mode = "indexeddb";
      return;
    } catch (error) {
      reportError(error);
    }
    if (localStorageImpl) mode = "localstorage";
  }

  function readFallback() {
    if (!localStorageImpl) return null;
    try {
      const raw = localStorageImpl.getItem(STORAGE_FALLBACK_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      reportError(error);
      return null;
    }
  }

  function writeFallback(snapshot) {
    if (!localStorageImpl) return false;
    try {
      localStorageImpl.setItem(STORAGE_FALLBACK_KEY, JSON.stringify(snapshot));
      return true;
    } catch (error) {
      reportError(error);
      return false;
    }
  }

  async function load() {
    await ensureBackend();
    const empty = createEmptySnapshot(appVersion, now());
    let raw = null;
    if (mode === "indexeddb") {
      try {
        const db = await dbPromise;
        raw = await idbGet(db, STORAGE_RECORD_KEY);
      } catch (error) {
        reportError(error);
        mode = localStorageImpl ? "localstorage" : "memory";
        raw = readFallback();
      }
    } else if (mode === "localstorage") {
      raw = readFallback();
    }
    const snapshot = sanitizeSnapshot(raw, empty);
    memorySnapshot = snapshot;
    return snapshot;
  }

  async function save(patch) {
    const base = memorySnapshot || (await load());
    const merged = sanitizeSnapshot(
      { ...base, ...patch, updatedAt: new Date(now()).toISOString() },
      base,
    );
    memorySnapshot = merged;

    if (mode === "indexeddb") {
      try {
        const db = await dbPromise;
        await idbPut(db, STORAGE_RECORD_KEY, merged);
        return { ok: true, mode, snapshot: merged };
      } catch (error) {
        reportError(error);
        mode = localStorageImpl ? "localstorage" : "memory";
      }
    }
    if (mode === "localstorage" && writeFallback(merged)) {
      return { ok: true, mode, snapshot: merged };
    }
    mode = "memory";
    return { ok: false, mode, snapshot: merged, error: lastError || "storage-unavailable" };
  }

  return {
    load,
    save,
    getMode: () => mode,
  };
}
