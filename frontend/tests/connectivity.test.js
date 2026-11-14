import test from "node:test";
import assert from "node:assert/strict";

import {
  CONNECTIVITY_STATES as S,
  createConnectivityMonitor,
  evaluateHealthResponse,
  initialConnectivitySnapshot,
  normalizeReturnTarget,
  reduceConnectivity,
} from "../src/offline/connectivity.js";

const ok = (time) => ({ type: "probe-ok", time });
const fail = (time) => ({ type: "probe-fail", time });

function run(events, options) {
  let snapshot = initialConnectivitySnapshot(0);
  for (const event of events) snapshot = reduceConnectivity(snapshot, event, options);
  return snapshot;
}

test("首次有效成功立即进入 ONLINE", () => {
  assert.equal(run([ok(1000)]).state, S.ONLINE);
});

test("NET-01 单次超时只进入 SUSPECT，不切换", () => {
  const snapshot = run([ok(0), fail(5000)]);
  assert.equal(snapshot.state, S.SUSPECT);
});

test("NET-02 连续失败 >=3 次且持续 >=15s 才进入 DEGRADED", () => {
  assert.equal(run([ok(0), fail(5000), fail(10000), fail(15000)]).state, S.SUSPECT);
  const degraded = run([ok(0), fail(5000), fail(10000), fail(15000), fail(20000)]);
  assert.equal(degraded.state, S.DEGRADED);
});

test("NET-03 navigator.onLine=true 但后端不可达也能进入 DEGRADED", () => {
  const snapshot = run([ok(0), fail(5000), fail(10000), fail(15000), fail(20000), fail(25000)]);
  assert.equal(snapshot.state, S.DEGRADED);
  assert.equal(snapshot.everOnline, true);
});

test("NET-04 恢复期间偶发一次成功不显示恢复", () => {
  const afterOutage = run([ok(0), fail(5000), fail(10000), fail(15000), fail(20000)]);
  const once = reduceConnectivity(afterOutage, ok(25000));
  assert.equal(once.state, S.RECOVERING);
});

test("NET-05 连续两次成功且间隔 >=3s 才回到 ONLINE", () => {
  const afterOutage = run([ok(0), fail(5000), fail(10000), fail(15000), fail(20000)]);
  const first = reduceConnectivity(afterOutage, ok(25000));
  assert.equal(first.state, S.RECOVERING);
  const tooSoon = reduceConnectivity(first, ok(26000));
  assert.equal(tooSoon.state, S.RECOVERING);
  const confirmed = reduceConnectivity(first, ok(28000));
  assert.equal(confirmed.state, S.ONLINE);
});

test("恢复成功后再次失败会重置恢复计数", () => {
  const afterOutage = run([ok(0), fail(5000), fail(10000), fail(15000), fail(20000)]);
  const first = reduceConnectivity(afterOutage, ok(25000));
  const broken = reduceConnectivity(first, fail(26000));
  assert.equal(broken.successCount, 0);
  assert.equal(broken.state, S.SUSPECT);
});

test("reset 事件回到 UNKNOWN", () => {
  const online = run([ok(0)]);
  assert.equal(reduceConnectivity(online, { type: "reset", time: 1 }).state, S.UNKNOWN);
});

test("NET-07 /health 返回 HTML 或错误 JSON 时视为失败", async () => {
  const html = new Response("<html>login</html>", {
    status: 200,
    headers: { "Content-Type": "text/html" },
  });
  assert.equal((await evaluateHealthResponse(html)).ok, false);

  const wrongJson = new Response(JSON.stringify({ status: "ready" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
  assert.equal((await evaluateHealthResponse(wrongJson)).ok, false);

  const okJson = new Response(JSON.stringify({ status: "ok", service: "x" }), {
    status: 200,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
  assert.equal((await evaluateHealthResponse(okJson)).ok, true);
});

test("NET-08 并发 probeNow 只发一个请求，stop 后迟到响应不覆盖状态", async () => {
  let resolveFetch;
  let calls = 0;
  const fetchImpl = () => {
    calls += 1;
    return new Promise((resolve) => {
      resolveFetch = resolve;
    });
  };
  const monitor = createConnectivityMonitor({ fetchImpl, intervalMs: 100000 });
  monitor.start();
  const a = monitor.probeNow();
  const b = monitor.probeNow();
  assert.equal(a, b);
  assert.equal(calls, 1);

  monitor.stop();
  resolveFetch(
    new Response(JSON.stringify({ status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  await a;
  assert.equal(monitor.getState(), S.UNKNOWN);
});

test("返回地址白名单只允许 /tourist 与已知工具", () => {
  assert.equal(normalizeReturnTarget("/tourist"), "/tourist");
  assert.equal(normalizeReturnTarget("/tourist?tool=map"), "/tourist?tool=map");
  assert.equal(normalizeReturnTarget("/tourist?tool=admin"), "/tourist");
  assert.equal(normalizeReturnTarget("https://evil.example/tourist"), "/tourist");
  assert.equal(normalizeReturnTarget("//evil.example"), "/tourist");
  assert.equal(normalizeReturnTarget("/admin/dashboard"), "/tourist");
  assert.equal(normalizeReturnTarget(null), "/tourist");
});
