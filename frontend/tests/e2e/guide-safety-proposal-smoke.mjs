// Synthetic API fixtures: no real tour or model request is used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
const tour = { id: 'fixture', title: '模拟游览', version: 1, snapshot: { schema_version: 2, constraints: {}, stops: [], legs: [], source: 'manual', source_references: [] } };
let proposals = 0;
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    if (path === '/api/tour-sessions/bootstrap') return route.fulfill({ json: { identity_id: 'fixture', csrf_token: 'fixture' } });
    if (path === '/api/tour-sessions') return route.fulfill({ json: { items: [tour] } });
    if (path === '/api/tour-sessions/fixture') return route.fulfill({ json: tour });
    if (path.endsWith('/proposals') && route.request().method() === 'POST') { proposals++; return route.fulfill({ status: 500 }); }
    if (path.endsWith('/revisions') || path.endsWith('/proposals')) return route.fulfill({ json: { items: [] } });
    if (path.endsWith('/progress')) return route.fulfill({ json: { status: 'not_started', progress_version: 0 } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '智能路线' }).click();
  await page.getByRole('button', { name: /模拟游览/ }).click();
  await page.getByLabel('总时长（分钟）').waitFor();
  await page.getByRole('button', { name: '收起导览工具' }).click();
  await page.getByRole('button', { name: '演示客流变化' }).click();
  const proposal = page.getByRole('button', { name: '生成路线调整提案' });
  await proposal.waitFor();
  assert.equal(await proposal.isEnabled(), true);
  await page.getByRole('button', { name: '演示预警抢占' }).click();
  await page.getByRole('button', { name: '继续演示：模拟预警变化' }).click();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor();
  if (await proposal.count()) assert.equal(await proposal.isDisabled(), true);
  await page.getByRole('button', { name: '键盘输入' }).click();
  await page.locator('#tourist-query').fill('修改行程增加休息');
  await page.locator('#tourist-query').press('Enter');
  await page.waitForTimeout(200);
  assert.equal(proposals, 0);
  console.log('Simulated safety hold prevents new itinerary proposal requests: PASS');
} finally { await browser.close(); }
