export function operationFingerprint(operation, payload) {
  return `${operation}:${JSON.stringify(payload)}`;
}

export function getOperationKey(cache, operation, payload, createKey) {
  const fingerprint = operationFingerprint(operation, payload);
  if (!cache[fingerprint]) cache[fingerprint] = createKey();
  return { fingerprint, key: cache[fingerprint] };
}
