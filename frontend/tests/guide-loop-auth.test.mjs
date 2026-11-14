import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

test('admin replay sends its token only to the authenticated admin endpoint', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-loop-auth-test', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  const originalFetch = globalThis.fetch;
  const originalCrypto = globalThis.crypto;
  try {
    const auth = await vite.ssrLoadModule('/src/utils/adminAuthStorage.js');
    const { replayGuideLoopQuestion } = await vite.ssrLoadModule('/src/api/guideLoop.js');
    auth.setAdminToken('local-test-token');
    if (!globalThis.crypto?.randomUUID) Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { randomUUID: () => 'test-uuid' } });
    let captured;
    globalThis.fetch = async (url, options) => {
      captured = { url, options };
      return new Response('event: text\ndata: {"text":"测试回答"}\n\nevent: done\ndata: {}\n\n', { headers: { 'Content-Type': 'text/event-stream' } });
    };
    const result = await replayGuideLoopQuestion({ query: '是谁', poiId: 'bathing' });
    assert.equal(captured.url, '/api/admin/guide-loop/replay');
    assert.equal(captured.options.headers.Authorization, 'Bearer local-test-token');
    assert.equal(JSON.parse(captured.options.body).guide_loop.poi_id, 'bathing');
    assert.equal(result.text, '测试回答');
    auth.clearAdminToken();
    await assert.rejects(() => replayGuideLoopQuestion({ query: '是谁', poiId: 'bathing' }), /登录/);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalCrypto) Object.defineProperty(globalThis, 'crypto', { configurable: true, value: originalCrypto });
    else delete globalThis.crypto;
    await vite.close();
  }
});
