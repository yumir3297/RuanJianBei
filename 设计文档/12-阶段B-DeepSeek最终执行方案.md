# 阶段 B：真实多模态 LLM 与证据回答 — 最终执行方案（DeepSeek API）

> 日期：2026-06-15
> 状态：方案已完成，等待用户确认 API Key 和费用上限后开始编码
> 主线依据：`设计文档/10-最终总体设计与开发主线.md`
> API 供应商：DeepSeek（文本问答）+ 待定（图片识别）

---

## 一、关键事实与决策

### 1.1 DeepSeek API 能力

| 项目 | 实际情况 |
|------|---------|
| API 地址 | `https://api.deepseek.com` |
| 接口格式 | OpenAI-compatible（`/v1/chat/completions`） |
| 推荐模型 | `deepseek-chat`（DeepSeek-V3，待迁移到 `deepseek-v4-flash`） |
| 上下文长度 | 1M tokens |
| 输入价格 | $0.14 / 百万 token（缓存命中更低） |
| 输出价格 | $0.28 / 百万 token（含思维链） |
| 视觉能力 | ❌ **不支持图片识别** |

### 1.2 关键决策

| 决策 | 结论 |
|------|------|
| 文本 LLM | **DeepSeek API (`deepseek-chat`)**，OpenAI 兼容，当前代码零改造 |
| 图片识别 | **本轮不实现**。DeepSeek API 不支持 Vision。视觉识别改为独立 Phase B-Vision，需另选供应商 |
| 多模态要求满足方式 | 文本问答 + 图片识别（待视觉供应商确定后追加）。在完成前，不宣称已满足多模态要求 |

### 1.3 为什么图片识别单独拆出去

1. DeepSeek API 不支持视觉。强行混用两个 API 供应商会在同一个 `OpenAICompatibleLLMService` 中引入两种不同的请求格式
2. 图片识别的业务逻辑（候选匹配 → SelectionContext 转换 → 游客确认）是独立闭环，不阻塞文本问答链路
3. 赛题要求"至少 1 个多模态大模型真实参与业务"——文本 LLM 本身不算多模态。图片识别必须在文本链路稳定后再接，避免两边都不稳

---

## 二、修正后的切片（3 个，从原计划 4 个精简）

```
B1：真实文本 LLM + 证据回答     ← 仅 DeepSeek API
B2：端到端评测（30→100 题）     ← B1 完成后立即启动
B3：图片识别（独立 Phase）      ← 等视觉供应商确定后单独启动
```

### 2.1 B1：真实文本 LLM 与证据回答

#### 目标

将 `OpenAICompatibleLLMService` 从硬编码占位替换为真实 DeepSeek API 调用。

#### 具体修改

**Step 1：证据编号 Prompt 构造**

在 `pipeline.py` 中构造 evidence-numbered context，传入 LLM：

```python
# pipeline.py — 改动
evidence_parts = []
for idx, doc in enumerate(documents, start=1):
    evidence_parts.append(
        f"[证据{idx}] 来源：{doc.source} | {doc.title}\n{doc.content}"
    )
evidence_context = "\n---\n".join(evidence_parts)
```

System Prompt（写入 `config.py` 的 `llm_system_prompt` 配置项，不写死在代码里）：

```text
你是"灵山胜境"景区的AI数字导游。

## 铁律
1. 只能使用【参考资料】中的信息，每个关键事实必须标注证据编号（如"[证据1]"）。
2. 参考资料中没有的信息，必须明确说"根据现有景区资料，暂时无法确定"。
3. 绝不编造数据、日期、价格、时间。
4. 回答开头直接回答核心问题，中间提供2-3个关键细节，结尾引导继续提问。

## 当前参考资料
{evidence_context}

## 在回答前检查：
- 每个陈述是否都能在参考资料中找到？
- 是否有编造的数据或事实？有则删除。
- 关键事实是否标注了证据编号？
```

**Step 2：替换 stub → 真实 API 调用**

在 `openai_compatible.py` 中新增真实 HTTP 流式实现：

