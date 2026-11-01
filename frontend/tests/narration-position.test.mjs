import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

test('invalid position drops pending narration without interrupting audio', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-position', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    let interrupts = 0, triggers = 0;
    const narration = useNarration({ getPosition: () => null, getSpots: () => [], isBusy: () => true,
      onInterrupt: () => interrupts++, onTrigger: () => triggers++, maxPendingWaitMs: 0 });
    narration.trigger({ name: '景点', lat: 31, lng: 120 });
    narration.drainPending();
    assert.equal(interrupts, 0);
    assert.equal(triggers, 0);
  } finally { await vite.close(); }
});

test('timed out narration does not take over unrelated busy audio', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-owner', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const spot = { name: '景点', lat: 31, lng: 120 };
    let triggered = 0, busyAllowed = false;
    const narration = useNarration({ getPosition: () => spot, getSpots: () => [spot], isBusy: () => true,
      onInterrupt: () => busyAllowed, onTrigger: () => triggered++, maxPendingWaitMs: 0 });
    narration.trigger(spot);
    narration.drainPending();
    assert.equal(triggered, 0);
    assert.equal(narration.status.value, 'pending');
    busyAllowed = true;
    narration.drainPending();
    assert.equal(triggered, 1);
  } finally { await vite.close(); }
});

test('a discarded pending narration can trigger after location recovers', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-recovery', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const spot = { name: '景点', lat: 31, lng: 120 };
    let position = spot, busy = true, triggers = 0;
    const narration = useNarration({ getPosition: () => position, getSpots: () => [spot], isBusy: () => busy,
      onTrigger: () => triggers++, maxPendingWaitMs: 0 });
    narration.update();
    position = null;
    narration.drainPending();
    position = spot; busy = false;
    narration.update();
    assert.equal(triggers, 1);
  } finally { await vite.close(); }
});

test('replaced pending spot can be narrated when revisited', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-replaced', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const first = { name: '甲', lat: 31, lng: 120 }, second = { name: '乙', lat: 31.01, lng: 120 };
    let position = first, busy = true, triggered = [];
    const narration = useNarration({ getPosition: () => position, getSpots: () => [first, second], isBusy: () => busy,
      onTrigger: spot => triggered.push(spot.name), maxPendingWaitMs: 0 });
    narration.trigger(first); narration.trigger(second);
    narration.drainPending();
    busy = false;
    narration.update();
    assert.deepEqual(triggered, ['甲']);
  } finally { await vite.close(); }
});

test('an older narration request cannot reset a newer playing state', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-generation', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const resolvers = [];
    const narration = useNarration({ getPosition: () => null, getSpots: () => [], isBusy: () => false,
      onTrigger: () => new Promise(resolve => resolvers.push(resolve)) });
    narration.fire({ name: '甲' }); narration.fire({ name: '乙' });
    resolvers[0]();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(narration.status.value, 'playing');
    resolvers[1]();
  } finally { await vite.close(); }
});

test('synchronous narration failure leaves state recoverable', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-failure', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const spot = { name: '景点', lat: 31, lng: 120 };
    let fail = true, calls = 0;
    const narration = useNarration({ getPosition: () => spot, getSpots: () => [spot], isBusy: () => false,
      onTrigger: () => { if (fail) throw new Error('failed'); calls++; } });
    narration.update();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(narration.status.value, 'idle');
    fail = false;
    narration.update();
    assert.equal(calls, 1);
  } finally { await vite.close(); }
});

test('asynchronous narration rejection clears its unfinished state', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-rejection', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    const spot = { name: '景点', lat: 31, lng: 120 };
    const narration = useNarration({ getPosition: () => spot, getSpots: () => [spot], isBusy: () => false,
      onTrigger: () => Promise.reject(new Error('failed')) });
    narration.update();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(narration.status.value, 'idle');
    assert.deepEqual(narration.completed.value, []);
    assert.equal(narration.activeSpot.value, null);
  } finally { await vite.close(); }
});
