// Writes synthetic data; use only a fresh isolated local database and synthetic DOCX.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1' || !process.env.DEMO_ADMIN_PASSWORD || !process.env.DEMO_DOCX_PATH) {
  throw new Error('Set DEMO_SYNTHETIC_CONFIRM=1, DEMO_ADMIN_PASSWORD and DEMO_DOCX_PATH for an isolated demo.');
}
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
try {
  const base = 'http://127.0.0.1:5174';
  const password = process.env.DEMO_ADMIN_PASSWORD;
  await page.goto(base);
  await page.locator('input[type=password]').fill(password);
  await page.getByRole('button', { name: '登录管理后台' }).click();
  await page.waitForURL('**/admin/dashboard');
  await page.getByText('知识管理', { exact: true }).first().click();
  const panel = page.locator('.import-panel');
  await panel.getByText('批量导入 PDF / JSON / DOCX / XLSX').waitFor();
  await panel.getByText(/当前服务器每批最多/).waitFor();
  await panel.locator('input[type=file]').setInputFiles(process.env.DEMO_DOCX_PATH);
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/knowledge-imports/') && response.request().method() === 'POST');
  await panel.getByRole('button', { name: '上传并解析' }).click();
  const upload = await responsePromise;
  assert.equal(upload.status(), 202, await upload.text());
  const batchId = (await upload.json()).id;
  await panel.locator('.job-card').getByText('drafts_created', { exact: true }).waitFor({ timeout: 30000 });
  assert.match(await panel.locator('.job-meta').innerText(), /草稿条目：1/);
  await page.getByText('合成导入景点', { exact: true }).first().waitFor();

  const auth = await page.request.post(`${base}/api/auth/login`, { data: { password } });
  assert.ok(auth.ok());
  const headers = { Authorization: `Bearer ${(await auth.json()).token}` };
  const batchResponse = await page.request.get(`${base}/api/knowledge-imports/${batchId}`, { headers });
  assert.ok(batchResponse.ok());
  const job = (await batchResponse.json()).jobs[0];
  assert.equal(job.state, 'succeeded');
  assert.equal(job.knowledge_entry_ids.length, 1);
  const response = await page.request.get(`${base}/api/knowledge/`, { headers });
  assert.ok(response.ok());
  const entry = (await response.json()).find(item => item.id === job.knowledge_entry_ids[0]);
  assert.ok(entry?.draft_revision_id);
  assert.equal(entry.title, '合成导入景点');
  assert.equal(entry.published_revision_id, null);
  assert.match(entry.content, /合成资料/);
  assert.match(entry.content, /示例字段 \| 演示内容/);
  assert.match(entry.source, /synthetic\.docx/);
  let savedDraftId = null;
  if (process.env.DEMO_TEST_UNDERSTANDING === '1') {
    const row = page.locator('.el-table__body-wrapper tr').filter({ hasText: '合成导入景点' }).first();
    await row.getByRole('button', { name: '理解预览' }).click();
    await page.locator('.el-message-box__btns button').last().click();
    const preview = page.getByRole('dialog', { name: '知识理解候选（待人工核对）' });
    await preview.getByText('本地演示模式：仅摘录原文，未调用 AI 模型。').waitFor();
    assert.match(await preview.innerText(), /合成资料/);
    assert.match(await preview.innerText(), /引用原文/);
    await preview.getByRole('button', { name: '带入编辑草稿' }).click();
    const editor = page.getByRole('dialog', { name: '编辑知识条目' });
    await editor.waitFor();
    assert.match(await editor.locator('textarea').inputValue(), /合成资料/);
    await editor.getByRole('button', { name: '取消' }).click();
    const after = await page.request.get(`${base}/api/knowledge/`, { headers });
    const unchanged = (await after.json()).find(item => item.id === entry.id);
    assert.equal(unchanged.draft_revision_id, entry.draft_revision_id);
    assert.equal(unchanged.published_revision_id, null);
    console.log('PASS: stub preview displays source, transfers to editor and cancel leaves draft unchanged');
    await row.getByRole('button', { name: '理解预览' }).click();
    await page.locator('.el-message-box__btns button').last().click();
    await preview.getByText('本地演示模式：仅摘录原文，未调用 AI 模型。').waitFor();
    await preview.getByRole('button', { name: '带入编辑草稿' }).click();
    await editor.waitFor();
    await editor.locator('textarea').fill('人工核对后的合成候选内容。');
    const savedResponse = page.waitForResponse(response => response.url().endsWith(`/api/knowledge/${entry.id}`) && response.request().method() === 'PUT');
    await editor.getByRole('button', { name: '提交' }).click();
    const saved = await savedResponse;
    assert.ok(saved.ok(), await saved.text());
    const updated = await saved.json();
    assert.notEqual(updated.draft_revision_id, entry.draft_revision_id);
    assert.equal(updated.published_revision_id, null);
    assert.equal(updated.content, '人工核对后的合成候选内容。');
    assert.equal(updated.source_document_version_id, entry.source_document_version_id);
    savedDraftId = updated.draft_revision_id;
    console.log('PASS: explicit save creates a new source-linked draft without publishing');
  }
  const chat = await page.request.post('http://127.0.0.1:8000/api/chat/stream', { data: { query: '合成导入景点是什么？', session_id: 'synthetic-docx-check', text_only: true }, timeout: 30000 });
  assert.ok(chat.ok());
  const body = await chat.text();
  assert.ok(!body.includes(entry.draft_revision_id), 'unpublished revision must not appear in visitor stream');
  if (savedDraftId) assert.ok(!body.includes(savedDraftId), 'saved candidate draft must not appear in visitor stream');
  console.log('PASS: DOCX browser upload creates source-linked unpublished draft; visitor stream excludes its revision');
} finally { await browser.close(); }
