# 源码只读审计：AI、RAG、视觉、语音、数字人与数据

日期：2026-10-30。审计对象：`code/RuanJianBei`、`v01-worktree`、`code/w02-integration`。仅静态读取源码、JSON及文档；没有启动应用、读取真实.env、调用供应商、迁移数据库或改动代码。以下历史报告仅作为已有证据，不能代替当前版本复测。本文不是官方评分表的逐项赋分。

## 总体判断

项目有实际的多模态服务适配、检索生成与3D数字人实现，不是只有界面的原型。主要缺口是可复现的端到端成功证据、真实设备验收、数据口径与技术主张边界。优先把已有功能跑成可靠演示闭环，再扩展能力。

三个目录的 `backend/app/services/llm/openai_compatible.py`、`backend/app/services/vision/qwen.py`、`frontend/src/components/ThreeAvatar.vue` SHA256分别一致；因此三份不是三套独立AI实现。V01及W02的 `backend/app/api/chat.py` 一致，和主目录不同。W02新增持久工具执行能力不能直接推定已经合回主目录。

## 能力与评分证据

| 维度 | 源码证据（以code/RuanJianBei为基准） | 可支持的表述 | 证据/评分缺口 |
|---|---|---|---|
| 大模型问答 | `backend/app/services/llm/openai_compatible.py:56-91`，`backend/app/api/chat.py:169-244` | OpenAI兼容接口流式调用；模型失败时可回退证据回答 | `core/config.py:38` 默认llm_provider=stub；不能凭默认启动页宣称真实大模型已接通。应演示实际provider/模型与成功响应、错误降级 |
| RAG | `backend/app/api/chat.py:169-214`；`services/rag/chroma_retriever.py`、`cross_encoder_reranker.py`、`resilient_reranker.py` | Chroma向量检索、BGE embedding、cross-encoder重排，失败回退repository/BM25 | 30条检索报告不是总体问答正确率；需独立测试集、错例与无证据拒答，验证索引和答案缓存更新 |
| 视觉识景 | `backend/app/services/vision/qwen.py:38-61,83-85,115,152-169`；前端`ChatView.vue:191-224` | 上传/摄像头→视觉模型提取线索→检索问答 | confidence来自模型返回字段，非校准准确率；失败回退confidence=0并可能使用文件名线索。单图成功不支持识景准确率95% |
| ASR | `backend/app/services/asr/local_sensevoice.py:34-69,118-120`；`api/voice.py` | 真实sherpa_onnx SenseVoice解码路径及云服务适配 | 默认asr_provider=stub；本地模型默认Windows绝对路径（config.py:82），跨系统部署需配置。缺中文噪声/方言/远场录音WER及延迟证据 |
| TTS | `backend/app/services/tts/factory.py:35-132`；`frontend/src/composables/useAudioPlayer.js:164-240` | 百炼/火山语音合成与流式输出；浏览器speechSynthesis降级 | 浏览器朗读不能算云TTS成功；需真实音频、首音延迟、打断与口型同步录屏 |
| 数字人 | `frontend/src/components/ThreeAvatar.vue:21-22,255-298`；`backend/app/services/avatar/viseme.py:1-5` | Three.js/VRM加载、动作与表情、文字拼音驱动口型 | 后端`avatar/stub.py`只回传neutral和文字；viseme明确不做真实音频分析。宜称“3D数字人交互、拼音口型”，不能声称自研音频驱动唇形模型或高精度音素对齐 |
| 前端闭环 | `ChatView.vue`、`stores/chat.js`、`useSSEStream.js`、`useRecorder.js`、`useCamera.js`、`useAudioPlayer.js` | 统一舞台含文字、录音、识景、引用、地图与路线 | 源码存在不等于手机端验收；浏览器权限、HTTPS、WebGL加载、停止后旧音频回流需实机验证 |
| 可编辑行程/持久执行 | `v01-worktree/backend/app/services/itinerary/`；`code/w02-integration/backend/app/services/tool_execution/`及`repositories/tool_execution.py` | V01可编辑行程；W02执行任务有持久化、查询、取消与重试结构 | W02地图记录36条目标测试和本地页面验证，但注明全量后端、PostgreSQL多worker、真实模型及手机未验收；本次未重跑，不能宣称全链路通过 |

## 已有评测的准确解读

以下文件在三目录均存在，读取结果一致：

- `eval/reports/retrieval_v0.json`：30条，Recall@1=0.9667、Recall@5=1.0、MRR=0.9833，passed=true。可支持小样本检索结果。
- `eval/reports/reranker_v0.json`：重排后Recall@1=1.0、MRR=1.0，但passed=false。不可只展示100%而略去报告总门禁未通过。
- `eval/reports/reranker_gate_v1.json`：candidate_k=5/max_length=128配置重排P95约833ms；报告明确30条不足以设置全局score或margin门限。
- `eval/reports/e2e_eval_b2_sampled_real.json:43-49`：case_count=100，accuracy/evidence_rate/refusal_pass_rate均为0。结果含大量HTTP 502，first_text计数0。这反映该次服务/环境链路失败，不证明模型知识能力为零，也绝不能作为100题验收成功的证据。
- `eval/reports/qwen_vision_smoke.json`：单图ok=true，约20.69秒，confidence=0.95。只能支持该图片当时调用成功，不支持95%识别准确率或实时识景。
- `deepseek_smoke_v1.json`与`chat_stream_smoke_b1.json`有ok=true，属于单次历史冒烟，不能覆盖当前配置及全部场景。

## 数据真实性与发布一致性

`data/processed/`实读计数：38条knowledge、88条FAQ、22节guide、7条route。knowledge和FAQ保存文档出处，可以支持来源可追溯；这些来源字段本身不证明来自景区官方或已获使用授权，仍需提交材料明确来源和采集/整理方法。

`visitor_behavior_summary.json`明确：140447行、152景点、2025全年，`contains_lingshan_records=false`，`intended_usage`为后台行为分析示例、不作为灵山问答事实源。因此不可包装成“灵山真实游客14万+运营数据”，也不可用来证明灵山个性化推荐的实证效果。可以展示为给定行为数据的分析能力，标清景区不匹配。

`docs/REPO_MAP.md`已明确后台知识CRUD、processed数据导入、分块、向量索引、FAQ运行时、QA缓存是不同层。答案缓存默认七天，编辑知识不应直接宣传为立即影响回答；需验收“编辑→发布/索引→原问题得到新答案”并避免同步导入覆盖后台编辑。

## 建议优先补齐的材料

1. 用最终交付目录与干净配置完成文字问答、无证据拒答、识景问答、语音输入输出、数字人、路线的一次连续录屏；记录供应商、模型、耗时及降级状态。
2. 修复/复核历史100题502环境，重跑离线或授权真实链路；分别报告检索、事实正确率、证据一致性、拒答及P50/P95，不把dry-run算模型评测。
3. 标清示例行为数据与景区知识数据；统一“拼音口型/VRM交互”的表述，移除没有测量依据的准确率与实时性承诺。
4. 固定最终源码目录、迁移与安装步骤；W02单列已验证及未验证范围。补手机摄像头/麦克风、低性能降级和中断回流验收。

审计限制：没有执行运行测试、浏览器测试或付费模型调用，未检查实际部署凭据与生产状态；上述缺口是证据不足或已记录失败，非断言所有对应功能不可用。
