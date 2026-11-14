// Writes synthetic data. Run only against a fresh isolated local demo database.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1' || !process.env.DEMO_ADMIN_PASSWORD) {
  throw new Error('Set DEMO_SYNTHETIC_CONFIRM=1 and DEMO_ADMIN_PASSWORD for an isolated demo database.');
}
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage();
try {
  const base = 'http://127.0.0.1:5174';
  const password = process.env.DEMO_ADMIN_PASSWORD;
  const login = await page.request.post(`${base}/api/auth/login`, { data: { password } });
  assert.ok(login.ok(), await login.text());
  const headers = { Authorization: `Bearer ${(await login.json()).token}` };
  const run = Date.now().toString();
  const question = `合成景点${run}在哪里`;
  let response = await page.request.post(`${base}/api/knowledge/`, { headers, data: {
    title: `合成景点${run}`, category: '景点信息', content: '虚构测试回答，仅用于隔离演示。',
    source: '本机合成资料', aliases: [], metadata_json: JSON.stringify({ attraction_id: `synthetic-${run}` }),
  } });
  assert.ok(response.ok(), await response.text());
  const entry = await response.json();
  response = await page.request.post(`${base}/api/knowledge-publications/`, { headers, data: {
    idempotency_key: `binding-${run}`, items: [{ entry_id: entry.id, revision_id: entry.draft_revision_id, expected_version: entry.lock_version }],
  } });
  assert.ok(response.ok(), await response.text());
  const job = await response.json();
  let state;
  for (let attempt = 0; attempt < 90; attempt++) {
    response = await page.request.get(`${base}/api/knowledge-publications/${job.id}`, { headers });
    assert.ok(response.ok(), await response.text());
    state = (await response.json()).state;
    if (['succeeded', 'failed'].includes(state)) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  assert.equal(state, 'succeeded');
  const caseId = `binding-${run}`;
  response = await page.request.post(`${base}/api/admin/guide-loop/observations`, { headers, data: {
    event_id: `event-${run}`, session_key: 'synthetic', cluster_id: caseId, text: question,
    poi_id: `synthetic-${run}`, target_id: 'target', result_code: 'unanswered', category: 'retrieval_gap',
    replay_id: 'synthetic', origin: 'synthetic',
  } });
  assert.ok(response.ok(), await response.text());
  await page.goto(base);
  await page.locator('input[type=password]').fill(password);
  await page.getByRole('button', { name: '登录管理后台' }).click();
  await page.waitForURL('**/admin/dashboard');
  await page.getByText('知识盲区', { exact: true }).first().click();
  await page.getByRole('button', { name: 'GuideLoop 试验' }).click();
  const card = page.locator('article.case-card').filter({ hasText: caseId });
  await card.waitFor();
  const field = label => card.locator('.el-form-item').filter({ hasText: label }).locator('input,textarea');
  await field('对象 ID').fill(`target-${run}`);
  await field('游客别名').fill(question);
  await field('人工审核后的回答').fill('虚构测试回答，仅用于隔离演示。');
  await field('证据 ID').fill('synthetic');
  await field('来源说明').fill('本机合成资料');
  await field('关联已发布知识').click();
  await page.getByRole('option', { name: new RegExp(`条目 ${entry.id} · 版本`) }).click();
  await card.getByText(entry.draft_revision_id, { exact: true }).waitFor();
  const draftSaved = page.waitForResponse(r => r.url().includes(`/cases/${caseId}/draft`) && r.request().method() === 'POST');
  await card.getByRole('button', { name: '保存草稿' }).click();
  response = await draftSaved;
  assert.ok(response.ok(), await response.text());
  await card.getByRole('button', { name: '技术路由验证' }).click();
  await card.getByText('我已人工核对来源确实支持该回答').waitFor();
  await card.getByText('我已人工核对来源确实支持该回答').click();
  await card.getByRole('button', { name: '发布版本' }).click();
  await page.getByText(/已发布 gl-/).waitFor();
  await card.getByRole('button', { name: '游客真实 SSE 复测' }).click();
  await card.getByText('虚构测试回答，仅用于隔离演示。', { exact: true }).waitFor({ timeout: 30000 });
  await card.getByRole('button', { name: '复测通过（人工核对）' }).click();
  await page.waitForFunction(() => [...document.querySelectorAll('.el-message')].some(e => e.textContent.includes('closed')));
  const touristBody = { query: question, session_id: `visitor-${run}`, text_only: true,
    selection: { mode: 'attraction', attraction_id: entry.id } };
  const touristAnswer = await page.request.post('http://127.0.0.1:5173/api/chat/stream', { data: touristBody });
  assert.ok(touristAnswer.ok(), await touristAnswer.text());
  const touristText = await touristAnswer.text();
  assert.ok(touristText.includes('虚构测试回答，仅用于隔离演示。') && touristText.includes('guide_loop_answer'), touristText);
  const tourist = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await tourist.goto('http://127.0.0.1:5173/tourist');
  await tourist.getByRole('button', { name: '键盘输入' }).click();
  const stream = tourist.waitForResponse(r => r.url().includes('/api/chat/stream') && r.request().method() === 'POST');
  await tourist.locator('#tourist-query').fill(`${question}呢`);
  await tourist.locator('#tourist-query').press('Enter');
  const uiResponse = await stream;
  assert.ok(uiResponse.ok());
  const uiText = await uiResponse.text();
  assert.ok(uiText.includes('guide_loop_answer') && uiText.includes('虚构测试回答，仅用于隔离演示。'), uiText);
  if (await tourist.locator('#text-panel-trigger').getAttribute('aria-expanded') !== 'true') {
    await tourist.locator('#text-panel-trigger').click();
  }
  await tourist.getByLabel('对话记录').getByText('虚构测试回答，仅用于隔离演示。', { exact: false }).waitFor({ timeout: 30000 });
  await tourist.close();
  response = await page.request.delete(`${base}/api/knowledge/${entry.id}`, { headers });
  assert.ok(response.ok(), await response.text());
  const afterWithdrawal = await page.request.post('http://127.0.0.1:5173/api/chat/stream', { data: touristBody });
  assert.ok(!(await afterWithdrawal.text()).includes('虚构测试回答，仅用于隔离演示。'));
  response = await page.request.post(`${base}/api/admin/guide-loop/replay`, { headers, data: {
    query: question, session_id: `admin-stale-${run}`, text_only: true, guide_loop: { poi_id: 'bathing' },
  } });
  assert.ok(response.ok(), await response.text());
  assert.match(await response.text(), /关联的知识版本已更新或下架/);
  console.log('PASS: publish and confirm K01-bound answer, tourist SSE, withdrawal and stale answer rejection');
} finally {
  await browser.close();
}
