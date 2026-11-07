import test from "node:test";
import assert from "node:assert/strict";
import { access, readdir, rm, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const stage = (target) => resolve(root, `.public-${target}`);

async function fileExists(path) {
  try { await access(path); return true; } catch { return false; }
}

test("public asset staging excludes tester pages and adds the worklet only for tourists", async () => {
  try {
    const run = (target) => {
      const result = spawnSync(process.execPath, ["scripts/prepare-public.mjs", target], { cwd: root, encoding: "utf8" });
      assert.equal(result.status, 0, result.stderr || result.stdout);
    };
    run("tourist");
    const touristStage = stage("tourist");
    for (const file of ["models/hanfu.vrm", "motions/双手挥手欢迎.glb", "assets/bg-scenic.png", "assets/slides/灵山大佛.png", "recorder-worklet.js", "favicon.svg"]) {
      assert.ok(await fileExists(resolve(touristStage, file)), `missing tourist asset ${file}`);
    }
    for (const file of ["motion-tester.html", "map-tester.html"]) assert.ok(!(await fileExists(resolve(touristStage, file))), `tester leaked: ${file}`);
    run("admin");
    const adminStage = stage("admin");
    for (const file of ["models/hanfu.vrm", "motions/双手挥手欢迎.glb", "assets/bg-scenic.png", "favicon.svg"]) {
      assert.ok(await fileExists(resolve(adminStage, file)), `missing admin asset ${file}`);
    }
    for (const file of ["motion-tester.html", "map-tester.html", "recorder-worklet.js"]) {
      assert.ok(!(await fileExists(resolve(adminStage, file))), `admin leaked ${file}`);
    }
  } finally {
    await rm(stage("tourist"), { recursive: true, force: true });
    await rm(stage("admin"), { recursive: true, force: true });
  }
});
