// Isolated presentation check: all API results below are synthetic fixtures.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

const snapshot = { schema_version: 2, constraints: {}, legs: [], source: 'manual', source_references: [], stops: [
  { stop_id: '00000000-0000-0000-0000-000000000001', kind: 'rest', name: '演示休息', duration_minutes: 10, duration_basis: 'estimate', evidence: [], locked_fields: [], created_by: 'demo_synthetic' },
  { stop_id: '00000000-0000-0000-0000-000000000002', kind: 'rest', name: '普通休息', duration_minutes: 10, duration_basis: 'user', evidence: [], locked_fields: [], created_by: 'manual' },
] };
const tour = { id: 'fixture', title: '模拟游览', version: 2, snapshot };
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/tour-sessions/bootstrap') return route.fulfill({ json: { identity_id: 'fixture', csrf_token: 'fixture' } });
    if (path === '/api/tour-sessions') return route.fulfill({ json: { items: [tour] } });
    if (path === '/api/tour-sessions/fixture') return route.fulfill({ json: tour });
    if (path.endsWith('/revisions') || path.endsWith('/proposals')) return route.fulfill({ json: { items: [] } });
    if (path.endsWith('/progress')) return route.fulfill({ json: { status: 'not_started', progress_version: 0 } });
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: false, demo_enabled: false, catalog: [] } });
    return route.fulfill({ status: 404, json: { detail: 'fixture unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '智能路线' }).click();
  await page.getByRole('button', { name: /模拟游览/ }).click();
  const synthetic = page.locator('.itinerary-stop-row').filter({ hasText: '演示休息' });
  const manual = page.locator('.itinerary-stop-row').filter({ hasText: '普通休息' });
  await synthetic.getByText('此停留点来自本地模拟演示').waitFor();
  assert.equal(await manual.getByText('此停留点来自本地模拟演示').count(), 0);
  console.log('Synthetic stop is visibly labeled; manual stop is not: PASS');
} finally { await browser.close(); }
