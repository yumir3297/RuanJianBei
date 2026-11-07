import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { resolve, relative } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));

async function snapshot(app) {
  const result = new Map();
  const visit = async (dir) => {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) await visit(path);
      else result.set(relative(resolve(root, "dist", app), path), createHash("sha256").update(await readFile(path)).digest("hex"));
    }
  };
  await visit(resolve(root, "dist", app));
  return result;
}

function build(app) {
  const result = spawnSync("npm", ["run", `build:${app}`], { cwd: root, stdio: "inherit" });
  assert.equal(result.status, 0, `${app} build failed`);
}

const beforeAdmin = await snapshot("admin");
build("tourist");
assert.deepEqual(await snapshot("admin"), beforeAdmin, "tourist build changed admin output");

const beforeTourist = await snapshot("tourist");
build("admin");
assert.deepEqual(await snapshot("tourist"), beforeTourist, "admin build changed tourist output");

const beforeLegacyAdmin = await snapshot("admin");
const beforeLegacyTourist = await snapshot("tourist");
build("legacy");
assert.deepEqual(await snapshot("admin"), beforeLegacyAdmin, "legacy build changed admin output");
assert.deepEqual(await snapshot("tourist"), beforeLegacyTourist, "legacy build changed tourist output");
console.log("Build isolation OK: each app build and the legacy build preserve the other outputs.");
