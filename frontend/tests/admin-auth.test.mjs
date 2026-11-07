import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createPinia, setActivePinia } from "pinia";
import { createServer } from "vite";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function withViteModules(run) {
  const server = await createServer({
    configFile: false,
    root: frontendRoot,
    logLevel: "silent",
    server: { middlewareMode: true },
    appType: "custom",
  });
  try {
    return await run(server);
  } finally {
    await server.close();
  }
}

test("a 401 clears the admin Pinia state and shared token memory", async () => {
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  const storage = new Map([["a5-admin-auth", "old-token"]]);
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
  });
  try {
    await withViteModules(async (server) => {
      const authModule = await server.ssrLoadModule("/src/utils/adminAuthStorage.js");
      const { default: adminHttp } = await server.ssrLoadModule("/src/api/adminHttp.js");
      const { useAuthStore } = await server.ssrLoadModule("/src/stores/auth.js");
      setActivePinia(createPinia());
      const auth = useAuthStore();
      assert.equal(auth.isAuthenticated, true);
      adminHttp.defaults.adapter = async (config) => Promise.reject({
        config,
        response: { status: 401, data: { detail: "expired" } },
      });
      await assert.rejects(adminHttp.get("/admin/overview"));
      assert.equal(auth.token, null);
      assert.equal(auth.isAuthenticated, false);
      assert.equal(authModule.getAdminToken(), null);
      assert.equal(storage.has("a5-admin-auth"), false);
    });
  } finally {
    if (previousStorage) Object.defineProperty(globalThis, "localStorage", previousStorage);
    else delete globalThis.localStorage;
  }
});

test("admin login works in memory when browser storage is disabled", async () => {
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem() { throw new Error("storage disabled"); },
      setItem() { throw new Error("storage disabled"); },
      removeItem() { throw new Error("storage disabled"); },
    },
  });
  try {
    await withViteModules(async (server) => {
      const { default: adminHttp } = await server.ssrLoadModule("/src/api/adminHttp.js");
      const authModule = await server.ssrLoadModule("/src/utils/adminAuthStorage.js");
      const { useAuthStore } = await server.ssrLoadModule("/src/stores/auth.js");
      setActivePinia(createPinia());
      const auth = useAuthStore();
      let nextRequestAuthorization;
      adminHttp.defaults.adapter = async (config) => {
        if (config.url.endsWith("/auth/login")) {
          return { data: { token: "fresh-token" }, status: 200, statusText: "OK", headers: {}, config };
        }
        nextRequestAuthorization = config.headers.get("Authorization");
        return { data: {}, status: 200, statusText: "OK", headers: {}, config };
      };
      assert.equal(await auth.login("test-password"), true);
      assert.equal(auth.isAuthenticated, true);
      assert.equal(authModule.getAdminToken(), "fresh-token");
      await adminHttp.get("/admin/overview");
      assert.equal(nextRequestAuthorization, "Bearer fresh-token");
    });
  } finally {
    if (previousStorage) Object.defineProperty(globalThis, "localStorage", previousStorage);
    else delete globalThis.localStorage;
  }
});
