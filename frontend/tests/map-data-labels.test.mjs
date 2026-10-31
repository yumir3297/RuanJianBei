import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const map = readFileSync(new URL('../src/views/tourist/MapView.vue', import.meta.url), 'utf8');
test('map does not present simulated crowd or unverified weather as live guide context', () => {
  assert.doesNotMatch(map, /结合当前客流与天气/);
  assert.doesNotMatch(map, /天气 · 实时|天气与景区颜色来自和风天气实时数据|正式版接入高德地图 MCP/);
  assert.match(map, /客流为演示数据/);
});
