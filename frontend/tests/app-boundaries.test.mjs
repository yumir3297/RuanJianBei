import test from "node:test";
import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function importsFrom(source) {
  const imports = [];
  for (const match of source.matchAll(/(?:from\s*|import\s*\()\s*["']([^"']+)["']/g)) {
    if (match[1].startsWith(".")) imports.push(match[1]);
  }
  return imports;
}

async function reachableFiles(entry) {
  const visited = new Set();
  async function resolveLocal(target) {
    const options = extname(target)
      ? [target]
      : [target, `${target}.js`, `${target}.vue`, `${target}.css`, `${target}.json`, join(target, "index.js")];
    for (const option of options) {
      try { await access(option); return option; } catch { /* try Vite's next extension */ }
    }
    throw new Error(`unresolved local import: ${target}`);
  }
  const visit = async (file) => {
    const absolute = await resolveLocal(resolve(frontendRoot, file));
    if (visited.has(absolute)) return;
    visited.add(absolute);
    const source = await readFile(absolute, "utf8");
    const script = extname(absolute) === ".vue"
      ? [...source.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]).join("\n")
      : source;
    for (const specifier of importsFrom(script)) {
      const target = resolve(dirname(absolute), specifier);
      await visit(target);
    }
  };
  await visit(entry);
  return [...visited].map((file) => file.slice(frontendRoot.length + 1));
}

test("tourist application graph excludes admin auth, APIs, charts, and Element Plus", async () => {
  const files = await reachableFiles("apps/tourist/main.js");
  assert.ok(files.includes("src/views/tourist/ChatView.vue"));
  assert.ok(files.includes("src/components/ThreeAvatar.vue"));
  assert.ok(!files.some((file) => /src\/(?:stores\/(?:auth|admin)\.js|api\/admin[^/]*\.js|views\/admin\/)/.test(file)), files.join("\n"));
  const source = await Promise.all(files.filter((file) => /\.(js|vue)$/.test(file)).map((file) => readFile(join(frontendRoot, file), "utf8")));
  assert.ok(!source.some((text) => /(?:from\s*|import\s*\()["'](?:element-plus|echarts)(?:\/|["'])/.test(text)));
});

test("admin graph retains avatar preview and excludes tourist conversation", async () => {
  const files = await reachableFiles("apps/admin/main.js");
  assert.ok(files.includes("src/views/admin/AvatarConfig.vue"));
  assert.ok(files.includes("src/components/ThreeAvatar.vue"));
  assert.ok(files.includes("src/stores/auth.js"));
  assert.ok(!files.includes("src/views/tourist/ChatView.vue"));
  assert.ok(!files.includes("src/router/index.js"));
});
