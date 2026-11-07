import assert from "node:assert/strict";
import { readdir, readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));

async function listFiles(dir) {
  const output = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = resolve(dir, entry.name);
    output.push(...(entry.isDirectory() ? await listFiles(full) : [full]));
  }
  return output;
}

async function checkApp(app) {
  const outputDir = resolve(frontendRoot, "dist", app);
  const manifestPath = resolve(outputDir, ".vite/manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  const entry = Object.entries(manifest).find(([key, value]) => key === "index.html" && value.isEntry);
  assert.ok(entry, `${app} HTML entry missing from manifest`);
  const seen = new Set();
  const visit = (key) => {
    if (seen.has(key)) return;
    const item = manifest[key];
    assert.ok(item, `${app} manifest reference is missing: ${key}`);
    seen.add(key);
    for (const dependency of [...(item.imports || []), ...(item.dynamicImports || [])]) visit(dependency);
  };
  visit(entry[0]);

  for (const item of Object.values(manifest)) {
    if (!item.file) continue;
    await stat(resolve(outputDir, item.file));
    for (const asset of item.assets || []) await stat(resolve(outputDir, asset));
  }
  const files = await listFiles(outputDir);
  assert.ok(!files.some((file) => /(?:motion|map)-tester\.html$/i.test(file)), `${app} includes a tester page`);
  if (app === "admin") {
    await stat(resolve(outputDir, "models/hanfu.vrm"));
    await assert.rejects(stat(resolve(outputDir, "recorder-worklet.js")));
  } else {
    await stat(resolve(outputDir, "recorder-worklet.js"));
    await stat(resolve(outputDir, "models/hanfu.vrm"));
    await stat(resolve(outputDir, "motions/双手挥手欢迎.glb"));
  }
  return { outputDir, manifestPath, files, seen: [...seen] };
}

const tourist = await checkApp("tourist");
const admin = await checkApp("admin");
assert.notEqual(tourist.outputDir, admin.outputDir);
console.log(`Build boundaries OK: tourist ${tourist.seen.length} manifest nodes; admin ${admin.seen.length}; outputs are self-contained.`);
