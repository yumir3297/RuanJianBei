const AUTH_KEY = "a5-admin-auth";
let memoryToken = null;
const listeners = new Set();

function notify(token) {
  for (const listener of [...listeners]) listener(token);
}

export function getAdminToken() {
  try {
    const stored = globalThis.localStorage?.getItem(AUTH_KEY);
    if (stored) {
      memoryToken = stored;
      return stored;
    }
    return memoryToken;
  } catch {
    return memoryToken;
  }
}

export function setAdminToken(token) {
  memoryToken = String(token || "") || null;
  try {
    if (memoryToken) globalThis.localStorage?.setItem(AUTH_KEY, memoryToken);
    else globalThis.localStorage?.removeItem(AUTH_KEY);
  } catch { /* current-page login remains available in memory */ }
  notify(memoryToken);
}

export function clearAdminToken() {
  memoryToken = null;
  try { globalThis.localStorage?.removeItem(AUTH_KEY); } catch { /* storage may be disabled */ }
  notify(null);
}

export function subscribeAdminToken(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
