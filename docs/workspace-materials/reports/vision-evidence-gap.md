# 视觉识景→RAG→答案证据关联缺口审计

2026-10-30，目标`integration-work/v01`。只读审计；只写本报告，未改业务/测试文件、未读秘钥、未调用付费服务。补充验证使用本地Vite SSR及fake SSE，不访问真实模型或数据库；这不是浏览器验收。

## 最关键且已复现的问题：历史答案引用被后续轮次的证据替换

`frontend/src/stores/chat.js:190-203`创建assistant消息只保存content/completion，sources事件`:247-251`仅写全局this.sources；新问题开始清空同一全局数组。没有给每条消息保存其sources或visionContext。

`frontend/src/views/tourist/ChatView.vue`的消息循环约110行把全部历史答案交给renderAnswer(content,...)；`:627-629`统一用`renderMarkdown(content,chatStore.sources,...)`。引用点击`:632-643`也只从当前全局sources找证据编号。`frontend/src/composables/useMarkdown.js:7-21`依赖传入sources将[证据1]转成标题/摘要，并不知消息所属轮次。

确定性复现（本轮已运行）：fake SSE第一轮返回照片A资料、answer“讲解[证据1]”，第二轮返回照片B资料且同样编号证据1。通过真实chat store连续sendMessage，输出：

```json
{
  "firstAnswer": "讲解[证据1]",
  "firstAnswerSources": null,
  "firstAnswerVision": null,
  "currentGlobalSources": [{"evidence_id":"证据1","title":"照片B对应资料","source":"fake-reference"}]
}
```

影响：游客先识A再识B，回看A答案时，其引用提示和跳转会使用B的资料；新轮次失败/无sources时旧引用又会变成未知来源。这不只影响视觉问答，所有多轮问答均受影响。后台单条chat_log保存sources不能自动修复当前前端引用，因为UI没有按chatLogId加载对应sources。优先级建议P2（证据归属错误，非仅缺少美化）。

最小测试与修复边界：

- 在`frontend/tests/chat-stream.test.mjs`新增两轮不同资料、同证据编号的回归测试，断言每条assistant.sources保持各自快照；开始下一轮、失败、停止后不能重写前轮sources。
- 为引用渲染/定位新增可单测helper，输入messageId+message.sources；测试A的[证据1]始终指A，B始终指B。ChatView使用消息对象而不是仅content/global sources。
- 来源面板需要选中消息的sources；点击引用时传入消息身份，不能只传“证据1”。保留全局sources作为当前流投影可兼容其他UI，但不能继续作为所有历史消息事实源。

## 当前链路及信息在哪一层丢失

| 层次 | 实际实现 | 缺失关联 |
|---|---|---|
| 图片选择/摄像头 | ChatView约1195-1245：本机File、object URL、request generation、幂等key；新图会清旧结果并取消旧请求 | 图像原文不被聊天持久化；这是合理隐私默认，不要求上传原图长期留存 |
| 视觉API | `backend/app/api/vision.py`校验体积、像素、MIME，调用视觉服务；`schemas/vision.py`返回摘要、候选、线索、confidence、provider | 返回结构没有analysis_id/image_digest/模型版本/时间等可用于同一次识别的稳定引用 |
| 转问答 | ChatView约1249-1259使用retrieval_query构造问题，明确“线索不作为事实来源”，并把完整result传options.visionContext | 用户消息未保存图片/识别结果的快照和归属ID；更换/清除图片后历史答案无法复核对应照片 |
| ChatRequest | `backend/app/schemas/chat.py:16-22`的VisionContext只保留摘要、候选、tags、query、confidence | API返回的provider没有进入该schema，Pydantic默认忽略额外字段；detected_text/query_hints也未单独保留 |
| RAG scope | `services/qa/pipeline.py:254-265`候选映射为source_entry_id；`guided_selector.py:303-314`返回第一个匹配候选 | 无按消息的识别来源记录、候选选择理由或歧义说明 |
| 答案记录 | `pipeline.py:963-1013`及`models/chat_log.py`记录query/answer/sources/session与语音元数据 | 无visual analysis ID、候选/置信快照、image digest；仅raw_query可能包含拼接后的线索，不能完整还原此次识别 |

