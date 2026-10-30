import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let createChatMetrics;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-metrics-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createChatMetrics } = await vite.ssrLoadModule('/src/utils/chatMetrics.js'));
});
after(async () => { await vite?.close(); });

test('measures distinct first text received, audio received, and audio scheduled without user content', () => {
  let now = 100;
  const metrics = createChatMetrics(() => now);
  now = 150; metrics.mark('text_received');
  now = 175; metrics.mark('audio_received');
  now = 200; metrics.mark('audio_scheduled');
  now = 210; metrics.mark('text_received');
  now = 300;
  assert.deepEqual(metrics.finish('complete'), {
    outcome: 'complete', duration_ms: 200, text_received_ms: 50,
    audio_received_ms: 75, audio_scheduled_ms: 100,
  });
});

test('unavailable audio timing remains absent', () => {
  let now = 0;
  const metrics = createChatMetrics(() => now);
  now = 10; metrics.mark('text_received');
  now = 50;
  assert.deepEqual(metrics.finish('incomplete'), { outcome: 'incomplete', duration_ms: 50, text_received_ms: 10 });
});

test('PCM underruns and added recovery buffering are recorded without content', () => {
  let now = 0;
  const metrics = createChatMetrics(() => now);
  metrics.recordAudioGap(100, 80);
  metrics.recordAudioGap(40, 0);
  now = 200;
  assert.deepEqual(metrics.finish('complete'), {
    outcome: 'complete', duration_ms: 200,
    pcm_underrun_count: 2, pcm_gap_ms: 140, pcm_extra_buffer_ms: 80,
  });
});
