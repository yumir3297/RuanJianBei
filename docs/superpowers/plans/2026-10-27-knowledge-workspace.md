# Knowledge Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本计划默认在当前会话直接实施；未经用户选择不派生子代理。

**Goal:** 实现永久草稿工作区，统一批量上传、文档重新导入、单条编辑、原子批量发布与立即下架。

**Architecture:** 文档版本和不可变知识修订存入关系数据库，发布任务先准备版本化切块和向量，再在一个数据库事务中切换选中条目的发布指针。所有读取通过发布可见性检查，缓存通过数据库知识代次隔离，任务持久化恢复。

**Tech Stack:** 现有 FastAPI、SQLAlchemy、Alembic、ChromaDB、Vue 3、Element Plus；pytest。PDF 文本解析依赖在实施时核对兼容性后锁定，OCR 通过独立适配器接入。

**Spec:** [已确认设计](../specs/2026-10-27-knowledge-workspace-design.md)

## Global Constraints

- 保存为草稿；每条知识可以独立编辑、发布。
- 草稿永久持久保存，刷新、退出、重启后可恢复，不自动过期；管理员可主动丢弃。
- 勾选多条可批量发布；全部准备成功后统一生效。
- 删除已发布知识立即下架；检索与相关缓存不能继续使用；旧任务或再次导入不能自动恢复。
- 不修改本地镜像 `sources/`。当前目录不是代码 checkout，本计划仅保存文档；执行时建立实际仓库工作区并重新核对 HEAD、AGENTS.md 和接口。
- 兼容 SQLite 与 PostgreSQL；用户未授权部署。本计划未执行，所有验证均为待执行。

## Review Focus

- 删除与发布并发：下架后旧发布、旧导入任务不能将条目重新激活（任务 2、4）。
- 版本向量混杂：未发布和过期候选不能挤掉有效结果导致假性空结果（任务 3）。
- 发布中继续编辑／多窗口编辑：不丢后续草稿，不静默覆盖他人修改（任务 2、4、7）。
- 文件插页、重名、解析遗漏：不误认版本、不批量重复或误删除（任务 5、6）。
- 多进程和任务崩溃：旧内存缓存、重试、迁移后旧索引不能泄露失效内容（任务 1、3、4、8）。

## 已核对的现状与文件职责

基线：`540568e231bbda10bfdfdeceaea4041aa681b078`。

| 现有文件 | 本次涉及职责 |
| --- | --- |
| `backend/app/models/knowledge.py`、`knowledge_chunk.py` | 当前知识没有草稿／发布版本；切块需关联不可变修订 |
| `backend/app/api/knowledge.py`、`repositories/knowledge.py` | 当前 CRUD 直接提交；切换为工作区写入与已发布读取 |
| `backend/app/services/data_import/importer.py` | 按标题＋来源覆盖，导入后 replace_all 切块；改为草稿导入 |
| `backend/app/services/data_import/chunker.py` | 现有 chunk ID 仅包含条目 ID、序号；加入修订 ID |
| `backend/app/services/rag/index_builder.py`、`vector_store.py` | 当前全量替换先删集合；增加版本化增量准备与安全重建 |
| `backend/app/services/rag/chroma_retriever.py`、`retriever.py`、`base.py` | 向量及回退读取统一校验修订可见性、保留来源 ID |
| `backend/app/services/qa/cache.py`、`pipeline.py` | 缓存有进程内与数据库两层；读写绑定知识代次 |
| `backend/app/api/admin.py`、`guide.py` | 同步／重建入口及讲解缓存接入一致性规则 |
| `backend/app/db/bootstrap.py`、`backend/main.py` | 初始化和任务恢复不得绕过发布规则 |
| `frontend/src/views/admin/KnowledgeManage.vue`、`frontend/src/api/knowledge.js` | 已有列表、编辑、同步、重建入口；扩展工作区和发布 |
| `backend/app/tests/` | 复用 pytest、TestClient 和 async_db 测试方式 |

新增模块统一放在 `backend/app/services/knowledge/`，分为工作区、发布、可见性、导入与任务调度职责；模型、schemas、repository 保持项目现有分层。前端工作区子组件放在 `frontend/src/components/knowledge/`。

## Task 1：持久模型与既有数据迁移

