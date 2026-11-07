import { spawnSync } from "node:child_process";

const result = spawnSync(process.execPath, ["--test", "tests/app-boundaries.test.mjs"], { stdio: "inherit" });
process.exitCode = result.status ?? 1;
