# 数字导游增强 — 轻量实施（3 项，2 小时）

> 审查了 implementation-plan-digital-guide-enhancement.md，方向全对但 9 天做不完。只做最有效果的 3 个轻量改动，不改 SSE 协议、不动数据库、不加依赖。

---

## A. 置信度→情感映射（backend/app/services/qa/pipeline.py，+30 行）

当前数字人永远 `emotion: "neutral"`。答对不笑，答不上不道歉。

在 `_emit_final_answer` 函数内，生成 avatar SSE 事件之前，新增一个映射函数：

```python
@staticmethod
def _answer_emotion(hit_level: str | None, source_count: int) -> str:
    if hit_level is None and source_count == 0:
        return "apology"
    if hit_level and hit_level.startswith("faq_"):
        return "happy"
    if hit_level == "rag_evidence" and source_count >= 2:
        return "happy"
    if hit_level == "rag_evidence":
        return "speaking"
    if hit_level in ("stub", "fallback"):
        return "apology"
    return "speaking"
```

然后在第 239 行附近（`yield StreamEvent(type="avatar", ...)` 这里）把 `emotion: "neutral"` 改为 `emotion: self._answer_emotion(hit_level, len(sources))`。

`hit_level` 变量来自 FAQ 匹配结果或 RAG 检索结果，已在 `_emit_final_answer` 上下文中有这个变量。`sources` 也已存在于该作用域。

前端 `useAvatar.js` 的 `handleAvatarEvent` 已支持 `happy`/`speaking`/`apology`，不需要改动。

---

## B. 讲解模式选择器（frontend/src/views/tourist/ChatView.vue，+20 行）

在 composer 区域的 `composer-context` 上方加一个讲解模式选择：

```html
<div class="explanation-mode">
  <el-radio-group v-model="explanationLevel" size="small">
    <el-radio-button value="child">儿童</el-radio-button>
    <el-radio-button value="adult">标准</el-radio-button>
    <el-radio-button value="expert">专业</el-radio-button>
  </el-radio-group>
</div>
```

```js
const explanationLevel = ref("adult");
```

在 `submitQuery` 函数中，`chatStore.sendMessage` 之前拼接：

```js
const levelPrefix = {
  child: '请用小朋友能听懂的语言解释：',
  adult: '',
  expert: '请给出专业详细的解释：',
}[explanationLevel.value];
submitQuery(levelPrefix + query.value);
```

快捷追问 `handleFollowup` 不受影响——它不走讲解模式前缀，保持原有行为。

CSS：

```css
.explanation-mode {
  margin-bottom: 8px;
}
```

---

## C. 拟人化图像响应（frontend/src/views/tourist/ChatView.vue，+5 行）

在 `vision-result-card` 中，候选景点标签后面加一行拟人化问候：

```html
<p v-if="visionResult?.candidate_attractions?.length" class="vision-greeting">
  我看到这是{{ visionResult.candidate_attractions[0] }}，让我为你介绍它！
</p>
```

```css
.vision-greeting {
  color: #0f766e;
  font-weight: 500;
  margin: 8px 0;
}
```

---

## 文件清单

```
backend/app/services/qa/pipeline.py    ← A. +30行
frontend/src/views/tourist/ChatView.vue ← B. +20行 + C. +5行
```

不改 SSE 协议，不改路由，不改后端 API，不新增依赖。

## 验证

```
cd frontend && npm.cmd run build
cd backend && .\.venv\Scripts\python.exe -m compileall .\app .\main.py -q
```
