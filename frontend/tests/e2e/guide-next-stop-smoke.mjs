// All tours, catalog entries and answers below are synthetic API fixtures.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
const catalog = [{ spot_code: 'a', title: '合成甲景点', published_revision_id: 'rev-a' }, { spot_code: 'b', title: '合成乙景点', published_revision_id: 'rev-b' }];
const snapshot = { schema_version: 2, constraints: {}, legs: [], source: 'manual', source_references: [], stops: [
  { stop_id: 'a', kind: 'visit', name: '合成甲景点', spot_code: 'a', source_revision_id: 'rev-a' },
  { stop_id: 'b', kind: 'visit', name: '合成乙景点', spot_code: 'b', source_revision_id: 'rev-b' },
] };
const tour = { id: 'fixture', title: '模拟游览', version: 1, snapshot };
let streamPayload;
let digest = 'catalog-v1';
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog, catalog_digest: digest } });
    if (path === '/api/tour-sessions/bootstrap') return route.fulfill({ json: { identity_id: 'fixture', csrf_token: 'fixture' } });
    if (path === '/api/tour-sessions') return route.fulfill({ json: { items: [tour] } });
    if (path === '/api/tour-sessions/fixture') return route.fulfill({ json: tour });
    if (path.endsWith('/revisions') || path.endsWith('/proposals')) return route.fulfill({ json: { items: [] } });
    if (path.endsWith('/progress')) return route.fulfill({ json: { status: 'active', progress_version: 1, current_stop_id: 'a', status_by_stop: { a: 'current', b: 'pending' } } });
    if (path === '/api/quick-select/bootstrap') return route.fulfill({ json: { attractions: [{ id: 1, title: '合成甲景点' }], routes: [] } });
    if (path === '/api/chat/stream') { streamPayload = route.request().postDataJSON(); return route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'event: text\ndata: {"text":"合成回答","is_complete":true}\n\nevent: done\ndata: {}\n\n' }); }
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '智能路线' }).click();
  await page.getByRole('button', { name: /模拟游览/ }).click();
  await page.getByLabel('总时长（分钟）').waitFor();
  await page.getByRole('button', { name: '收起导览工具' }).click();
  await page.getByRole('button', { name: '演示雨天讲解适配' }).click();
  digest = 'catalog-v2';
  await page.getByRole('button', { name: '按演示情境生成讲解' }).click();
  await page.getByText('景点资料已更新，请重新评估当前情境。').waitFor();
  assert.equal(streamPayload, undefined);
  await page.getByRole('button', { name: '演示雨天讲解适配' }).click();
  await page.getByRole('button', { name: '按演示情境生成讲解' }).click();
  await page.waitForFunction(() => document.body.textContent.includes('合成回答'), null, { timeout: 10000 });
  assert.match(streamPayload.query, /下一待游览景点是合成乙景点/);
  assert.match(streamPayload.query, /不要臆造/);
  console.log('Changed catalog blocks old request; refreshed tour context reaches narration with next-stop caution: PASS');
} finally { await browser.close(); }
