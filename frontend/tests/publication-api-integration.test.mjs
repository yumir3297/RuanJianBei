import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { createServer } from 'vite';

test('K01 publication API reuses the provided idempotency key', { skip: !existsSync('src/api/knowledgePublications.js') }, async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-k01-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  const { createKnowledgePublication } = await vite.ssrLoadModule('/src/api/knowledgePublications.js');
  const { default: http } = await vite.ssrLoadModule('/src/api/http.js');
  const original = http.defaults.adapter;
  const storage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: () => null } });
  let sent;
  http.defaults.adapter = async config => {
    sent = JSON.parse(config.data);
    return { status: 202, statusText: 'Accepted', data: { id: 'job-1', state: 'queued' }, headers: {}, config };
  };
  try {
    await createKnowledgePublication([{ entry_id: 1, revision_id: 'rev-1', expected_version: 1 }], 'original-key');
    assert.equal(sent.idempotency_key, 'original-key');
  } finally {
    http.defaults.adapter = original;
    if (storage) Object.defineProperty(globalThis, 'localStorage', storage);
    else delete globalThis.localStorage;
    await vite.close();
  }
});
