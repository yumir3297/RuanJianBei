# 第三阶段开发准备与决策记录

日期：2026-10-29。性质：需求决策及初步技术评估，不是已批准的功能设计或实施计划。

## 用户确定的边界

- 采用本地新版第三阶段：V02 识景关联游览、V03 播放补齐、K02 扩展解析/OCR、O01 运营讲解生产、W03 成果库与总结导出。
- 文件格式：用户已确认，在难度可控且有成熟开源组件的前提下，首批尽量纳入 Word、Excel、PPT、TXT、Markdown，以及已有 PDF/JSON。优先支持 DOCX/XLSX/PPTX；旧版二进制格式和复杂内容单独评估，不将目标范围等同于已验证支持。
- OCR 工具位置由用户稍后提供；引擎、运行方式尚未确定。
- 上传进入草稿，人工纠错后发布；已有部分实现，应先核对再复用。
- 总结同时支持实际游览内容和用户选择的讲解/聊天内容，用户选择后形成可编辑草稿。已游览事实与仅讨论内容要区分；成果持久保存按新版 W03 目标设计。
- 美图范围为基础编辑及景区相框、贴纸、文案，按新版 E01 后续推进。
- 离线范围为主动下载的基础资料和文字讲解，显示版本及清理入口，按 E04 后续推进。真正离线访问还需要最小阅读页及其资源可用。
- 照片是否默认本地处理、上传规则等未被单独明确答复，仍为设计建议。
- 产品须服务游客与运营 AI 工作台，任务可持续、成果可编辑、来源可追溯、失败可恢复。
- 技术方案参考公开开源代码并融合业务场景；可形成技术场景创新，但不将开源组件或未经验证效果描述为原创算法。

## 已核对的实现

- GitHub master 与 codex/repository-map 上的路线图仍为旧版；本地新版清单尚未出现在上述两分支。
- 主检出 code/RuanJianBei 有大量在途修改；不应将其单独作为全部能力基线。
- v01-worktree/backend/app/services/knowledge/parsers.py 已有 BaseDocumentParser、PDFTextParser、JSONKnowledgeParser；当前按 PDF/JSON 后缀分派，PDF 使用 pypdf。
- 同工作树已有 imports、import_diff、file_storage、workspace、publication、jobs 服务及导入/发布 API，包含重试与冲突处理。仅静态读取，未在本轮验证完整运行行为。
- PDFTextParser 当前逐页提取文字并跳过空文本页；纯扫描文档返回 needs_ocr，混合文档的扫描页可能被跳过。扩展设计须按页判断和记录漏页/待 OCR 状态。

## 格式难度初评

| 格式 | 初评 | 注意事项 |
|---|---|---|
| TXT、Markdown | 低 | 编码、标题/段落定位、大小限制 |
| DOCX | 中低 | 标题/段落/表格定位；不能凭空承诺 Word 页码 |
| XLSX | 中 | 工作表与单元格范围；公式缓存值及表头上下文，不执行公式 |
| PPTX | 中 | 幻灯片与形状定位，文本阅读顺序；不承诺图表和 SmartArt 全量语义还原 |
| 文本 PDF | 已有基础，中 | 多栏、表格、阅读顺序及逐页质量检测 |
| 扫描 PDF、JPG/PNG | 中高，待 OCR 核对 | 中文准确率、版面、旋转、资源成本与取消/重试 |
| DOC/XLS/PPT | 中高 | 额外转换链和运行时依赖，建议首版改传现代格式 |

难度为工程判断，并非安装、性能或样本验证结论。

## 开源方向及建议

1. 推荐：复用已有解析接口与持久任务，简单格式走轻量解析，复杂 PDF/表格评估 Docling，OCR 通过适配器接入用户现有工具。所有结果统一为带原文定位的结构化片段后进入 K01 草稿。
2. 备选：MarkItDown 快速统一转 Markdown，接入简单；需要额外补齐业务要求的稳定片段身份、细粒度来源与修订映射。
3. 不建议首版所有格式强制经过重型解析/OCR；会扩大部署和资源成本，收益需样本证明。

Docling 官方列出 PDF、DOCX、XLSX、PPTX、Markdown、图像等输入；旧 Office 格式需额外 LibreOffice。具体锁定版本、依赖冲突、模型许可、内存和部署条件仍需验证。

W03 可评估 html-to-image 导出受控卡片，手机保存、字体和跨域素材仍需实测；E01 可参考 Cropper.js 并结合 Canvas；E04 可参考 Vite PWA/Workbox 的缓存机制，内容版本及权限由业务维护。

## 场景创新的候选表述

“来源与版本驱动的双端 AI 内容生产闭环”：异构资料解析 → 带定位的证据片段 → 人工修订发布 → 多风格讲解及游客引用 → 根据真实游览和选定内容生成可编辑成果 → 对固定版本导出或离线下载。

可验证价值：引用定位准确率、漏页率、更新后旧内容失效率、任务恢复成功率、总结事实正确率、手机导出成功率。尚未测量，不宣称性能领先或首创。

## 公开参考

- https://github.com/docling-project/docling
- https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md
- https://github.com/microsoft/markitdown
- https://github.com/bubkoo/html-to-image
- https://github.com/fengyuanchen/cropperjs
- https://vite-pwa-org.netlify.app/guide/

后续采用具体代码时记录项目、版本/提交、参考文件、许可和本项目适配改动。
