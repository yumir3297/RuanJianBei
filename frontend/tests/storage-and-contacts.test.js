import test from "node:test";
import assert from "node:assert/strict";

import {
  SNAPSHOT_SCHEMA_VERSION,
  STORAGE_FALLBACK_KEY,
  createEmptySnapshot,
  createOfflineStorage,
  sanitizeSnapshot,
} from "../src/offline/offline-storage.js";
import { isDialable, sanitizeContacts } from "../src/offline/offline-help.js";

function createMemoryLocalStorage() {
  const map = new Map();
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
  };
}

test("快照 schema 会丢弃未知字段并归一化分数", () => {
  const snapshot = sanitizeSnapshot({
    schemaVersion: 99,
    appVersion: "x".repeat(100),
    bestScore: -5,
    lastScore: 12.9,
    returnTarget: "/admin/dashboard",
    chatHistory: ["敏感内容"],
    updatedAt: "not-a-date",
  });
  assert.equal(snapshot.schemaVersion, SNAPSHOT_SCHEMA_VERSION);
  assert.equal(snapshot.bestScore, 0);
  assert.equal(snapshot.lastScore, 12);
  assert.equal(snapshot.returnTarget, "/tourist");
  assert.equal(snapshot.appVersion.length, 32);
  assert.equal(Object.hasOwn(snapshot, "chatHistory"), false);
});

test("空输入也能得到合法快照", () => {
  const snapshot = sanitizeSnapshot(null, createEmptySnapshot("1.0.0", Date.parse("2026-10-31T00:00:00Z")));
  assert.deepEqual(Object.keys(snapshot).sort(), [
    "appVersion",
    "bestScore",
    "contactsVersion",
    "lastScore",
    "mapVersion",
    "returnConsumedAt",
    "returnTarget",
    "schemaVersion",
    "sessionId",
    "updatedAt",
  ]);
});

test("GAME-05 IndexedDB 不可用时降级到 localStorage 且可跨实例读取", async () => {
  const localStorageImpl = createMemoryLocalStorage();
  const first = createOfflineStorage({ indexedDbImpl: null, localStorageImpl, appVersion: "1.0.0" });
  const result = await first.save({ bestScore: 360, lastScore: 140, returnTarget: "/tourist?tool=map" });
  assert.equal(result.ok, true);
  assert.equal(result.mode, "localstorage");
  assert.ok(localStorageImpl.getItem(STORAGE_FALLBACK_KEY));

  const second = createOfflineStorage({ indexedDbImpl: null, localStorageImpl, appVersion: "1.0.0" });
  const loaded = await second.load();
  assert.equal(loaded.bestScore, 360);
  assert.equal(loaded.lastScore, 140);
  assert.equal(loaded.returnTarget, "/tourist?tool=map");
});

test("存储完全不可用时不抛出，标记为内存模式", async () => {
  const storage = createOfflineStorage({ indexedDbImpl: null, localStorageImpl: null });
  const result = await storage.save({ bestScore: 10 });
  assert.equal(result.ok, false);
  assert.equal(storage.getMode(), "memory");
  assert.equal(result.snapshot.bestScore, 10);
});

test("坏掉的 localStorage 内容不会让读取崩溃", async () => {
  const localStorageImpl = {
    getItem: () => "{not-json",
    setItem: () => {},
    removeItem: () => {},
  };
  const storage = createOfflineStorage({ indexedDbImpl: null, localStorageImpl });
  const snapshot = await storage.load();
  assert.equal(snapshot.bestScore, 0);
  assert.equal(snapshot.returnTarget, "/tourist");
});

test("SAFE-04 只有 verified 且 tel: 合规的条目才允许拨号", () => {
  assert.equal(
    isDialable({ status: "verified", phoneUri: "tel:051085688120" }),
    true,
  );
  assert.equal(isDialable({ status: "unverified", phoneUri: "tel:051085688120" }), false);
  assert.equal(isDialable({ status: "verified", phoneUri: "javascript:alert(1)" }), false);
  assert.equal(isDialable({ status: "verified", phoneUri: "tel:123;rm -rf" }), false);
});

test("通讯录会丢弃无号码条目并归一化未知状态", () => {
  const data = sanitizeContacts({
    regionName: "测试景区",
    status: "bogus",
    entries: [
      { id: "a", label: "急救", phoneDisplay: "120", phoneUri: "tel:120", status: "verified" },
      { id: "b", label: "空号码" },
      { id: "c", label: "奇怪状态", phoneDisplay: "123", status: "hacked" },
    ],
  });
  assert.equal(data.status, "unverified");
  assert.equal(data.entries.length, 2);
  assert.equal(data.entries[1].status, "unverified");
});
