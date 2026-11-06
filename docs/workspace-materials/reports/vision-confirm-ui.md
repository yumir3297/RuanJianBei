# 视觉识景：游客确认交互调查

2026-10-30；对 `integration-work/v01` 静态审查，未访问真实模型、数据库或浏览器。当前 `vision_scope_unconfirmed` 表示视觉线索尚未确认；不能把模型自报 confidence 当作准确率，也不能把视觉候选当作知识证据。

## 当前能力

`frontend/src/views/tourist/ChatView.vue` 的视觉面板展示 `scene_summary`、字符串数组 `candidate_attractions`、`visual_tags` 和 `confidence`，按钮直接用 `retrieval_query` 与 `visionContext` 发起讲解。`handleVisionFileChange`、`handleAnalyzeImage`、`clearVisionState` 已使用 `visionRequests.cancel()/begin()/isCurrent()`、AbortSignal、幂等键及预览 URL 清理，适合复用；当前候选只是标签，不是可选择的已发布实体。

`frontend/src/api/itinerary.js` 的 `fetchItineraryCatalog()` 获取 `/itinerary/catalog`；其 `items` 包含 `site_id`、`spot_code`、`entry_id`、`published_revision_id`、`title`、`aliases` 和 `source_label`，响应含 `digest`。`RouteView.vue` 已用该目录选择景点，可复用 API 和已发布列表，但不能仅按相似名称静默把视觉候选变成唯一实体：别名可能重复、没有匹配或被下架。

当前 `ChatRequest.selection` 的 `attraction_id` 是正整数快捷选择 ID，目录 `entry_id` 是另一种标识；不能直接把 entry_id 塞进 attraction_id。`VisionContext` 目前没有确认身份字段。后端当前 `pipeline.py` 对视觉上下文清除受影响 scope 并发 warning，所以纯前端增加选中按钮尚不能安全实现已确认范围；需要单独后端协议支持并重新查询当前 site 的已发布 entry/revision，不能信任客户端 title、revision、confidence。

## 建议的最小交互

1. 显示模型候选为“识别线索”，旁边展示从已发布目录加载的可搜索列表；允许游客明确选一个目录项目，也提供“不确定/没有匹配”与继续开放检索选项。无候选时也允许手动搜索；目录不可用时说明无法确认，保留开放问答或取消，不生成虚假来源。
2. 用户点选并再次提交时，发送明确确认的 entry ID 与观察到的 revision/digest（新协议须由主 Agent 定义）；后端按 site 重新核验仍已发布且版本匹配，变更时提示重新选择。把用户确认记为用户输入，不等于证据能证明照片就是该景点。已选全局景点与照片选择冲突时展示两个名称让游客决定，不静默覆盖。
3. 每张图的确认状态绑定视觉请求 generation；换图、清除、关闭面板或新一轮分析立即重置确认并取消挂起目录/识别请求。目录或模型迟到响应必须同时匹配图片 generation；用户选择后若提交时仍在流式或图已变则拒绝旧选择。取消确认只清空该次确认，不修改已保存行程或其他游览状态。
4. 候选标签与目录条目可辅助匹配但必须显示“可能匹配”，多项同名均列出且标明来源；无结果时允许不确认继续，提示讲解未针对照片完成核验。来源面板只显示本消息真正检索到的已发布资料。

## 验证建议

使用无真实供应商的 store/component 测试覆盖：双候选、别名歧义、目录为空/失败、显式取消、换图后迟到分析和迟到目录、确认后重分析、目录版本改变与跨 site、原先选中景点与图片冲突。后端接口测试覆盖篡改 ID、下架、revision 不匹配、消息 warning 与真实检索 scope 绑定；确认前继续不限制错误 scope。再用真实浏览器和真实图片/授权知识验收并人工核查事实，不将 mock 的通过作为视觉准确率。