```python
import httpx
import json

class OpenAICompatibleLLMService(BaseLLMService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._stub = (settings.llm_provider == "stub")

    async def stream_generate(self, query, documents):
        if not documents:
            yield self._no_evidence_response()
            return

        if self._stub:
            async for token in self._stub_stream(query, documents):
                yield token
            return

        messages = [
            {"role": "system", "content": self.settings.llm_system_prompt},
            {"role": "user", "content": f"问题：{query}\n\n参考资料：\n{evidence_context}"},
        ]

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0)
        ) as client:
            async with client.stream(
                "POST",
                f"{self.settings.llm_base_url}/v1/chat/completions",
                json={
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.3,           # 低温度降低编造倾向
                },
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
            ) as response:
                if response.status_code != 200:
                    yield self._error_response(response.status_code)
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
```

**Step 3：超时与降级**

```python
# 连接超时 5s，总超时 30s
timeout=httpx.Timeout(30.0, connect=5.0)

# API 返回非 200 → 降级
if response.status_code != 200:
    yield self._error_response(response.status_code)
    return
```

降级策略（三层，优先级从高到低）：

1. **DeepSeek API 正常** → 流式回答
2. **API 超时/报错** → 返回"AI 服务暂时繁忙，请稍后再试。您可以先查看：景点介绍 | 路线推荐 | 实用信息"
3. **API Key 未配置（llm_provider="stub"）** → 保持现有占位行为（方便开发调试）

**Step 4：配置文件更新**

`.env.example`：
```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_SYSTEM_PROMPT=你是灵山胜境景区的AI数字导游...
```

**Step 5：chat.py 不动**

现状 `build_pipeline()` 已经传了 `settings`，不需要改。LLM 配置完全由 `.env` 驱动。

#### 改动清单

```
修改 (4):
├── backend/app/services/llm/openai_compatible.py    # stub → 真实 HTTP 流式
├── backend/app/services/qa/pipeline.py               # 证据编号构造
├── backend/app/core/config.py                        # +llm_system_prompt 配置项
└── backend/.env.example                              # LLM 配置项补全

不改：
├── backend/app/schemas/chat.py                       # SSE 事件格式不变
├── backend/app/api/chat.py                           # pipeline 构造不变
├── 前端任何文件                                       # SSE 消费端不变
└── backend/requirements.txt                          # httpx 已有
```

#### 验收标准

1. `llm_provider=stub` 行为不变（开发模式可用）
2. `llm_provider=deepseek` + 正确 API Key → 流式返回真实回答
3. 回答中关键事实包含证据编号
4. 问资料中不存在的信息 → 回答含"暂时无法确定"
5. API Key 错误 → 不崩溃，返回友好降级提示
6. 网络不通 → 不崩溃，返回友好降级提示
7. 后端回归测试通过（stub 模式测试不受影响）
8. SSE 输出格式不变，前端不需要任何修改

---

### 2.2 B2：端到端评测（30→100 题）

#### 目标

B1 完成后立即跑评测，验证"准确率 ≥ 90%"这个硬指标。

#### 具体内容

1. 从现有 30 题检索评测集扩展到 100 题端到端问答集：
   - FAQ 类 40 题
   - 知识类 40 题
   - 推荐类 20 题
2. 每道题记录：query、expected_answer、must_contain 关键词、source_doc
3. 评测指标：
   - must_contain 命中率（主判定）
   - 无证据坦承率（必须 = 100%）
   - 来源展示覆盖率（必须 = 100%）
   - LLM 首 token P50/P95
   - 全链路 P50/P95
4. 输出评测报告，与阶段 A 基线对比

#### 改动清单

```
修改:
├── eval/testset/*.json              # 从 30 题扩展到 100 题
├── eval/scripts/regression.py       # 扩展为端到端评测
└── eval/reports/end_to_end_v1.json  # 新增报告
```

---

### 2.3 B3：图片识别（独立 Phase，本轮不入）

#### 为什么拆出去

| 问题 | 说明 |
|------|------|
| DeepSeek 不支持 Vision | 必须另选供应商（通义千问 VL / StepFun / 本地模型） |
| 前端改动量大 | 需要文件上传组件、拍摄按钮、识别中状态、候选选择 UI |
| B1+B2 已覆盖硬指标主体 | 准确率评测在文本链路上验证，图片识别是加分项 |

#### 后续启动条件