识景幂等key目前是短期请求去重，不是可审计的跨接口analysis ID；不能当作照片→答案的持久绑定。

## 其他高价值缺口（静态确定，端到端待补测试）

### 低置信及多个候选仍可能直接硬限定检索

`pipeline.py:255-264`只判断candidate_attractions非空及当前scope为空，完全不读取confidence；`guided_selector.find_attraction_by_candidates`依次返回第一个匹配项。即便confidence=0或候选并列，也可把RAG范围直接锁到第一景点。视觉provider返回0.95只是其自报数值，不是校准准确率。

`schemas/chat.py`confidence没有ge/le约束，本轮纯schema验证确认`VisionContext(confidence=-1)`被接受为-1.0。虽然Qwen适配内部会clamp数值，但chat接口直接接受客户端构造VisionContext，不能依赖前一接口的约束替代后续校验。

测试建议：`backend/app/tests/test_pipeline_vision_evidence.py`用fake selector和捕获scope的fake RAG，覆盖confidence 0/低/高、两个候选、无匹配；低置信和歧义应走澄清/保持开放检索/显式不确定策略，策略由产品确定，不凭空设置一个未经评测的概率阈值。schema测试拒绝越界值。明确来源仍应是文档，不能把视觉候选当已证实事实。

### 已选景点/历史scope可能压过新照片，缺少冲突处理

同一pipeline分支要求resolved.scope为空；若游客已有A景点选择/历史范围，新照片识别出B时不会应用视觉scope。现有图像问答仍传interactionStore.selectionPayload及conversationContext，并没有在提交图片问答时显式处理两者冲突。视觉线索不应悄悄覆盖明确用户选择，但也不应无提示地继续讲旧景点。

测试建议：fake guided resolver给A scope、VisionContext给B，断言输出context含冲突提示或进入确认流程；用真实guided selector分别测“之前选择A→照片B”，不能只测手工空selection成功路径。后续改动须说明优先级，避免回归普通多轮上下文。

### 答案缓存键不包含视觉解析后的检索scope

`pipeline.py:310-316`仅把normalized_query、resolved.selection、namespace、audience传`guided_selector.build_selection_cache_key`；视觉分支保持resolved.selection不变，只替换scope和active_subject。键函数`:29-52`不含scope、候选或analysis ID。因此在归一化问题与selection相同而照片对应scope不同的情况下，有缓存混用风险。

当前ChatView通常把retrieval_query拼入问题，可能使两次normalized_query不同；不能据此宣称所有真实照片都会串缓存。应加针对性pipeline测试：两个vision_context候选分别映射A/B，使用相同通用query且rewrite fake固定归一化，第二轮不得复用A答案。若确认命中，再把实际resolved scope/受信解析结果纳入缓存身份，而非简单把未验证客户端字段全拼进key。

## 建议分层验收标准

1. 先修消息级sources归属；这项有确定双轮fake SSE复现，最容易形成稳定回归。
2. 增加轻量analysis ID或非可逆image digest及识别结果快照，绑定到请求/assistant/chat_log；是否保留原图由隐私与容量策略决定，本审计不建议默认永久保存照片。
3. 识别置信、歧义、与用户选择冲突应有显式策略和测试；保留“视觉线索不是文档事实”的边界。
4. 验证视觉scope的缓存隔离、资料撤回/更新后的可见性，再做真实浏览器两张图、多轮引用点击与清除图片回看验收。

本轮确定完成的是源码追踪、fake SSE双轮store复现及schema越界验证；尚未新增实现或测试文件、未做真实识景准确率评估，也没有宣称浏览器页面已验证。
