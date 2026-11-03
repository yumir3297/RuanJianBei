export function setManualStopDuration(stop, raw) {
  const minutes = raw === '' ? null : Number(raw);
  if (minutes === stop.duration_minutes) return;
  stop.duration_minutes = minutes;
  stop.duration_basis = minutes === null ? 'unknown' : 'user';
}
