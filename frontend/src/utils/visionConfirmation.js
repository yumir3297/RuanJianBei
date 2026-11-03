// Confirmation is an explicit visitor choice among currently displayed published entries.
export function buildVisionChatRequest(result, confirmation) {
  return {
    query: "请依据已发布资料帮助我了解这张照片可能涉及的景点。",
    visionContext: { ...result, ...(confirmation ? { confirmation } : {}) },
  };
}

export function visionConfirmation(catalog, spotCode) {
  if (!spotCode || !catalog?.site_id) return null;
  const item = (catalog.items || []).find(entry => entry.spot_code === spotCode);
  if (!item?.published_revision_id) return null;
  return { site_id: catalog.site_id, spot_code: item.spot_code, published_revision_id: item.published_revision_id };
}

export function createVisionAsyncGuard() {
  let generation = 0;
  return {
    cancel() { generation += 1; },
    async run(operation) {
      const current = ++generation;
      const result = await operation();
      return current === generation ? result : undefined;
    },
  };
}
