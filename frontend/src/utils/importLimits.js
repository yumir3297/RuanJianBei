export function validateImportFiles(files, limits) {
  const policy = limits?.knowledge_import;
  if (!Number.isInteger(policy?.max_files) || policy.max_files < 1
    || !Number.isInteger(policy?.max_file_bytes) || policy.max_file_bytes < 1) {
    return { ok: false, reason: "limits_unavailable" };
  }
  if (!Array.isArray(files)) return { ok: false, reason: "limits_unavailable" };
  if (files.length > policy.max_files) return { ok: false, reason: "too_many_files" };
  if (files.some((file) => !Number.isFinite(file?.size) || file.size < 0 || file.size > policy.max_file_bytes)) {
    return { ok: false, reason: "file_too_large" };
  }
  return { ok: true, reason: "" };
}

export function canSubmitImports({ files, limits, limitsLoading, limitsError, uploading }) {
  return Boolean(!limitsLoading && !limitsError && !uploading && files?.length
    && validateImportFiles(files.map((file) => file?.raw || file), limits).ok);
}
