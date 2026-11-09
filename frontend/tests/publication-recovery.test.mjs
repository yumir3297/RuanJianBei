import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite;
let createPublicationRecovery;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-pub-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createPublicationRecovery } = await vite.ssrLoadModule('/src/utils/publicationRecovery.js'));
});
after(async () => { await vite?.close(); });

function memoryStorage() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}

test('a lost creation response can be recovered after refresh with the same idempotency key', async () => {
  const storage = memoryStorage();
  const jobs = new Map();
  let calls = 0;
  const submit = async (items, key) => {
    calls++;
    if (!jobs.has(key)) jobs.set(key, { id: 'job-1', state: 'queued', items });
    if (calls === 1) throw new Error('response lost');
    return jobs.get(key);
  };
  const items = [{ entry_id: 1, revision_id: 'rev-1', expected_version: 2 }];
  const first = createPublicationRecovery({ storage, createKey: () => 'request-1', submit });
  first.begin(items);
  await assert.rejects(first.submitPending());
  const afterRefresh = createPublicationRecovery({ storage, createKey: () => 'wrong-new-key', submit });
  assert.equal(afterRefresh.getPending().key, 'request-1');
  assert.equal((await afterRefresh.submitPending()).id, 'job-1');
  assert.equal(jobs.size, 1);
  assert.equal(afterRefresh.getPending().jobId, 'job-1');
});

test('an unresolved publication blocks creating a second operation', () => {
  const recovery = createPublicationRecovery({ storage: memoryStorage(), createKey: () => 'request-1', submit: async () => ({ id: 'job-1' }) });
  recovery.begin([{ entry_id: 1, revision_id: 'rev-1', expected_version: 1 }]);
  assert.throws(() => recovery.begin([{ entry_id: 2, revision_id: 'rev-2', expected_version: 1 }]), /待确认/);
});

test('a corrupt pending record repeatedly blocks new submissions instead of being forgotten', () => {
  const storage = memoryStorage();
  storage.setItem('guide-pending-publication-v1', '{broken');
  const recovery = createPublicationRecovery({ storage, createKey: () => 'new', submit: async () => ({ id: 'job' }) });
  assert.throws(() => recovery.getPending(), /记录损坏/);
  assert.throws(() => recovery.begin([{ entry_id: 1 }]), /记录损坏/);
});

test('publication recovery works when structuredClone is unavailable', () => {
  const original = globalThis.structuredClone;
  try {
    globalThis.structuredClone = undefined;
    const recovery = createPublicationRecovery({ storage: memoryStorage(), createKey: () => 'k', submit: async () => ({ id: 'job' }) });
    assert.equal(recovery.begin([{ entry_id: 1, revision_id: 'r', expected_version: 1 }]).key, 'k');
  } finally { globalThis.structuredClone = original; }
});
