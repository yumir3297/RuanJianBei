// Confirmation is an explicit visitor choice among currently displayed published entries.
export function visionConfirmation(catalog, spotCode) {
  if (!spotCode || !catalog?.site_id) return null;
  const item = (catalog.items || []).find(entry => entry.spot_code === spotCode);
  if (!item?.published_revision_id) return null;
  return { site_id: catalog.site_id, spot_code: item.spot_code, published_revision_id: item.published_revision_id };
}
