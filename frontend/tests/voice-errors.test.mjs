import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let getTranscriptionErrorMessage;
let transcribeAudio;
let http;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-voice-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ getTranscriptionErrorMessage, transcribeAudio } = await vite.ssrLoadModule('/src/api/voice.js'));
  ({ default: http } = await vite.ssrLoadModule('/src/api/http.js'));
});
after(async () => { await vite?.close(); });

test('audio duration rejection tells user to shorten the recording', () => {
  assert.match(getTranscriptionErrorMessage({ response: { status: 413, data: { detail: '录音时间过长，请缩短录音后重试。' } } }), /时间过长/);
});

test('network error retains a non-technical way to continue', () => {
  assert.match(getTranscriptionErrorMessage({ code: 'ECONNABORTED' }), /文字输入/);
});

test('capacity rejection describes a busy service', () => {
  assert.match(getTranscriptionErrorMessage({ response: { status: 429 } }), /繁忙/);
});

test('canceling a transcription propagates to the underlying request', async () => {
  const original = http.defaults.adapter;
  const storage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: () => null } });
  let underlyingSignal;
  http.defaults.adapter = config => new Promise((_resolve, reject) => {
    underlyingSignal = config.signal;
    config.signal.addEventListener('abort', () => reject(new Error('canceled')), { once: true });
  });
  try {
    const controller = new AbortController();
    const pending = transcribeAudio(new Blob(['abc'], { type: 'audio/wav' }), { signal: controller.signal });
    await new Promise(resolve => setTimeout(resolve, 0));
    controller.abort();
    await assert.rejects(pending);
    assert.equal(underlyingSignal.aborted, true);
  } finally {
    http.defaults.adapter = original;
    if (storage) Object.defineProperty(globalThis, 'localStorage', storage);
    else delete globalThis.localStorage;
  }
});
