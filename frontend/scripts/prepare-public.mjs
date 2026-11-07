import { cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "public");
const target = process.argv[2];

if (!["tourist", "admin"].includes(target)) {
  throw new Error("usage: node scripts/prepare-public.mjs tourist|admin");
}

const output = resolve(root, `.public-${target}`);
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
for (const name of ["assets", "models", "motions", "favicon.svg"]) {
  await cp(resolve(source, name), resolve(output, name), { recursive: true });
}
if (target === "tourist") await cp(resolve(source, "recorder-worklet.js"), resolve(output, "recorder-worklet.js"));
