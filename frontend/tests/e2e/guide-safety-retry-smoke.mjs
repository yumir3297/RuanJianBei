// Synthetic waiting-user proposal; the retry endpoint is intercepted.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
const snapshot = { schema_version: 2, constraints: {}, stops: [], legs: [], source: 'manual', source_references: [] };
const tour = { id: 'fixture', title: '模拟游览', version: 1, snapshot };
const proposal = { id: 'proposal', session_id: 'fixture', status: 'waiting_user', request_text: '模拟修改', execution_job_id: 'job', base_snapshot: snapshot };
let retries = 0;
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    if (path === '/api/tour-sessions/bootstrap') return route.fulfill({ json: { identity_id: 'fixture', csrf_token: 'fixture' } });
    if (path === '/api/tour-sessions') return route.fulfill({ json: { items: [tour] } });
    if (path === '/api/tour-sessions/fixture') return route.fulfill({ json: tour });
    if (path.endsWith('/executions/job/retry')) { retries++; return route.fulfill({ json: { status: 'queued' } }); }
    if (path.endsWith('/proposals/proposal')) return route.fulfill({ json: proposal });
    if (path.endsWith('/proposals')) return route.fulfill({ json: { items: [proposal] } });
    if (path.endsWith('/revisions')) return route.fulfill({ json: { items: [] } });
    if (path.endsWith('/progress')) return route.fulfill({ json: { status: 'not_started', progress_version: 0 } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '智能路线' }).click();
  await page.getByRole('button', { name: /模拟游览/ }).click();
  await page.getByLabel('总时长（分钟）').waitFor();
  await page.getByRole('button', { name: '收起导览工具' }).click();
  await page.getByRole('button', { name: /文字记录与资料/ }).click();
  const retry = page.getByRole('button', { name: '确认可能重复产生调用费用并重试' });
  await retry.waitFor();
  assert.equal(await retry.isEnabled(), true);
  await page.getByRole('button', { name: '收起文字记录' }).click();
  await page.getByRole('button', { name: '演示预警抢占' }).click();
  await page.getByRole('button', { name: '继续演示：模拟预警变化' }).click();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor();
  await page.getByRole('button', { name: /文字记录与资料/ }).click();
  assert.equal(await retry.isDisabled(), true);
  await page.getByRole('button', { name: '收起文字记录' }).click();
  await page.getByRole('button', { name: '我已了解' }).click();
  await page.getByRole('button', { name: /文字记录与资料/ }).click();
  assert.equal(await retry.isDisabled(), true);
  assert.equal(retries, 0);
  await page.getByRole('button', { name: '收起文字记录' }).click();
  await page.getByRole('button', { name: '继续演示（需再次确认）' }).click();
  await page.getByRole('button', { name: /文字记录与资料/ }).click();
  await retry.waitFor({ state: 'visible' });
  assert.equal(await retry.isEnabled(), true);
  await retry.click();
  await page.waitForFunction(() => document.querySelector('.itinerary-proposal') !== null);
  assert.equal(retries, 1);
  console.log('Retry blocked during simulated safety hold and allowed after explicit resume: PASS');
} finally { await browser.close(); }
