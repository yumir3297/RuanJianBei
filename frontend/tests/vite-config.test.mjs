import test from "node:test";
import assert from "node:assert/strict";
import { makeAppConfig } from "../vite.shared.js";

test("tourist and admin Vite servers use isolated optimize dependency caches", () => {
  const tourist = makeAppConfig({ app: "tourist", port: 5173 });
  const admin = makeAppConfig({ app: "admin", port: 5174 });

  assert.ok(tourist.cacheDir, "tourist Vite config must name a cache directory");
  assert.ok(admin.cacheDir, "admin Vite config must name a cache directory");
  assert.notEqual(tourist.cacheDir, admin.cacheDir);
  assert.equal(tourist.build.emptyOutDir, true, "tourist rebuild must remove stale assets from its own output");
  assert.equal(admin.build.emptyOutDir, true, "admin rebuild must remove stale assets from its own output");
  assert.notEqual(tourist.build.outDir, admin.build.outDir, "cleaning one app must not clean the other app");
});
