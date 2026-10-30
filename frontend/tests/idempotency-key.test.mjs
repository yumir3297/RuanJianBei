import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let createIdempotencyKey;
let transcribeAudio;
let analyzeImage;
let http;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-idempotency-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createIdempotencyKey } = await vite.ssrLoadModule('/src/utils/idempotencyKey.js'));
  ({ transcribeAudio } = await vite.ssrLoadModule('/src/api/voice.js'));
  ({ analyzeImage } = await vite.ssrLoadModule('/src/api/vision.js'));
  ({ default: http } = await vite.ssrLoadModule('/src/api/http.js'));
});
after(async () => { await vite?.close(); });

test('operation keys are unique random identifiers', () => {
  assert.notEqual(createIdempotencyKey(), createIdempotencyKey());
});

test('ASR and vision requests send the supplied operation key', async () => {
  const original = http.defaults.adapter;
  const storage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: () => null } });
  const seen = [];
  http.defaults.adapter = async (config) => {
    seen.push(config.headers['Idempotency-Key'] || config.headers.get?.('Idempotency-Key'));
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config };
  };
  try {
    await transcribeAudio(new Blob(['audio'], { type: 'audio/webm' }), { idempotencyKey: 'asr-key' });
    await analyzeImage(new File(['image'], 'photo.jpg', { type: 'image/jpeg' }), 'question', { idempotencyKey: 'vision-key' });
    assert.deepEqual(seen, ['asr-key', 'vision-key']);
  } finally {
    http.defaults.adapter = original;
    if (storage) Object.defineProperty(globalThis, 'localStorage', storage);
    else delete globalThis.localStorage;
  }
});
