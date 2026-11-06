import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const chatView = readFileSync(new URL('../src/views/tourist/ChatView.vue', import.meta.url), 'utf8');
const guideCss = readFileSync(new URL('../src/assets/guide-page.css', import.meta.url), 'utf8');

test('desktop map tool gets a dedicated wide rail at mid-size desktop widths', () => {
  assert.match(chatView, /'map-open'\s*:\s*activeTool\s*===\s*'map'/);
  const breakpointStart = guideCss.lastIndexOf('@media (min-width: 1000px) and (max-width: 1399px)');
  const mapRuleStart = guideCss.indexOf('.tourist-page .guide-layout.map-open', breakpointStart);
  const nextBreakpoint = guideCss.indexOf('@media', breakpointStart + 1);
  assert.ok(breakpointStart >= 0, 'mid-size desktop breakpoint exists');
  assert.ok(mapRuleStart > breakpointStart && (nextBreakpoint < 0 || mapRuleStart < nextBreakpoint), 'map rail override is scoped to mid-size desktops');
  assert.match(guideCss.slice(mapRuleStart), /^\.tourist-page \.guide-layout\.map-open \{ grid-template-columns: minmax\(300px,26vw\) minmax\(0,1fr\) 210px;/);
});
