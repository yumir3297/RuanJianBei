// Synthetic response shaped like a non-simulated warning; no real alert source is used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    if (path === '/api/guide/decision') return route.fulfill({ json: { available: true, decision: { action: 'none' }, safety_events: [{ event_id: 'synthetic-private-id', priority: 80, simulated: false, headline: '合成测试提醒' }] } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '开启情境导览' }).click();
  await page.getByText('合成测试提醒').waitFor();
  assert.equal(await page.evaluate(() => sessionStorage.getItem('a5-guide-real-safety-hold-v1')), '1');
  assert.equal(await page.evaluate(() => JSON.stringify(sessionStorage).includes('synthetic-private-id')), false);
  await page.reload();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor();
  await page.getByText('预警结束状态尚未核实').waitFor();
  assert.equal(await page.getByText('合成测试提醒').count(), 0);
  assert.equal(await page.getByRole('button', { name: '演示预警抢占' }).isDisabled(), true);
  console.log('Synthetic non-simulated response persists hold through reload without alert details: PASS');
} finally { await browser.close(); }
