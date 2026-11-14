// Writes synthetic data; run only against an isolated local server and synthetic scan.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright-core';

if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1' || !process.env.DEMO_ADMIN_PASSWORD || !process.env.DEMO_SCAN_PATH) {
  throw new Error('Set DEMO_SYNTHETIC_CONFIRM=1, DEMO_ADMIN_PASSWORD and DEMO_SCAN_PATH for an isolated demo.');
}
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
try {
  const base = 'http://127.0.0.1:5174', password = process.env.DEMO_ADMIN_PASSWORD;
  await page.goto(base);
  await page.locator('input[type=password]').fill(password);
  await page.getByRole('button', { name: '登录管理后台' }).click();
  await page.waitForURL('**/admin/dashboard');
  await page.getByText('知识管理', { exact: true }).first().click();
  const panel = page.locator('.import-panel');
  await panel.getByText(/当前服务器每批最多/).waitFor();
  await panel.locator('input[type=file]').setInputFiles(process.env.DEMO_SCAN_PATH);
  const uploadResponse = page.waitForResponse(response => response.url().endsWith('/api/knowledge-imports/') && response.request().method() === 'POST');
  await panel.getByRole('button', { name: '上传并解析' }).click();
  const upload = await uploadResponse;
  assert.equal(upload.status(), 202);
  const batchId = (await upload.json()).id;
  await panel.locator('.job-card').getByText('drafts_created', { exact: true }).waitFor({ timeout: 90000 });
  const login = await page.request.post(`${base}/api/auth/login`, { data: { password } });
  assert.ok(login.ok());
  const headers = { Authorization: `Bearer ${(await login.json()).token}` };
  const batch = await (await page.request.get(`${base}/api/knowledge-imports/${batchId}`, { headers })).json();
  assert.equal(batch.jobs[0].state, 'succeeded');
  assert.equal(batch.jobs[0].knowledge_entry_ids.length, 1);
  const entries = await (await page.request.get(`${base}/api/knowledge/`, { headers })).json();
  const entry = entries.find(item => item.id === batch.jobs[0].knowledge_entry_ids[0]);
  assert.ok(entry?.draft_revision_id && !entry.published_revision_id);
  assert.match(entry.content, /合成景点资料/);
  assert.equal(JSON.parse(entry.metadata_json).extraction_method, 'ocr_mixed');
  await page.getByText('含 OCR 识别内容，可能有错漏，请对照原文件核对。').first().waitFor();
  const row = page.locator('.el-table__body-wrapper tr').filter({ hasText: '合成景点资料' }).first();
  const downloadPromise = page.waitForEvent('download');
  await row.getByRole('button', { name: '下载原件' }).click();
  const download = await downloadPromise;
  assert.match(download.suggestedFilename(), /\.pdf$/);
  assert.deepEqual(await readFile(await download.path()), await readFile(process.env.DEMO_SCAN_PATH));
  const chat = await page.request.post('http://127.0.0.1:8000/api/chat/stream', { data: { query: '合成景点资料是什么？', session_id: 'synthetic-ocr-check', text_only: true } });
  assert.ok(chat.ok());
  assert.ok(!(await chat.text()).includes(entry.draft_revision_id));
  console.log('PASS: Chinese OCR creates an unpublished draft and downloaded source matches upload');
} finally { await browser.close(); }
