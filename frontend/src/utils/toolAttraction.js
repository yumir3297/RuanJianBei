export function findPublishedAttraction(name, attractions) {
  const matches = (Array.isArray(attractions) ? attractions : []).filter(item => item.title === name && Number.isInteger(item.id) && item.id > 0);
  return matches.length === 1 ? matches[0].id : null;
}

export async function resolvePublishedAttraction(name, store) {
  if (!store.loaded && !store.loading) await store.loadBootstrap();
  if (!store.loaded) return null;
  return findPublishedAttraction(name, store.bootstrap.attractions);
}
