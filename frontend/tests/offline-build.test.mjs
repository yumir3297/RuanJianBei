import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { offlineServiceWorkerPlugin } from "../scripts/offline-sw-plugin.mjs";

// Public data has stable URLs. Changes to it must create a new SW cache.
test("offline cache version changes when public data changes", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "offline-build-"));
  try {
    const pub = path.join(root, "public");
    const dist = path.join(root, "dist");
    mkdirSync(path.join(pub, "offline"), { recursive: true });
    mkdirSync(path.join(dist, "offline"), { recursive: true });
    const data = path.join(pub, "offline", "map.json");
    writeFileSync(data, '{"version":1}');
    writeFileSync(path.join(dist, "offline", "map.json"), "{}");
    writeFileSync(path.join(pub, "favicon.svg"), "<svg/>");
    const template = path.join(root, "sw.js");
    const html = path.join(root, "offline.html");
    writeFileSync(template, "const info = __OFFLINE_BUILD_INFO__;");
    writeFileSync(html, "<html></html>");
    const plugin = offlineServiceWorkerPlugin({ templatePath: template, offlineHtmlPath: html, publicDir: pub, distDir: dist, version: "1" });
    const bundle = { "offline-abc.js": { type: "chunk", isEntry: true, name: "offline", fileName: "offline-abc.js", code: "export {}", imports: [] } };
    const build = () => {
      const assets = {};
      plugin.generateBundle.call({ emitFile: (asset) => { assets[asset.fileName] = asset.source; }, info: () => {}, error: (message) => { throw new Error(message); } }, {}, bundle);
      return JSON.parse(assets["offline-precache-manifest.json"]).buildId;
    };
    const before = build();
    assert.equal(build(), before);
    writeFileSync(data, '{"version":2}');
    assert.notEqual(build(), before);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("offline static server rejects missing cache resources instead of serving the SPA", async () => {
  const { startStaticServer } = await import("../scripts/offline-test-server.mjs");
  const root = mkdtempSync(path.join(os.tmpdir(), "offline-server-"));
  writeFileSync(path.join(root, "index.html"), "<html>SPA</html>");
  const { server, origin } = await startStaticServer({ distDir: root });
  try {
    for (const resource of ["/offline/map/missing.svg", "/offline.html", "/sw.js", "/assets/missing.js"]) {
      assert.equal((await fetch(origin + resource)).status, 404, resource);
    }
    assert.equal((await fetch(origin + "/tourist")).status, 200);
    assert.equal((await (await fetch(origin + "/health")).json()).status, "ok");
  } finally {
    await new Promise((resolve) => server.close(resolve));
    rmSync(root, { recursive: true, force: true });
  }
});
