import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createServer } from "vite";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function withViteModule(id, run) {
  const server = await createServer({
    configFile: false,
    root: frontendRoot,
    logLevel: "silent",
    server: { middlewareMode: true },
    appType: "custom",
  });
  try {
    const module = await server.ssrLoadModule(id);
    return await run(module, server);
  } finally {
    await server.close();
  }
}

 test("tourist Axios never reads or forwards an admin token", async () => {
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  let storageReads = 0;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem() { storageReads += 1; return "administrator-token"; },
      removeItem() { storageReads += 1; },
    },
  });
  try {
    await withViteModule("/src/api/http.js", async ({ default: http }) => {
      let request;
      http.defaults.adapter = async (config) => {
        request = config;
        return { data: {}, status: 200, statusText: "OK", headers: {}, config };
      };
      await http.get("/visitor-config");
      assert.equal(request.headers.get("Authorization"), undefined);
      assert.equal(storageReads, 0);
    });
  } finally {
    if (previousStorage) Object.defineProperty(globalThis, "localStorage", previousStorage);
    else delete globalThis.localStorage;
  }
});

test("shared transport creates an identity-free API client", async () => {
  await withViteModule("/src/api/transport.js", async ({ createHttpClient }) => {
    const client = createHttpClient("https://guide.example");
    assert.equal(client.defaults.baseURL, "https://guide.example/api");
    assert.equal(client.defaults.timeout, 10000);
    assert.equal(client.interceptors.request.handlers.length, 0);
    assert.equal(client.interceptors.response.handlers.length, 0);
  });
});

test("tourist SSE fetch sends no admin bearer header", async () => {
  const previousFetch = globalThis.fetch;
  let requestHeaders;
  globalThis.fetch = async (_url, options) => {
    requestHeaders = options.headers;
    return { ok: false, status: 401, body: null, text: async () => "{}" };
  };
  try {
    await withViteModule("/src/composables/useSSEStream.js", async ({ useSSEStream }) => {
      await assert.rejects(useSSEStream().postStream("/api/chat/stream", { message: "test" }));
      assert.deepEqual(requestHeaders, {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      });
      assert.equal(Object.keys(requestHeaders).some((name) => name.toLowerCase() === "authorization"), false);
    });
  } finally {
    globalThis.fetch = previousFetch;
  }
});
