import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite;
let createPublicationRecovery;
let createPublicationWorkflow;
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-pub-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createPublicationRecovery, createPublicationWorkflow } = await vite.ssrLoadModule('/src/utils/publicationRecovery.js'));
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

test('the admin workflow does not auto-resubmit an unknown publication after refresh', async () => {
  const storage = memoryStorage();
  const jobs = new Map();
  const submittedKeys = [];
  let submitCalls = 0;
  const options = {
    storage,
    createKey: () => 'admin-request-1',
    submit: async (items, key) => {
      submitCalls++;
      submittedKeys.push(key);
      if (!jobs.has(key)) jobs.set(key, { id: 'job-1', state: 'queued', items });
      if (submitCalls === 1) throw new Error('response lost');
      return jobs.get(key);
    },
    fetch: async (id) => ({ id, state: 'queued' }),
    retry: async (id) => ({ id, state: 'queued' }),
    setTimer: () => 1,
    clearTimer: () => {},
  };
  const items = [{ entry_id: 7, revision_id: 'rev-7', expected_version: 3 }];
  let visibleJob = null;
  const firstPage = createPublicationWorkflow({ ...options, onJob: (job) => { visibleJob = job; } });

  await assert.rejects(firstPage.publish(items), /response lost/);
  assert.equal(visibleJob.state, 'unknown');

  const refreshedPage = createPublicationWorkflow({ ...options, createKey: () => 'must-not-be-used', onJob: (job) => { visibleJob = job; } });
  await refreshedPage.restore();
  assert.equal(submitCalls, 1, 'refresh only presents a recovery action; it does not POST');
  assert.equal(visibleJob.state, 'unknown');

  await refreshedPage.recover();
  assert.equal(submitCalls, 2);
  assert.deepEqual(submittedKeys, ['admin-request-1', 'admin-request-1']);
  assert.equal(jobs.size, 1);
  assert.equal(refreshedPage.getPending().jobId, 'job-1');
});

test('a known publication job is restored by status lookup, not by creating another job', async () => {
  const storage = memoryStorage();
  let submissions = 0;
  let lookups = 0;
  const options = {
    storage,
    createKey: () => 'request-2',
    submit: async () => { submissions++; return { id: 'job-2', state: 'queued' }; },
    fetch: async (id) => { lookups++; return { id, state: 'queued' }; },
    retry: async (id) => ({ id, state: 'queued' }),
    setTimer: () => 1,
    clearTimer: () => {},
  };
  const firstPage = createPublicationWorkflow(options);
  await firstPage.publish([{ entry_id: 2, revision_id: 'rev-2', expected_version: 1 }]);
  const beforeRefreshLookups = lookups;
  const refreshedPage = createPublicationWorkflow(options);

  await refreshedPage.restore();
  assert.equal(submissions, 1);
  assert.equal(lookups, beforeRefreshLookups + 1);
  assert.equal(refreshedPage.getPending().jobId, 'job-2');
});

test('the admin workflow refuses to submit if session storage cannot persist the idempotency record', async () => {
  let submissions = 0;
  const workflow = createPublicationWorkflow({
    storage: { getItem: () => null, setItem: () => { throw new Error('blocked'); }, removeItem: () => {} },
    createKey: () => 'request-3',
    submit: async () => { submissions++; return { id: 'job-3' }; },
    fetch: async (id) => ({ id, state: 'queued' }),
    retry: async (id) => ({ id, state: 'queued' }),
  });

  await assert.rejects(workflow.publish([{ entry_id: 3, revision_id: 'rev-3', expected_version: 1 }]), /未发送/);
  assert.equal(submissions, 0);
});

test('a successful publication clears its recovery record', async () => {
  const storage = memoryStorage();
  let succeeded = false;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => 'request-4',
    submit: async () => ({ id: 'job-4', state: 'queued' }),
    fetch: async (id) => ({ id, state: 'succeeded' }),
    retry: async (id) => ({ id, state: 'queued' }),
    onSuccess: () => { succeeded = true; },
    setTimer: () => 1,
    clearTimer: () => {},
  });

  await workflow.publish([{ entry_id: 4, revision_id: 'rev-4', expected_version: 2 }]);
  assert.equal(succeeded, true);
  assert.equal(workflow.getPending(), null);
});

test('a definitive create rejection clears the rejected request so a refreshed draft can be published', async () => {
  const storage = memoryStorage();
  let submissions = 0;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => `request-${submissions + 1}`,
    submit: async () => {
      submissions++;
      if (submissions === 1) throw Object.assign(new Error('draft changed'), { response: { status: 409 } });
      return { id: 'job-5', state: 'queued' };
    },
    fetch: async (id) => ({ id, state: 'queued' }),
    retry: async (id) => ({ id, state: 'queued' }),
    setTimer: () => 1,
    clearTimer: () => {},
  });

  await assert.rejects(workflow.publish([{ entry_id: 5, revision_id: 'rev-old', expected_version: 1 }]), /draft changed/);
  assert.equal(workflow.getPending(), null);
  await workflow.publish([{ entry_id: 5, revision_id: 'rev-new', expected_version: 2 }]);
  assert.equal(submissions, 2);
});

