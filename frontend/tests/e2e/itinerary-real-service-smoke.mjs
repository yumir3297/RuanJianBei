// Writes a synthetic tour: run only against an isolated local demo database.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1') throw new Error('Use only an isolated synthetic database and set DEMO_SYNTHETIC_CONFIRM=1');
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
try {
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '智能路线' }).click();
  await page.getByRole('button', { name: '新建空白游览' }).click();
  await page.getByRole('button', { name: '升级为 V2 行程' }).click();
  await page.getByLabel('总时长（分钟）').waitFor({ state: 'visible', timeout: 10000 });
  await page.getByRole('button', { name: '收起导览工具' }).click();
  await page.getByRole('button', { name: '键盘输入' }).click();
  await page.locator('#tourist-query').fill('演示：行程增加十分钟休息');
  await page.locator('#tourist-query').press('Enter');
  await page.getByText('本地模拟演示：此提案由固定演示规则生成，不是真实 AI 结果。').waitFor({ timeout: 30000 });
  const applied = page.waitForResponse(response => response.url().includes('/proposals/') && response.url().endsWith('/apply') && response.request().method() === 'POST');
  await page.getByRole('button', { name: '确认并保存新版本' }).click();
  assert.equal((await applied).status(), 200);
  await page.getByRole('button', { name: '智能路线' }).click();
  const stop = page.locator('.itinerary-stop-row').filter({ hasText: '演示休息' });
  await stop.getByText('此停留点来自本地模拟演示').waitFor();
  assert.equal(await stop.count(), 1);
  console.log('Real API + independent worker + synthetic provider: proposal, confirmation and route label PASS');
} finally { await browser.close(); }
