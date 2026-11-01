// Labels are estimates; choose the upper bound rather than understate a range.
export function routeDurationMinutes(label) {
  const match = String(label || '').match(/(\d+(?:\.\d+)?)\s*(?:[-–—~～至]\s*(\d+(?:\.\d+)?))?\s*小时/);
  if (!match) return null;
  const hours = Math.max(Number(match[1]), Number(match[2] || match[1]));
  return Math.max(1, Math.min(720, Math.ceil(hours * 60)));
}
