import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite;
let getVisionErrorMessage;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-vision-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ getVisionErrorMessage } = await vite.ssrLoadModule('/src/api/vision.js'));
});
after(async () => { await vite?.close(); });

test('animated WebP rejection tells the visitor to choose a static image', () => {
  assert.match(getVisionErrorMessage({ response: { status: 415, data: { detail: '暂不支持动态 WebP，请选择静态图片。' } } }), /静态/);
});

test('timeouts offer a retry without exposing technical errors', () => {
  assert.match(getVisionErrorMessage({ code: 'ECONNABORTED' }), /重试/);
});

test('capacity rejection describes a busy service', () => {
  assert.match(getVisionErrorMessage({ response: { status: 429 } }), /繁忙/);
});