1. 视觉模型供应商确定
2. 开发机确认有可用的 Vision API（或 GPU）
3. B1+B2 文本链路稳定

---

## 三、30 分钟接入验证计划（先跑通再正式改）

在正式修改 `openai_compatible.py` 之前，先用一个独立脚本验证 DeepSeek API 可用性：

```python
# backend/test_deepseek_api.py（临时文件，验证后删除）
import httpx
import json
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST", "https://api.deepseek.com/v1/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "灵山大佛有多高？请用一句话回答。"}],
                "stream": True,
            },
            headers={"Authorization": "Bearer sk-your-key", "Content-Type": "application/json"},
        ) as response:
            print(f"Status: {response.status_code}")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                    print(content, end="", flush=True)

asyncio.run(test())
```

验收标准：
1. HTTP 200
2. 逐字流式输出
3. Token count 在响应头中可见（用于估算费用）

---

## 四、费用预估

| 场景 | 用量 | 预估费用 |
|------|------|---------|
| 单次问答（输入 2000 token + 输出 500 token） | ~2500 token | **约 ¥0.003**（不到 1 分钱） |
| 100 题评测（同上 × 100 次） | ~250K token | **约 ¥0.3**（3 毛钱） |
| 开发调试（每天 200 次问答） | ~500K token/day | **约 ¥0.5/天** |

DeepSeek API 计费单位为百万 token。对于一个景区知识库（66 个 chunk，平均 300 token/chunk + System Prompt 约 200 token = 每次输入约 2000 token），费用完全可以忽略。

---

## 五、与 Codex 原方案的关键差异

| 维度 | Codex 原方案 | 本方案 |
|------|------------|--------|
| LLM 供应商 | "阿里云百炼通义视觉"（未锁定） | **DeepSeek API (`deepseek-chat`)**（已确定） |
| 图片识别 | 与文本 LLM 同阶段实现（B2+B3） | **独立 Phase，本轮不入** |
| 证据方案 | "证据编号 Prompt"（未展开） | **具体 Prompt 模板 + pipeline 构造方式**（已展开） |
| 评测 | B4 最后做 | **B2 紧随 B1 立即启动** |
| 切片数 | 4 个 | **3 个（B1→B2→B3）** |
| LLM 调用方式 | 未说明是否复用现有 SSE 格式 | **复用现有 SSE，前端零改动** |

---

## 六、改动汇总

```
B1 改动：
├── backend/app/services/llm/openai_compatible.py     stub → 真实 HTTP 流式
├── backend/app/services/qa/pipeline.py                证据编号构造（传入 LLM 前）
├── backend/app/core/config.py                        + llm_system_prompt 配置项
├── backend/.env.example                               LLM 配置补全（deepseek）

B2 改动：
├── eval/testset/*.json                                30 题 → 100 题
├── eval/scripts/regression.py                         端到端评测适配
└── eval/reports/end_to_end_v1.json                    新增

不改（4 个零改动保证）：
├── 前端 0 改动（SSE 格式不变）
├── chat.py 0 改动（构造逻辑在 OpenAICompatibleLLMService 内部）
├── schemas/chat.py 0 改动
└── requirements.txt 0 改动（httpx 已有）
```

---

## 七、需要用户确认的 3 件事

1. **DeepSeek API Key** 是否已获取？Base URL 是否为 `https://api.deepseek.com`？
2. **费用上限**：B1 开发测试预计每天不超过 ¥1，是否接受？
3. **图片识别延后**：是否同意将图片识别从阶段 B 拆出，作为独立 Phase 在本轮文本链路稳定后再启动？

---

## 八、开始编码顺序

```
Step 1（5 分钟）：在 .env 中填入 DeepSeek API Key，跑独立验证脚本确认可用
Step 2（30 分钟）：改 openai_compatible.py，替换 stub 为真实 HTTP 流式调用
Step 3（15 分钟）：改 pipeline.py + config.py，构造证据编号 Prompt
Step 4（15 分钟）：跑后端回归测试 + 真实 SSE 冒烟测试
Step 5（60 分钟）：评测集扩展 30→100 题 + 端到端评测脚本
```

**总计约 2 小时完成 B1+B2。**
