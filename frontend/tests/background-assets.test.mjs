import assert from "node:assert/strict";
import test from "node:test";
import { createBackgroundAssetLoader, preloadBackgroundImage } from "../src/utils/backgroundAssetLoader.js";

class FakeImage {
  static instances = [];
  constructor() { FakeImage.instances.push(this); }
  set src(value) { this.url = value; }
}

test("background image preload times out at 15 seconds and reports a 404", async () => {
  FakeImage.instances = [];
  let timeoutCallback;
  let timeoutDelay;
  const timedOut = preloadBackgroundImage("/slow.jpg", {
    ImageConstructor: FakeImage,
    setTimeoutFn: (callback, delay) => { timeoutCallback = callback; timeoutDelay = delay; return 1; },
    clearTimeoutFn: () => {},
  });
  assert.equal(timeoutDelay, 15000);
  timeoutCallback();
  assert.equal(await timedOut, false);

  const failed = preloadBackgroundImage("/missing.jpg", {
    ImageConstructor: FakeImage,
    setTimeoutFn: () => 2,
    clearTimeoutFn: () => {},
  });
  FakeImage.instances.at(-1).onerror();
  assert.equal(await failed, false);
});

test("a failed replacement keeps the last successfully loaded background", async () => {
  const loader = createBackgroundAssetLoader({
    resolveUrl: (url) => url,
    preload: async (url) => url === "/good.jpg",
  });
  await loader.load("/good.jpg");
  await loader.load("/missing.jpg");
  assert.equal(loader.currentUrl, "/good.jpg");
});

test("a late image load cannot replace a newer background", async () => {
  const resolvers = new Map();
  const loader = createBackgroundAssetLoader({
    resolveUrl: (url) => url,
    preload: (url) => new Promise((resolve) => resolvers.set(url, resolve)),
  });
  const oldLoad = loader.load("/old.jpg");
  const newLoad = loader.load("/new.jpg");
  resolvers.get("/new.jpg")(true);
  await newLoad;
  resolvers.get("/old.jpg")(true);
  await oldLoad;
  assert.equal(loader.currentUrl, "/new.jpg");
});

test("reselecting the current background invalidates a different pending image", async () => {
  const resolvers = new Map();
  const loader = createBackgroundAssetLoader({
    resolveUrl: (url) => url,
    preload: (url) => new Promise((resolve) => resolvers.set(url, resolve)),
  });
  const first = loader.load("/a.jpg");
  resolvers.get("/a.jpg")(true);
  await first;

  const obsolete = loader.load("/b.jpg");
  const selectedAgain = await loader.load("/a.jpg");
  resolvers.get("/b.jpg")(true);
  await obsolete;

  assert.equal(selectedAgain.url, "/a.jpg");
  assert.equal(loader.currentUrl, "/a.jpg");
  assert.equal(loader.loading, false);
});
