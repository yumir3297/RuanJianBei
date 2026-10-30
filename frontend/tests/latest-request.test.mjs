import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite;
let createLatestRequest;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-latest-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createLatestRequest } = await vite.ssrLoadModule('/src/utils/latestRequest.js'));
});
after(async () => { await vite?.close(); });

test('starting a new request aborts and invalidates the old request', () => {
  const requests = createLatestRequest();
  const old = requests.begin();
  const current = requests.begin();
  assert.equal(old.signal.aborted, true);
  assert.equal(old.isCurrent(), false);
  assert.equal(current.isCurrent(), true);
  requests.cancel();
  assert.equal(current.signal.aborted, true);
  assert.equal(current.isCurrent(), false);
});
