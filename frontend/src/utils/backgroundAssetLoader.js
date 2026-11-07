export const BACKGROUND_IMAGE_TIMEOUT_MS = 15000;

export function preloadBackgroundImage(url, {
  ImageConstructor = globalThis.Image,
  setTimeoutFn = globalThis.setTimeout,
  clearTimeoutFn = globalThis.clearTimeout,
  timeoutMs = BACKGROUND_IMAGE_TIMEOUT_MS,
} = {}) {
  if (typeof ImageConstructor !== "function") return Promise.resolve(false);
  return new Promise((resolve) => {
    const image = new ImageConstructor();
    const timeout = setTimeoutFn(() => finish(false), timeoutMs);
    let settled = false;
    function finish(loaded) {
      if (settled) return;
      settled = true;
      clearTimeoutFn(timeout);
      image.onload = null;
      image.onerror = null;
      resolve(loaded);
    }
    image.onload = () => finish(true);
    image.onerror = () => finish(false);
    image.src = url;
  });
}

export function createBackgroundAssetLoader({
  resolveUrl = (url) => url,
  preload = preloadBackgroundImage,
  onChange = () => {},
} = {}) {
  let generation = 0;
  let currentUrl = null;
  let pendingUrl = null;
  let loading = false;
  let disposed = false;

  function snapshot() {
    return { url: currentUrl, loading };
  }

  async function load(assetUrl) {
    if (disposed) return snapshot();
    const nextUrl = resolveUrl(assetUrl);
    if (!nextUrl) {
      generation += 1;
      pendingUrl = null;
      currentUrl = "";
      loading = false;
      onChange(snapshot());
      return snapshot();
    }
    if (nextUrl === currentUrl || nextUrl === pendingUrl) return snapshot();

    const requestGeneration = ++generation;
    pendingUrl = nextUrl;
    loading = true;
    onChange(snapshot());
    let loaded = false;
    try {
      loaded = await preload(nextUrl);
    } catch { /* preserve a previous good background */ }
    if (disposed || requestGeneration !== generation) return snapshot();

    pendingUrl = null;
    loading = false;
    if (loaded) currentUrl = nextUrl;
    else if (currentUrl === null) currentUrl = "";
    onChange(snapshot());
    return snapshot();
  }

  function dispose() {
    disposed = true;
    generation += 1;
    pendingUrl = null;
    loading = false;
  }

  return {
    load,
    dispose,
    snapshot,
    get currentUrl() { return currentUrl; },
    get loading() { return loading; },
  };
}
