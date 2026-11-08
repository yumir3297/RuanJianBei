import test from "node:test";
import assert from "node:assert/strict";
import { canSubmitImports, validateImportFiles } from "../src/utils/importLimits.js";

const limits = { knowledge_import: { max_files: 1, max_file_bytes: 50 * 1024 * 1024 } };

test("selection respects the server file-count limit", () => {
  assert.deepEqual(validateImportFiles([{ size: 1 }, { size: 1 }], limits), { ok: false, reason: "too_many_files" });
});

test("selection respects the server per-file byte limit", () => {
  assert.deepEqual(validateImportFiles([{ size: 50 * 1024 * 1024 + 1 }], limits), { ok: false, reason: "file_too_large" });
});

test("missing or malformed limits fail closed", () => {
  assert.deepEqual(validateImportFiles([{ size: 1 }], null), { ok: false, reason: "limits_unavailable" });
});

test("limits are checked against the configured actual batch size, not a production constant", () => {
  assert.deepEqual(validateImportFiles([{ size: 100 }, { size: 100 }], {
    knowledge_import: { max_files: 20, max_file_bytes: 200 },
  }), { ok: true, reason: "" });
});

test("upload remains disabled after a failed limits request and enables only with a valid policy", () => {
  assert.equal(canSubmitImports({ files: [{ size: 1 }], limits: null, limitsLoading: false, limitsError: "unavailable", uploading: false }), false);
  assert.equal(canSubmitImports({ files: [{ size: 1 }], limits, limitsLoading: false, limitsError: "", uploading: false }), true);
  assert.equal(canSubmitImports({ files: [{ size: 1 }], limits, limitsLoading: true, limitsError: "", uploading: false }), false);
});
