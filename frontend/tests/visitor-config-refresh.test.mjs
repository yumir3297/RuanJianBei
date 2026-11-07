import assert from "node:assert/strict";
import test from "node:test";
import { createVisitorConfigRefresher } from "../src/utils/visitorConfigRefresh.js";

function createFakeClock() {
  let nextId = 0;
  const intervals = new Map();
  return {
    intervals,
    setInterval(callback, delay) {
      const id = ++nextId;
      intervals.set(id, { callback, delay });
      return id;
    },
    clearInterval(id) { intervals.delete(id); },
    tick() { for (const { callback } of [...intervals.values()]) callback(); },
  };
}

const validConfig = {
  avatar: { model_key: "monk", voice_type: "calm-female" },
  display: { welcome_text: "新欢迎语" },
};

test("visible pages poll every 60 seconds and pause while hidden", async () => {
  const clock = createFakeClock();
  let visible = true;
  let requests = 0;
  const applied = [];
  const refresher = createVisitorConfigRefresher({
    clock,
    isVisible: () => visible,
    isIdle: () => true,
    fetchConfig: async () => { requests += 1; return validConfig; },
    onApply: (config) => applied.push(config),
  });
  refresher.start();
  await Promise.resolve();
  assert.equal(requests, 1);
  assert.deepEqual([...clock.intervals.values()].map((item) => item.delay), [60000]);
  visible = false;
  refresher.setVisible(false);
  assert.equal(clock.intervals.size, 0);
  clock.tick();
  assert.equal(requests, 1);
  visible = true;
  refresher.setVisible(true);
  await Promise.resolve();
  assert.equal(requests, 2);
  clock.tick();
  await Promise.resolve();
  assert.equal(requests, 3);
  assert.equal(applied.length, 3);
  refresher.dispose();
});

test("refresh is single-flight and a late response is ignored after dispose", async () => {
  const clock = createFakeClock();
  let resolveFetch;
  let requests = 0;
  const applied = [];
  const refresher = createVisitorConfigRefresher({
    clock,
    isVisible: () => true,
    isIdle: () => true,
    fetchConfig: () => { requests += 1; return new Promise((resolve) => { resolveFetch = resolve; }); },
    onApply: (config) => applied.push(config),
  });
  const first = refresher.refresh();
  const second = refresher.refresh();
  assert.equal(requests, 1);
  refresher.dispose();
  resolveFetch(validConfig);
  await Promise.all([first, second]);
  assert.deepEqual(applied, []);
  assert.equal(clock.intervals.size, 0);
});

test("a busy page applies the latest pending config immediately when it becomes idle", async () => {
  const clock = createFakeClock();
  let idle = false;
  const applied = [];
  const refresher = createVisitorConfigRefresher({
    clock,
    isVisible: () => true,
    isIdle: () => idle,
    fetchConfig: async () => validConfig,
    onApply: (config) => applied.push(config),
  });
  await refresher.refresh();
  assert.deepEqual(applied, []);
  idle = true;
  refresher.flushPending();
  assert.deepEqual(applied, [validConfig]);
  refresher.dispose();
});

test("failed refresh preserves the latest successfully applied config", async () => {
  const clock = createFakeClock();
  const applied = [];
  let fail = false;
  const refresher = createVisitorConfigRefresher({
    clock,
    isVisible: () => true,
    isIdle: () => true,
    fetchConfig: async () => { if (fail) throw new Error("offline"); return validConfig; },
    onApply: (config) => applied.push(config),
  });
  await refresher.refresh();
  fail = true;
  await refresher.refresh();
  assert.deepEqual(applied, [validConfig]);
  refresher.dispose();
});

test("visitor config exits initial loading after the public endpoint fails", async () => {
  const { createRenderer, nextTick } = await import("vue");
  const { createServer } = await import("vite");
  const path = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const server = await createServer({
    configFile: false,
    root: frontendRoot,
    logLevel: "silent",
    server: { middlewareMode: true },
    appType: "custom",
  });
  const renderer = createRenderer({
    createElement: (type) => ({ type, children: [] }),
    createText: (text) => ({ text }),
    createComment: (text) => ({ text }),
    setText: (node, text) => { node.text = text; },
    setElementText: (node, text) => { node.text = text; },
    patchProp: () => {},
    insert: (node, parent) => { parent.children.push(node); },
    remove: () => {},
    parentNode: () => null,
    nextSibling: () => null,
  });
  let config;
  const { useVisitorConfig } = await server.ssrLoadModule("/src/composables/useVisitorConfig.js");
  const app = renderer.createApp({
    setup() {
      config = useVisitorConfig({ fetchConfig: async () => { throw new Error("offline"); } });
      return () => null;
    },
  });
  try {
    app.mount({ children: [] });
    await nextTick();
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(config.loading.value, false);
  } finally {
    app.unmount();
    await server.close();
  }
});
