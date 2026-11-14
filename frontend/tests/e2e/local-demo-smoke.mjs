import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {})});
const password=process.env.DEMO_ADMIN_PASSWORD;
if (!password || process.env.DEMO_SYNTHETIC_CONFIRM !== '1') { await browser.close(); throw new Error('Set DEMO_ADMIN_PASSWORD and DEMO_SYNTHETIC_CONFIRM=1; use only an isolated synthetic demo database.'); }
const admin=await browser.newPage();
try {
 const caseId='local-demo-'+Date.now();
 await admin.goto('http://127.0.0.1:5174/');
 await admin.locator('input[type=password]').fill(password);
 await admin.getByRole('button',{name:'登录管理后台'}).click();
 await admin.waitForURL('**/admin/dashboard');
 const login=await admin.request.post('http://127.0.0.1:5174/api/auth/login',{data:{password}}); const token=(await login.json()).token;
 assert.ok(token);
 const observation={event_id:'smoke-'+Date.now(),session_key:'synthetic-session',cluster_id:caseId,text:'莲花里是谁',poi_id:'bathing',target_id:'prince',unit_id:'demo',evidence_ids:['synthetic'],result_code:'unanswered',category:'retrieval_gap',replay_id:'demo-replay',origin:'synthetic'};
 const created=await admin.request.post('http://127.0.0.1:5174/api/admin/guide-loop/observations',{headers:{Authorization:`Bearer ${token}`},data:observation}); assert.ok(created.ok(),await created.text());
 await admin.getByText('知识盲区',{exact:true}).first().click();
 await admin.getByRole('button',{name:'GuideLoop 试验'}).click();
 const card=admin.locator('article.case-card').filter({hasText:caseId}); await card.waitFor();
 const field=(label)=>card.locator('.el-form-item').filter({hasText:label}).locator('input,textarea');
 await field('游客别名').fill('莲花里是谁'); await field('人工审核后的回答').fill('演示资料：莲花中有人物造像。'); await field('证据 ID').fill('synthetic-demo'); await field('来源说明').fill('本机合成演示资料，非真实来源');
 await card.getByRole('button',{name:'保存草稿'}).click(); await card.getByRole('button',{name:'技术路由验证'}).waitFor({state:'visible'}); await admin.waitForTimeout(500); await card.getByRole('button',{name:'技术路由验证'}).click();
 await card.getByText('我已人工核对来源确实支持该回答').click(); await card.getByRole('button',{name:'发布版本'}).click(); await admin.waitForTimeout(1000);
 await card.getByRole('button',{name:'游客真实 SSE 复测'}).click(); await card.getByText('新会话 SSE 复测').waitFor({timeout:30000});
 assert.match(await card.innerText(), /演示资料：莲花中有人物造像/);
 await card.getByRole('button',{name:'复测通过（人工核对）'}).click();
 await admin.waitForFunction(() => [...document.querySelectorAll('.el-message')].some(e => e.textContent.includes('closed')));
 console.log('GuideLoop synthetic case publish, replay, confirmation: PASS');
 const guest=await browser.newPage();await guest.goto('http://127.0.0.1:5173/tourist');await guest.getByRole('button',{name:'演示预警抢占'}).click();await guest.getByRole('button',{name:'继续演示：模拟预警变化'}).click();assert.ok(await guest.getByText('安全提醒期间，普通讲解已暂停').isVisible());await guest.getByRole('button',{name:'我已了解'}).click();assert.ok(await guest.getByText('安全提醒期间，普通讲解已暂停').isVisible());await guest.getByRole('button',{name:'继续演示（需再次确认）'}).click();assert.equal(await guest.getByText('安全提醒期间，普通讲解已暂停').count(),0);console.log('CASS simulated warning and explicit resume: PASS');
} finally { await browser.close(); }
