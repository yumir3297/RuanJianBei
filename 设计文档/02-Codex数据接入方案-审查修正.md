# Codex 数据接入方案 — 审查修正确认

> 本文档是对 Codex `CURRENT_TASK_SUMMARY.md` 的审查结果。**Codex 原方案方向正确，但以下 5 点必须在执行前修正。** 修正后可直接开写。

---

## 一、准入条件（修正后方案）

- [x] 方案方向、边界、约束全部正确
- [x] 5 处修正已明确，无遗留歧义
- [x] 修正不引入新依赖、不扩大本轮范围
- [x] **批准执行**

---

## 二、修正清单

### 修正 1：Knowledge 模型补 `metadata_json` 列

**问题**：`knowledge_entries.json` 每条都有 `metadata` 对象（景点ID、位置、参数、文化内涵、开放信息等），当前模型只有 `title/category/content/source/aliases` 5 个字段，导入时会丢弃结构化元数据。

**修正**：在 `models/knowledge.py` 的 `KnowledgeEntry` 里加一列：

```python
metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
```

迁移方式：`create_all` 自动处理，无需 Alembic。

**同时更新**：`schemas/knowledge.py`（读写 DTO 加 `metadata_json`）、`repositories/knowledge.py`（create 时填入）、`api/knowledge.py`（返回时包含）。

> 如果不加这列，未来 RAG 按景点分组检索、按文化权重排序这些能力全部无法实现。现在加一列的代价极小。

---

### 修正 2：FAQ 加载链路改为 DB→内存

**问题**：当前 `chat.py:34` 从 JSON 文件直接加载 FAQ，修正后应切为 DB。但不能每次匹配都查 SQLite——会破坏 L1 精确匹配 < 5ms 的延迟约束。

**修正**：FAQ 命中层启动时从 DB 一次性全量加载到内存，匹配逻辑不变（hash 索引）。

```python
# FAQMatcher 改造成支持两种加载源
class FAQMatcher:
    def load_from_file(self, path: Path) -> None: ...   # 保留，开发调试用
    def load_from_db(self, session: Session) -> None: ...  # 新增，生产用
    def reload(self, session: Session) -> None:    # 知识库更新后清除+重载
        self.entries.clear()
        self.exact_index.clear()
        self.load_from_db(session)
```

**同时修改 `chat.py`**：`build_pipeline()` 中把 `faq_matcher.load_from_file(...)`改为 `faq_matcher.load_from_db(session)`。

**验证要求**：启动后加载时间 < 1s，精确匹配延迟 < 5ms。

---

### 修正 3：推荐引擎从 stub 改为 DB 驱动

**问题**：`services/recommend/engine.py` 返回纯占位路线，连灵山的边都没沾。

**修正**：导入 `route_recommendations.json` → 入库 → 推荐引擎做简单规则匹配：

```
user.interests 含"历史"  → route_001（历史文化爱好者路线）
user.interests 含"自然"  → route_002（自然风光爱好者路线）
user.interests 含"亲子"/"孩子"/"家庭" → route_003（亲子家庭路线）
默认 → route_001
```

`audience_type` 作为辅助信号（如 `family` 类型也偏向亲子路线）。

**需要新增模型**：

```python
# models/route.py
class RouteTemplate(Base):
    __tablename__ = "route_templates"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str]
    duration_label: Mapped[str]
    route_plan: Mapped[str] = mapped_column(Text)
    guide_points_json: Mapped[str] = mapped_column(Text)   # JSON array
    experiences_json: Mapped[str] = mapped_column(Text)     # JSON array
    source: Mapped[str]
    tags: Mapped[str]   # "|" 分隔，"历史|文化|朝圣"
```

**同时更新**：`services/recommend/engine.py` 改为接收 `session`，从 DB 查路线做规则匹配。

---

### 修正 4：确认 `guide_sections.json` 用途并入库

**结论**：`guide_sections.json` 是"景区概况、历史渊源、文化内涵"等篇章级内容，与 `knowledge_entries.json`（景点结构化数据）互补。**建议也导入**，作为知识库的"综述/背景"类条目。导入规则：