**Files:** 新增 `backend/app/models/knowledge_workspace.py`、`backend/app/schemas/knowledge_workspace.py`、`backend/app/repositories/knowledge_workspace.py`、`backend/alembic/versions/<new_revision>_knowledge_workspace.py`；修改上述知识模型、models/__init__.py；测试 `backend/app/tests/test_knowledge_workspace_migration.py`。

**Interfaces:** `KnowledgeEntry` 保留稳定整数 ID，新增 `published_revision_id`、`draft_revision_id`、`lock_version`、`withdrawn_at`；`KnowledgeRevision` 使用 UUID 字符串，内容不可变并含来源版本／页段、base_revision_id。新增 `SourceDocument`、`SourceDocumentVersion`、`ImportJob`、`ImportConflict`、`PublicationJob`、`PublicationItem`、单行 `KnowledgeState(epoch:int)`。任务保存错误、幂等键、租约和阶段。

- [x] 写失败测试：迁移前后知识 ID 和已发布正文不变；新草稿无 published 指针；关闭并重建 session 后草稿仍在；旧切块映射到迁移修订。
- [x] 从 backend 运行 `python -m pytest app/tests/test_knowledge_workspace_migration.py -q`，确认新增行为失败。
- [x] 实现表结构、索引、外键和回填。现存条目作为已发布基线；迁移清除旧答案缓存，旧向量通过后续版本校验不可直接绕过；迁移后安全重建流程由 Task 8 完成。原件持久目录纳入备份，不存临时目录。
- [x] 在 SQLite 和临时隔离 PostgreSQL 执行 Alembic upgrade 并运行上述测试通过；提交该任务。

## Task 2：单条工作区与立即下架

**Files:** 新增 `services/knowledge/workspace.py`；修改知识 API、schemas、repository；新增 `app/tests/test_knowledge_workspace.py`，更新 `test_knowledge_api.py`。

**Interfaces:** `save_draft(entry_id:int|None,payload:KnowledgeCreate|KnowledgeUpdate,expected_version:int|None)->WorkspaceEntry`；`discard_draft(entry_id:int,expected_version:int)->None`；`withdraw(entry_id:int,expected_version:int)->None`。均为 async。POST/PUT `/api/knowledge/` 保存草稿；GET 返回管理员工作区数据；DELETE 下架；新增 DELETE `/{id}/draft` 主动丢弃。修改冲突返回 409。

- [x] 写失败测试：保存新草稿游客搜索为空；修改已发布条目游客仍见旧文；重新登录草稿仍在；重复版本编辑 409；丢弃不影响已发布；下架与旧任务竞争不能复活。
- [x] 运行 `python -m pytest app/tests/test_knowledge_workspace.py app/tests/test_knowledge_api.py -q`，先确认失败。
- [x] 实现不可变修订、乐观锁与事务。删除提交同时清空发布指针、递增 epoch、记录防恢复状态；游客 list/search/get/get_attraction 等入口仅返回有效已发布内容。新草稿 entry 的占位正文绝不作为游客数据。
- [x] 运行该组测试并确认通过，提交。

## Task 3：版本化检索与缓存可见性

**Files:** 新增 `services/knowledge/visibility.py`；修改 RAG base、retriever、chroma_retriever、vector_store、index_builder、chunker；修改 QA cache、pipeline、repositories/qa_cache.py 及讲解缓存路径；测试 `app/tests/test_knowledge_visibility.py`。

**Interfaces:** `VisibilityService.read_epoch()->int`、`filter_published(references:list[tuple[int,str]])->set[tuple[int,str]]` 均 async；vector store 增加同步 `upsert(records:Sequence[VectorStoreRecord])->int`、`delete_ids(ids:Sequence[str])->None`。chunk ID 固定为 `ke_{entry_id}_{revision_id}_{index:03d}`。RetrievedDocument 保留 entry_id/revision_id；缓存键包含 epoch，set 写入请求开始时捕获的 epoch。

