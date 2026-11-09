import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let createAdaptiveAudioBuffer;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-adaptive-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createAdaptiveAudioBuffer } = await vite.ssrLoadModule('/src/utils/adaptiveAudioBuffer.js'));
});
after(async () => { await vite?.close(); });

test('healthy chunks are scheduled in order with no added delay', () => {
  const policy = createAdaptiveAudioBuffer();
  assert.equal(policy.schedule(0.08, 0.10), 0.10);
  assert.equal(policy.schedule(0.15, 0.20), 0.20);
});

test('a large stall adds a bounded buffer at most once during cooldown', () => {
  const policy = createAdaptiveAudioBuffer();
  assert.equal(policy.schedule(1, 0.8), 1.08);
  assert.equal(policy.schedule(1.3, 1.1), 1.3);
  assert.equal(policy.schedule(3.5, 3.3), 3.58);
});

test('small jitter does not add delay', () => {
  const policy = createAdaptiveAudioBuffer();
  assert.equal(policy.schedule(1, 0.97), 1);
});

test('on a deterministic burst trace the extra buffer absorbs a later stall', () => {
  const arrivals = [0, 0.25, 0.26, 0.27, 0.61, 0.62, 0.63];
  const run = (policy) => {
    let end = 0.1;
    let stalls = 0;
    for (const now of arrivals.slice(1)) {
      if (now > end + 0.001) stalls++;
      end = (policy ? policy.schedule(now, end) : Math.max(now, end)) + 0.1;
    }
    return stalls;
  };
  assert.equal(run(null), 2);
  assert.equal(run(createAdaptiveAudioBuffer()), 1);
});
