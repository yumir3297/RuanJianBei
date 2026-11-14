// The management list may display a draft title. Bind only the published IDs.
export function publishedKnowledgeOptions(entries) {
  if (!Array.isArray(entries)) throw new TypeError("知识列表格式不正确");
  return entries.filter(entry => Number.isSafeInteger(entry.id) && entry.id > 0 &&
    typeof entry.published_revision_id === "string" && entry.published_revision_id && !entry.withdrawn_at)
    .map(entry => ({
      entryId: entry.id,
      revisionId: entry.published_revision_id,
      label: `条目 ${entry.id} · 版本 ${entry.published_revision_id}${entry.draft_revision_id ? " · 存在草稿" : ""}`,
    }));
}

export function applyKnowledgeSelection(form, option) {
  form.knowledge_entry_id = option?.entryId ?? "";
  form.knowledge_revision_id = option?.revisionId ?? "";
}

export function isCurrentKnowledgeSelection(form, options) {
  return options.some(option => String(option.entryId) === String(form.knowledge_entry_id) &&
    option.revisionId === form.knowledge_revision_id);
}