test('an in-flight status response cannot restart polling after the workflow is disposed', async () => {
  const storage = memoryStorage();
  const seed = createPublicationRecovery({ storage, createKey: () => 'request-6', submit: async () => ({ id: 'job-6' }) });
  seed.begin([{ entry_id: 6, revision_id: 'rev-6', expected_version: 1 }]);
  await seed.submitPending();
  let resolveFetch;
  let scheduled = 0;
  let visibleUpdates = 0;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => 'unused',
    submit: async () => { throw new Error('must not submit'); },
    fetch: () => new Promise((resolve) => { resolveFetch = resolve; }),
    retry: async (id) => ({ id, state: 'queued' }),
    onJob: () => { visibleUpdates++; },
    setTimer: () => { scheduled++; return scheduled; },
    clearTimer: () => {},
  });

  const restoring = workflow.restore();
  workflow.stop();
  resolveFetch({ id: 'job-6', state: 'queued' });
  await restoring;
  assert.equal(visibleUpdates, 0);
  assert.equal(scheduled, 0);
});

test('a lost retry response reconciles the known job before offering another retry', async () => {
  const storage = memoryStorage();
  const seed = createPublicationRecovery({ storage, createKey: () => 'request-7', submit: async () => ({ id: 'job-7' }) });
  seed.begin([{ entry_id: 7, revision_id: 'rev-7', expected_version: 1 }]);
  await seed.submitPending();
  let currentState = 'failed';
  let retryCalls = 0;
  let visibleJob;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => 'unused',
    submit: async () => { throw new Error('must not create'); },
    fetch: async (id) => ({ id, state: currentState }),
    retry: async () => {
      retryCalls++;
      currentState = 'queued';
      throw new Error('retry response lost');
    },
    onJob: (job) => { visibleJob = job; },
    setTimer: () => 1,
    clearTimer: () => {},
  });
  await workflow.restore();

  await workflow.retry();
  assert.equal(retryCalls, 1);
  assert.equal(visibleJob.state, 'queued');
});

test('a known job remains queryable in memory when persisting its ID fails', async () => {
  const backing = memoryStorage();
  let writes = 0;
  const storage = {
    getItem: (key) => backing.getItem(key),
    setItem: (key, value) => {
      writes++;
      if (writes > 1) throw new Error('quota exceeded');
      backing.setItem(key, value);
    },
    removeItem: (key) => backing.removeItem(key),
  };
  let submits = 0;
  let fetches = 0;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => 'request-8',
    submit: async () => { submits++; return { id: 'job-8', state: 'queued' }; },
    fetch: async (id) => {
      fetches++;
      if (fetches === 1) throw new Error('temporary network failure');
      return { id, state: 'queued' };
    },
    retry: async (id) => ({ id, state: 'queued' }),
    setTimer: () => 1,
    clearTimer: () => {},
  });

  await assert.rejects(workflow.publish([{ entry_id: 8, revision_id: 'rev-8', expected_version: 1 }]));
  assert.equal(workflow.getPending().jobId, 'job-8');
  await workflow.recover();
  assert.equal(submits, 1);
  assert.equal(fetches, 2);
});

test('a status lookup rejection after successful creation preserves the known job ID', async () => {
  const storage = memoryStorage();
  let submissions = 0;
  let lookups = 0;
  let visibleJob;
  const workflow = createPublicationWorkflow({
    storage,
    createKey: () => 'request-9',
    submit: async () => { submissions++; return { id: 'job-9', state: 'queued' }; },
    fetch: async (id) => {
      lookups++;
      if (lookups === 1) throw Object.assign(new Error('not visible yet'), { response: { status: 404 } });
      return { id, state: 'queued' };
    },
    retry: async (id) => ({ id, state: 'queued' }),
    onJob: (job) => { visibleJob = job; },
    setTimer: () => 1,
    clearTimer: () => {},
  });

  await assert.rejects(workflow.publish([{ entry_id: 9, revision_id: 'rev-9', expected_version: 1 }]), /not visible yet/);
  assert.equal(workflow.getPending().jobId, 'job-9');
  assert.equal(visibleJob.state, 'unknown');
  await workflow.recover();
  assert.equal(submissions, 1);
  assert.equal(lookups, 2);
  assert.equal(visibleJob.state, 'queued');
});
