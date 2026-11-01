export function findPublishedAttraction(name, attractions) {
  const matches = (Array.isArray(attractions) ? attractions : []).filter(item => item.title === name && Number.isInteger(item.id) && item.id > 0);
  return matches.length === 1 ? matches[0].id : null;
}