- [ ] 写失败测试：未发布和旧修订向量被过滤；向量里全是旧版时仍可通过补取／数据库回退找到有效知识；下架后旧内存和数据库缓存不命中；旧请求不能在新 epoch 写回旧结果；回退、讲解和 FAQ 衍生答案均按相同规则失效。
- [ ] 运行 `python -m pytest app/tests/test_knowledge_visibility.py app/tests/test_chroma_retriever.py app/tests/test_rag_retriever.py -q`，确认失败。
- [ ] 实现关系库可见性校验，向量结果经校验后才能进入 LLM。限定候选补取次数后使用已发布数据库回退，避免旧向量挤占 top-k。各进程请求都查持久 epoch；缓存失效不依赖进程广播。向量记录缺修订信息时禁用并走回退。输出前重查 epoch；流式期间检查下架，停止相关后续输出，不承诺撤回已发送片段。
- [ ] 测试通过后提交；补跑现有 pipeline 与 guide 测试，记录兼容性变化。

## Task 4：可恢复的单条／批量发布

**Files:** 新增 `services/knowledge/publication.py`、`jobs.py`、`api/knowledge_publications.py`；修改 API router 和应用生命周期；测试 `app/tests/test_knowledge_publication.py`。

**Interfaces:** async `create_publication(items:list[PublicationSelection],idempotency_key:str)->PublicationJob`，selection 包含 entry_id、revision_id、expected_version；async `run_publication(job_id:str)->None`；POST `/api/knowledge-publications/` 返回 202 和 job_id，GET `/{job_id}` 查状态，POST `/{job_id}/retry` 重试。状态 queued/preparing/committing/succeeded/failed。

- [ ] 写失败测试：批量第二条 embedding 失败时两条均不切换；准备完成进程崩溃后恢复；同幂等键只创建一个任务；发布中继续编辑保留新草稿；两个发布竞争返回冲突；下架后旧任务切换失败。
- [ ] 运行 `python -m pytest app/tests/test_knowledge_publication.py -q`，确认失败。
- [ ] 点击发布即固定修订；工作进程用数据库租约取任务，准备所有切块和版本向量，校验数量后通过一个短事务校验版本／下架状态、切换所有指针、递增 epoch 并记成功。已发送外部向量的孤儿记录不可见，可重试清理。事务内不调用外部模型。不把内存 BackgroundTasks 作为唯一恢复来源。
- [ ] 测试通过并用两个独立 session 验证竞争；提交。

## Task 5：批量上传、解析与来源持久化

**Files:** 新增 `api/knowledge_imports.py`、`services/knowledge/imports.py`、`parsers.py`、`file_storage.py`；修改 router、config 和 requirements；测试 `app/tests/test_knowledge_imports.py`。

**Interfaces:** async `create_import(files:list[UploadFile],document_ids:list[str|None],idempotency_key:str)->ImportBatch`；async `run_import(job_id:str)->None`；解析协议 `parse(path:Path)->list[ParsedSection]`，section 含 title/content/page_start/page_end/section_path。POST `/api/knowledge-imports/`、GET `/{batch_id}`，均需管理员鉴权。

- [ ] 写失败测试：多个 PDF 独立成功／失败；同文档相同 hash 不重复生成；同名不同内容不自动归并；损坏／加密／空文本／超限文件有明确状态；服务重启原件与任务仍在；恶意文件名不能越界写入。
- [ ] 运行 `python -m pytest app/tests/test_knowledge_imports.py -q`，确认失败。
- [ ] 以服务端生成 ID 存原件，保存 hash，文件名仅展示；校验实际类型与可配置数量／字节／页数／时间边界。首批实现 JSON 与文本 PDF 解析，锁定验证过的依赖；扫描件保留并标 needs_ocr，不当作成功的空知识；OCR 适配器未接入时前端说明。解析任务独立事务，失败保留已成功结果，重试不重复。
- [ ] 测试通过并用真实中文文本 PDF 校验页码和提取结果；提交。扫描 OCR 尚未接入时明确记录能力边界。

## Task 6：重新导入差异、冲突与旧同步兼容

**Files:** 新增 `services/knowledge/import_diff.py`；修改 imports、importer.py、api/admin.py、bootstrap.py；测试 `app/tests/test_knowledge_reimport.py`、更新 test_data_import.py。

**Interfaces:** `compare_sections(previous:list[ParsedSection],incoming:list[ParsedSection])->list[ImportChange]`；async `resolve_conflict(conflict_id:str,choice:str,merged_payload:KnowledgeCreate|None,expected_version:int)->WorkspaceEntry`。change 类型 unchanged/added/modified/possibly_removed/conflict；choice 为 keep_current/use_incoming/merge；POST `/api/knowledge-imports/conflicts/{id}/resolve`。