```python
{
    "title": "景区概况与千年历史渊源",
    "category": "景区概况",
    "content": "...",
    "source": "灵山胜境：历史、文化、景点特色与个性化游览指南.docx",
    "aliases": ["灵山胜境历史", "灵山胜境介绍"],
    "metadata_json": {"scenic_area": "灵山胜境", "section_type": "overview"}
}
```

导入时打标 `metadata.section_type = "overview"`，RAG 检索时可区别对待（概述类权重略低于精确景点数据）。

---

### 修正 5：验证补一条 FAQ 延迟测试

**在 Codex 原 6 条功能验证后追一条**：

7. 触发 FAQ 全量加载，确认加载时间 < 1s。
8. 对已导入 FAQ 条目做精确匹配调用，确认延迟 < 5ms。

用简单 Python 计时即可：

```python
# tests/test_faq_perf.py
import time
start = time.perf_counter()
result = faq_matcher.match("灵山大佛多高")
elapsed_ms = (time.perf_counter() - start) * 1000
assert result.is_hit and elapsed_ms < 5
```

---

## 三、`visitor_behavior_summary.json` 处理策略（无需修正，仅确认）

Codex 原方案中对此文件的处理是正确的：

- ✅ 不接入问答事实源（数据包里明确标注非灵山景区数据）
- ✅ 只作为后台分析页面的示例统计源
- ✅ 导入到独立的 visitor_behavior 表，不与 knowledge 混

**本轮不做**真实分析逻辑，只导入汇总摘要供 `api/admin.py` 的概览接口展示。

---

## 四、数据流转最终确认图

```
data/processed/
├── knowledge_entries.json  ──→  KnowledgeEntry 表  ──→  知识库API / RAG检索源
├── guide_sections.json     ──→  KnowledgeEntry 表  ──→  同上（category="景区概况"）
├── faq_entries.json        ──→  FAQ 专用表         ──→  FAQMatcher 内存索引
├── route_recommendations   ──→  RouteTemplate 表    ──→  推荐引擎
└── visitor_behavior_summary ──→  BehaviorSummary 表  ──→  后台概览API
```

**约束**：JSON 文件仅作为导入源。导入完成后，所有运行时查询均读取 DB/内存索引，不再依赖文件 I/O。

---

## 五、本次实际改动范围

### 新增文件

| 文件 | 说明 |
|------|------|
| `models/behavior_summary.py` | 行为分析数据模型 |
| `models/route.py` | 路线模板模型 |
| `repositories/behavior_summary.py` | 行为数据仓储 |
| `repositories/route.py` | 路线仓储 |
| `repositories/faq.py` | FAQ 数据仓储 |
| `services/data_import/importer.py` | 数据同步服务（核心新增） |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `models/knowledge.py` | 补 `metadata_json` 列 |
| `schemas/knowledge.py` | DTO 补 `metadata_json` |
| `repositories/knowledge.py` | create 补 `metadata_json` |
| `api/knowledge.py` | 返回补 `metadata_json` |
| `api/chat.py` | FAQ 加载源改 `load_from_db` |
| `services/qa/faq_matcher.py` | 加 `load_from_db` 和 `reload` |
| `services/recommend/engine.py` | 从 stub 改为 DB 驱动规则匹配 |
| `api/admin.py` | 概览接口补路线/FAQ/行为统计 |
| `api/recommend.py` | 传 session 给 engine |
| `core/config.py` | 补数据目录配置项 |
| `db/bootstrap.py` | 补新模型 create_all |

---

## 六、本轮明确不做

与 Codex 原方案一致，以下**本轮不做**：

1. ❌ 不接入 ChromaDB 向量检索
2. ❌ 不做 embedding 和切块入库
3. ❌ 不接新外部模型
4. ❌ 不做管理端上传工作流
5. ❌ 不重写 QA pipeline 主线
6. ❌ 不对 visitor behavior 做深度分析
