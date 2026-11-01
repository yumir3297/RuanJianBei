import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { createPinia, setActivePinia } from 'pinia';

let vite, useStore, http, store, route;
const snapshot = label => ({ schema_version: 2, stops: [{ stop_id: label, name: label }], constraints: {} });
const proposal = (session = 'a', status = 'ready') => ({ id: `p-${session}`, session_id: session, status, execution_job_id: `job-${session}`, base_snapshot: snapshot('base'), diff: [], validation: {} });
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { resolve, promise }; };
before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-proposal-recovery-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ useTourSessionsStore: useStore } = await vite.ssrLoadModule('/src/stores/tourSessions.js'));
  ({ default: http } = await vite.ssrLoadModule('/src/api/http.js'));
  http.defaults.adapter = async config => ({ data: await route(config), status: 200, statusText: 'OK', headers: {}, config });
});
beforeEach(() => {
  store?.clearProposal();
  setActivePinia(createPinia()); store = useStore();
  store.csrfToken = 'csrf'; store.identityId = 'owner';
  store.current = { id: 'a', version: 1, snapshot: snapshot('base') };
  store.draftSnapshot = snapshot('base');
  route = async () => { throw new Error('Unexpected API request'); };
});
after(async () => { store?.clearProposal(); await vite.close(); });

test('latest failed proposal is restored instead of an older ready proposal', async () => {
  const failed = { ...proposal('a', 'failed'), id: 'failed-new', validation: { message: '提案未能完成' } };
  const older = { ...proposal(), id: 'ready-old' };
  route = async config => {
    if (config.url.endsWith('/proposals')) return { items: [failed, older] };
    if (config.url.endsWith('/proposals/failed-new')) return failed;
    if (config.url.endsWith('/proposals/ready-old')) return older;
    throw new Error(config.url);
  };
  await store.restoreProposal();
  assert.equal(store.proposal.id, 'failed-new');
  assert.equal(store.proposal.status, 'failed');
});

test('latest applied proposal does not resurrect an older ready proposal', async () => {
  store.proposal = { ...proposal(), id: 'ready-old' };
  route = async config => {
    if (config.url.endsWith('/proposals')) return { items: [{ ...proposal('a', 'applied'), id: 'applied-new' }, { ...proposal(), id: 'ready-old' }] };
    throw new Error(`unexpected detail request ${config.url}`);
  };
  await store.restoreProposal();
  assert.equal(store.proposal, null);
});

test('equal proposal timestamps do not silently choose a random latest task', async () => {
  route = async config => {
    if (config.url.endsWith('/proposals')) return { items: [
      { ...proposal('a', 'ready'), id: 'first', created_at: '2026-11-01T10:00:00' },
      { ...proposal('a', 'failed'), id: 'second', created_at: '2026-11-01T10:00:00' },
    ] };
    return { ...proposal(), id: 'first' };
  };
  await store.restoreProposal();
  assert.equal(store.proposal, null);
  assert.match(store.error, /无法确定|无法判断/);
  assert.match(store.error, /避免重复调用/);
  assert.equal(store.proposalChoices.length, 2);
  await store.selectProposalChoice('first');
  assert.equal(store.proposal.id, 'first');
});

test('opening a tour restores a ready proposal and its base without changing the saved draft', async () => {
  route = async config => {
    if (config.url === '/tour-sessions/a') return { id: 'a', version: 1, snapshot: snapshot('saved') };
    if (config.url.endsWith('/revisions')) return { items: [] };
    if (config.url.endsWith('/progress')) return { progress_version: 1 };
    if (config.url.endsWith('/budget')) return { known_minutes: 10 };
    if (config.url.endsWith('/proposals')) return { items: [proposal()] };
    if (config.url.endsWith('/proposals/p-a')) return proposal();
    throw new Error(config.url);
  };
  await store.open('a'); await tick(); await tick();
  assert.equal(store.proposal.id, 'p-a');
  assert.deepEqual(store.draftSnapshot, snapshot('saved'));
  assert.deepEqual(store.proposalBaseSnapshot, snapshot('base'));
  assert.equal(store.proposalIsStale, true);
  assert.equal(store.proposalLoading, false);
});