- [ ] 写失败测试：插页不复制知识；重命名和分拆合并不确定时需要确认；旧 PDF、人改、旧草稿、新 PDF 之间不丢任一候选；解析遗漏不下架；被删知识不复活；旧同步和启动流程不绕过工作区；未解决冲突不能发布。
- [ ] 运行 `python -m pytest app/tests/test_knowledge_reimport.py app/tests/test_data_import.py -q`，确认失败。
- [ ] 优先使用文档稳定 ID、已确认映射及章节结构匹配；内容 hash 判不变，标题／页码不能作为唯一身份。以先前导入原文为基线，比较人工修改与新原文；任何已有未发布修改都保留，冲突单独持久化。旧同步改为导入草稿，FAQ／路线原有导入行为单独保留并测试，不暗中删除。
- [ ] 测试通过后提交。

## Task 7：管理端工作区与发布界面

**Files:** 修改 KnowledgeManage.vue、api/knowledge.js；新增 api/knowledgeImports.js、api/knowledgePublications.js，components/knowledge/ 下 WorkspaceEditor.vue、ImportBatchPanel.vue、ImportConflictPanel.vue、PublicationStatus.vue。

**Interfaces:** JS API 对应任务 2／4／5／6；保存提交 expected_version；发布选中 revision_id 快照；响应明确 saved_at、状态、错误和后续草稿，不使用 localStorage 作为唯一存储。

- [ ] 先编写可重复的界面验收脚本：上传两文件→修正一条→保存→退出再进→选中发布；发布失败重试；发布期间继续改；重新导入解决冲突；下架；丢弃草稿。
- [ ] 实现已发布／草稿／任务分开呈现、来源页码与差异、逐条保存、选中发布。明确显示“保存草稿”和“发布”；离开有未保存内容时提示，后端确认保存后才显示成功。409 保留本地编辑供对比。旧“立即同步”改为“导入至草稿”，重建不隐含发布。
- [ ] 执行 `npm --prefix frontend run build`，必须退出 0；浏览器按上述脚本验证电脑与手机宽度，刷新和断网重试后不得丢已保存草稿。
- [ ] 记录实际结果、未覆盖设备和截图，提交。

## Task 8：安全重建、迁移演练与端到端验收

**Files:** 修改 index_builder.py、api/admin.py；新增 `app/tests/test_knowledge_workspace_e2e.py`、`docs/knowledge-workspace-operations.md`；更新路线图当前工作包状态（仅标真实完成项）。

**Interfaces:** async `rebuild_published_index()->RAGIndexBuildReport` 仅构建有效已发布修订，新集合准备好后切换持久集合引用；读服务每次按当前引用读取，旧集合延迟清理。此操作不发布草稿。

- [ ] 写失败测试：全量重建失败保留旧集合；重建并发下架不复活；准备索引后数据库事务失败不泄露新版；清理失败只影响空间；迁移期间数据库回退可回答；第二进程不读旧缓存。
- [ ] 运行 `python -m pytest app/tests/test_knowledge_workspace_e2e.py app/tests/test_rag_index_builder.py -q`，确认失败。
- [ ] 实现发布有效性校验、安全重建和恢复步骤。运维文档包含数据库＋原件备份恢复演练、任务故障恢复、磁盘不足告警与拒绝新上传；禁止按时间自动清草稿。旧版本索引回收不得删除工作区依赖的原件／修订。
- [ ] 从 backend 运行 `python -m pytest app/tests -q`，frontend 执行 `npm run build`；在隔离数据库完成 upgrade 与备份恢复演练。任何不可用依赖或外部服务缺失必须记录，不能把跳过当通过。
- [ ] 按设计七项验收逐项记录证据；确认无遗漏再提交和准备可审阅变更，不自动部署。

## 自查记录

设计目标映射：持久草稿→1/2；单条编辑／删除→2/3；原子批量发布与失败恢复→3/4；多文件与来源→5；重新导入、人工冲突、防恢复→6；上传到发布前编辑→7；旧入口、重建、迁移、备份→6/8。Review Focus 均分配测试。上述任务和文件名是实施约定，执行前须核对仓库 HEAD；本计划没有声称代码或测试已经完成。
