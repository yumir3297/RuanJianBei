function savedLocks(stop, savedStops) {
  return savedStops.find(item => item.stop_id === stop?.stop_id)?.locked_fields || [];
}

export function canEditDuration(stop, savedStops) {
  const locks = savedLocks(stop, savedStops);
  return !locks.includes('stop') && !locks.includes('duration');
}

export function canDeleteStop(stops, index, savedStops) {
  if (!stops[index] || savedLocks(stops[index], savedStops).length) return false;
  return !stops.slice(index + 1).some(stop => savedLocks(stop, savedStops).includes('position'));
}

export function canMoveStop(stops, index, direction, savedStops) {
  const target = index + direction;
  if (!stops[index] || !stops[target]) return false;
  return ![stops[index], stops[target]].some(stop => savedLocks(stop, savedStops).includes('position'));
}
