import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';

// This is a local, synthetic-data acceptance check. It deliberately crosses
// the admin origin and the tourist origin so a passing API check cannot hide a
// broken split deployment or an unpublished revision becoming visible.
const adminUrl = process.env.DEMO_ADMIN_URL || 'http://127.0.0.1:5174';
const touristUrl = process.env.DEMO_TOURIST_URL || 'http://127.0.0.1:5173';
const password = process.env.DEMO_ADMIN_PASSWORD;
if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1' || !password) {
  throw new Error('Set DEMO_SYNTHETIC_CONFIRM=1 and DEMO_ADMIN_PASSWORD for an isolated synthetic demo database.');
}

const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
});
const run = Math.random().toString(36).slice(2, 10);
const spotCode = `synthetic-${run}`;
const title = `合并验收演示景点${run}`;

try {
  const admin = await browser.newPage();
  const adminPage = await admin.goto(`${adminUrl}/`, { waitUntil: 'domcontentloaded' });
  assert.ok(adminPage?.ok(), `admin page returned ${adminPage?.status()}`);
  const adminApi = (path, options = {}) => admin.request.fetch(`${adminUrl}${path}`, options);
  const login = await adminApi('/api/auth/login', { method: 'POST', data: { password } });
  assert.ok(login.ok(), await login.text());
  const token = (await login.json()).token;
  assert.ok(token);
  const headers = { Authorization: `Bearer ${token}` };
  const payload = {
    title,
    category: '景点信息',
    aliases: [title],
    content: `${title}是虚构的本地合并验收景点，仅用于验证管理端发布到游客端目录。`,
    source: '本机合成演示资料，非真实景区信息',
    metadata_json: JSON.stringify({ attraction_id: spotCode }),
  };

  const draftResponse = await adminApi('/api/knowledge/', { method: 'POST', headers, data: payload });
  assert.equal(draftResponse.status(), 201, await draftResponse.text());
  const draft = await draftResponse.json();

  const before = await adminApi('/api/guide/bootstrap');
  assert.ok(before.ok(), await before.text());
  assert.equal((await before.json()).catalog.some((item) => item.spot_code === spotCode), false);

  const publicationResponse = await adminApi('/api/knowledge-publications/', {
    method: 'POST',
    headers,
    data: {
      idempotency_key: `merge-demo-${run}`,
      items: [{ entry_id: draft.id, revision_id: draft.draft_revision_id, expected_version: draft.lock_version }],
    },
  });
  assert.equal(publicationResponse.status(), 202, await publicationResponse.text());
  const publication = await publicationResponse.json();
  let job;
  for (let attempt = 0; attempt < 90; attempt += 1) {
    const status = await adminApi(`/api/knowledge-publications/${publication.id}`, { headers });
    assert.ok(status.ok(), await status.text());
    job = await status.json();
    if (['succeeded', 'failed'].includes(job.state)) break;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  assert.equal(job?.state, 'succeeded', JSON.stringify(job));

  const published = await adminApi('/api/guide/bootstrap');
  assert.ok(published.ok(), await published.text());
  const publishedCatalog = await published.json();
  const entry = publishedCatalog.catalog.find((item) => item.spot_code === spotCode);
  assert.ok(entry, 'published attraction is missing from guide bootstrap');
  assert.equal(entry.published_revision_id, draft.draft_revision_id);

  // The tourist site must see the same published revision through its own
  // origin. This catches proxy and app-boundary mistakes between the two apps.
  await admin.close();
  const tourist = await browser.newPage();
  const response = await tourist.goto(`${touristUrl}/tourist`, { waitUntil: 'domcontentloaded' });
  assert.ok(response?.ok(), `tourist page returned ${response?.status()}`);
  const touristBootstrap = await tourist.evaluate(async () => {
    const result = await fetch('/api/guide/bootstrap');
    return { status: result.status, body: await result.json() };
  });
  assert.equal(touristBootstrap.status, 200);
  const touristEntry = touristBootstrap.body.catalog.find((item) => item.spot_code === spotCode);
  assert.ok(touristEntry, 'tourist origin cannot read the published attraction');
  assert.equal(touristEntry.published_revision_id, draft.draft_revision_id);
  if (touristBootstrap.body.enabled) {
    await tourist.getByRole('combobox', { name: '选择情境讲解景点' }).waitFor({ timeout: 10_000 });
    assert.ok(await tourist.getByRole('option', { name: title }).count(), 'tourist UI did not render published catalog');
  }

  // Ask through the actual tourist page after publication. The demo provider
  // may fall back to an evidence answer, but the published revision must be
  // present in the returned source list.
  await tourist.getByRole('button', { name: '键盘输入' }).click();
  await tourist.locator('#tourist-query').fill(`${title}是什么？`);
  await tourist.locator('#tourist-query').press('Enter');
  const assistant = tourist.locator('.msg-item.assistant').last();
  await assistant.waitFor({ state: 'visible', timeout: 30_000 });
  await tourist.getByRole('button', { name: /参考资料/ }).click();
  await tourist.getByText('本机合成演示资料，非真实景区信息').waitFor({ timeout: 10_000 });
  console.log(`PASS: admin draft hidden; published revision ${draft.draft_revision_id} visible through tourist API/UI and ordinary Q&A sources (${spotCode})`);
} finally {
  await browser.close();
}