test('resume preserves manual edits and never automatically retries waiting_user', async () => {
  store.draftSnapshot = snapshot('edited');
  await store.resumeProposal(proposal('a', 'waiting_user'));
  assert.deepEqual(store.draftSnapshot, snapshot('edited'));
  assert.equal(store.proposalIsStale, true);
  assert.equal(await store.retryProposal(), null);
  assert.match(store.error, /确认.*费用/);
});

test('a restored detail arriving after switching tours cannot replace the new proposal', async () => {
  const late = deferred();
  route = async config => config.url.endsWith('/proposals') ? { items: [proposal()] } : late.promise;
  const old = store.restoreProposal(); await tick();
  store.clearProposal(); store.current = { id: 'b' }; store.draftSnapshot = snapshot('b');
  await store.resumeProposal(proposal('b'));
  late.resolve(proposal()); await old;
  assert.equal(store.proposal.id, 'p-b');
  assert.deepEqual(store.draftSnapshot, snapshot('b'));
  assert.equal(store.error, '');
});

test('stopping browser waiting preserves backend work and blocks delayed UI writes', async () => {
  const pending = store.resumeProposal(proposal('a', 'executing'));
  assert.equal(store.proposalLoading, true);
  store.cancelProposal(); await pending;
  assert.equal(store.proposal, null);
  assert.equal(store.proposalLoading, false);
  assert.equal(store.error, '');
});

test('poll completion cannot overwrite a newer tour or proposal', async () => {
  const late = deferred();
  const realTimeout = globalThis.setTimeout;
  globalThis.setTimeout = (fn, ms, ...args) => realTimeout(fn, ms === 1000 ? 0 : ms, ...args);
  try {
    route = async config => { assert.equal(config.url, '/tour-sessions/a/proposals/p-a'); return late.promise; };
    const old = store.resumeProposal(proposal('a', 'executing'));
    await new Promise(resolve => realTimeout(resolve, 10));
    store.clearProposal(); store.current = { id: 'b' };
    await store.resumeProposal(proposal('b'));
    late.resolve(proposal()); await old;
    assert.equal(store.proposal.id, 'p-b');
    assert.equal(store.proposalLoading, false);
  } finally { globalThis.setTimeout = realTimeout; }
});

test('explicit risk confirmation sends protected retry and recovers its result', async () => {
  const realTimeout = globalThis.setTimeout;
  globalThis.setTimeout = (fn, ms, ...args) => realTimeout(fn, ms === 1000 ? 0 : ms, ...args);
  try {
    let retries = 0;
    route = async config => {
      if (config.method === 'post') {
        retries++;
        assert.equal(config.url, '/tour-sessions/a/executions/job-a/retry');
        assert.equal(JSON.parse(config.data).confirm_duplicate_risk, true);
        assert.equal(config.headers.get('X-CSRF-Token'), 'csrf');
        assert.ok(config.headers.get('Idempotency-Key'));
        return { status: 'queued' };
      }
      return proposal();
    };
    await store.resumeProposal(proposal('a', 'waiting_user'));
    await store.retryProposal(true);
    assert.equal(retries, 1);
    assert.equal(store.proposal.status, 'ready');
    assert.equal(store.proposalLoading, false);
  } finally { globalThis.setTimeout = realTimeout; }
});

test('retry response after closing a proposal cannot restart its polling', async () => {
  const late = deferred(); let calls = 0;
  route = async () => { calls++; return late.promise; };
  await store.resumeProposal(proposal('a', 'waiting_user'));
  const retry = store.retryProposal(true); await tick();
  store.cancelProposal(); late.resolve({ status: 'queued' }); await retry;
  assert.equal(calls, 1);
  assert.equal(store.proposal, null);
  assert.equal(store.proposalLoading, false);
});

