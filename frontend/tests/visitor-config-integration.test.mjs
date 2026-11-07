import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createServer } from "vite";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("tourist config API calls the public combined endpoint", async () => {
  const server = await createServer({
    configFile: false,
    root: frontendRoot,
    logLevel: "silent",
    server: { middlewareMode: true },
    appType: "custom",
  });
  try {
    const { default: visitorHttp } = await server.ssrLoadModule("/src/api/http.js");
    const { fetchVisitorConfig } = await server.ssrLoadModule("/src/api/visitorConfig.js");
    let requestedUrl;
    const responseConfig = { avatar: { model_key: "hanfu", voice_type: "gentle-female" }, display: {} };
    visitorHttp.defaults.adapter = async (config) => {
      requestedUrl = config.url;
      return { data: responseConfig, status: 200, statusText: "OK", headers: {}, config };
    };
    assert.deepEqual(await fetchVisitorConfig(), responseConfig);
    assert.equal(requestedUrl, "/visitor-config");
  } finally {
    await server.close();
  }
});

test("reapplying the same visitor avatar config does not replace the avatar model state", async () => {
  const { createRenderer, nextTick, watch } = await import("vue");
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
  let visitor;
  const { useVisitorConfig } = await server.ssrLoadModule("/src/composables/useVisitorConfig.js");
  let requests = 0;
  const config = {
    avatar: { model_key: "monk", voice_type: "deep-male" },
    display: { tourist_background: { asset_url: null }, welcome_text: "欢迎" },
  };
  const app = renderer.createApp({
    setup() {
      visitor = useVisitorConfig({ fetchConfig: async () => { requests += 1; return structuredClone(config); } });
      return () => null;
    },
  });
  try {
    app.mount({ children: [] });
    await new Promise((resolve) => setImmediate(resolve));
    await visitor.refresh();
    await nextTick();
    const appliedAvatar = visitor.avatar.value;
    let changes = 0;
    const stopWatch = watch(visitor.avatar, () => { changes += 1; });
    await visitor.refresh();
    await nextTick();
    assert.ok(requests >= 2);
    assert.equal(visitor.avatar.value, appliedAvatar);
    assert.equal(changes, 0);
    stopWatch();
  } finally {
    app.unmount();
    await server.close();
  }
});