test('out-of-order open responses cannot replace the most recently selected tour', async () => {
  const late = deferred();
  route = async config => {
    if (config.url === '/tour-sessions/a') return late.promise;
    if (config.url === '/tour-sessions/b') return { id: 'b', snapshot: snapshot('b') };
    if (config.url.endsWith('/progress')) return {};
    if (config.url.endsWith('/budget')) return {};
    return { items: [] };
  };
  const old = store.open('a'); await tick();
  await store.open('b'); await tick();
  late.resolve({ id: 'a', snapshot: snapshot('a') }); await old;
  assert.equal(store.current.id, 'b');
  assert.deepEqual(store.draftSnapshot, snapshot('b'));
});

test('late progress update cannot overwrite the newly selected tour', async () => {
  const late = deferred();
  store.progress = { status: 'active', progress_version: 1, current_stop_id: 'old-stop' };
  route = async config => {
    if (config.method === 'post') { assert.equal(config.url, '/tour-sessions/a/progress'); return late.promise; }
    throw new Error(`unexpected ${config.url}`);
  };
  const pending = store.applyProgress({ type: 'set_remaining_budget', remaining_minutes: 30 });
  await tick();
  store.current = { id: 'b', version: 1 };
  store.progress = { status: 'active', progress_version: 7, current_stop_id: 'new-stop' };
  store.budget = { known_minutes: 12 };
  late.resolve({ status: 'active', progress_version: 2, current_stop_id: 'old-stop' });
  await pending;
  assert.equal(store.current.id, 'b');
  assert.equal(store.progress.current_stop_id, 'new-stop');
  assert.deepEqual(store.budget, { known_minutes: 12 });
  assert.equal(store.error, '');
});

test('late budget refresh after a progress update cannot overwrite another tour', async () => {
  const late = deferred();
  store.progress = { status: 'active', progress_version: 1, current_stop_id: 'old-stop' };
  route = async config => {
    if (config.method === 'post') return { status: 'active', progress_version: 2, current_stop_id: 'old-stop' };
    if (config.url === '/tour-sessions/a/budget') return late.promise;
    throw new Error(config.url);
  };
  const pending = store.applyProgress({ type: 'set_remaining_budget', remaining_minutes: 30 });
  await tick();
  store.current = { id: 'b', version: 1 };
  store.progress = { status: 'active', progress_version: 7, current_stop_id: 'new-stop' };
  store.budget = { known_minutes: 12 };
  late.resolve({ known_minutes: 999 });
  await pending;
  assert.equal(store.progress.current_stop_id, 'new-stop');
  assert.deepEqual(store.budget, { known_minutes: 12 });
});

test('late start response does not update another selected tour', async () => {
  const late = deferred();
  store.progress = { status: 'not_started', progress_version: 0 };
  route = async config => {
    assert.equal(config.url, '/tour-sessions/a/start');
    return late.promise;
  };
  const pending = store.start(); await tick();
  store.current = { id: 'b', version: 1 };
  store.progress = { status: 'active', progress_version: 7, current_stop_id: 'new-stop' };
  store.budget = { known_minutes: 12 };
  late.resolve({ status: 'active', progress_version: 1, current_stop_id: 'old-stop' });
  await pending;
  assert.equal(store.progress.current_stop_id, 'new-stop');
  assert.deepEqual(store.budget, { known_minutes: 12 });
  assert.equal(store.error, '');
});

test('only the latest current-stop budget query can update the result, even when values repeat', async () => {
  const first = deferred(), second = deferred(), third = deferred();
  let calls = 0;
  store.progress = { status: 'active', progress_version: 1, current_stop_id: 'old-stop' };
  route = async () => [first, second, third][calls++].promise;
  const a = store.setCurrentStopRemainingMinutes(5); await tick();
  const b = store.setCurrentStopRemainingMinutes(10); await tick();
  const c = store.setCurrentStopRemainingMinutes(5); await tick();
  third.resolve({ known_minutes: 5 }); await c;
  second.resolve({ known_minutes: 10 }); await b;
  first.resolve({ known_minutes: 999 }); await a;
  assert.equal(store.currentStopRemainingMinutes, 5);
  assert.equal(store.budget.known_minutes, 5);
});
