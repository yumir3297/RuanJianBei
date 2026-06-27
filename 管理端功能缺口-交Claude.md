# 管理端功能缺口清单 · 交 Claude

> **状态**: 前端 11 项已修复，待处理以下后端问题
> **当前数据库** (`backend/app.db`) 快照时间: 2026-06-21

---

## 〇、当前数据库表行数

| 表名 | 行数 | 备注 |
|------|------|------|
| chat_logs | 349 | 有数据 |
| qa_cache_entries | 102 | 有数据 |
| faq_entries | 88 | 有数据 |
| knowledge_chunks | 66 | 有数据 |
| knowledge_entries | 38 | 有数据 |
| quick_topics | 8 | 有数据 |
| route_templates | 3 | 有数据 |
| avatar_configs | 3 | 有数据 |
| visitor_profiles | 2 | ⚠️ 接近空 |
| behavior_summaries | 1 | 同步过 |
| **knowledge_blind_spots** | **0** | ❌ 永远是空 |

---

## 一、功能缺口 #1：知识盲区表始终为空

### 表现
`knowledge_blind_spots` 表在 349 条聊天日志下为 **0 条**。前端的 BlindSpotManage 和 AnalyticsReport 盲区区域永远显示"暂无待处理盲区"。

### 根因
**不是代码没连上**。管线是通的：

```
chat.py:235 → BlindSpotTracker(KnowledgeBlindSpotRepository(session)) 传入 pipeline
pipeline.py:130-133 → 当 RAG 返回空 documents 时调用 blind_spot_tracker.record()
```

问题在于 pipeline 走到盲区记录的条件是 `RAG 检索返回空 documents`。但如果 FAQ 匹配、缓存命中、或 LLM 直接回答，都不会走到盲区记录。

实际可能有两种情况：
- 所有问题都被 FAQ / cache / LLM 直接回答了，没有真正 RAG 空结果
- 或者 blind_spot 的条件有 bug

### 需要验证
在 `backend/app/services/qa/pipeline.py` 第 130-135 行附近，确认盲区记录的触发条件是否正确：
```python
if not documents:
    if self.blind_spot_tracker is not None:
        try:
            self.blind_spot_tracker.record(
                raw_query=request.query,
                normalized_query=normalized_query,
            )
```

同时确认：如果 FAQ 命中但 RAG 检索没找到参考文献，这个算不算应该进盲区？

### 修复建议
在 blind_spot_tracker.record() 调用处加日志，或放宽盲区判定条件——不仅限于 "RAG documents 为空"，也可以包括 "RAG 检索到的内容相关度低于阈值" 的情况。

---

## 二、功能缺口 #2：用户画像表几乎一直为空

### 表现
`visitor_profiles` 当前只有 **2 条**，但 `chat_logs` 有 349 条。前端的"游客画像数"始终很低、"游客群体构成"饼图几乎无数据。

### 根因
写入路径存在但**聊天管线不调用它**：

```python
# recommend.py:21 — 唯一的写入点
VisitorRepository(session).upsert(payload.session_id, payload.interests, payload.audience_type)
```

这只在 `POST /api/recommend/` 端点被调用。而 `chat.py` 中**完全没有**调用 recommend 或 VisitorRepository。

聊天管线 (`pipeline.py`) 的 stream_chat 在结束时：
- ✅ 写了 `chat_logs`（ChatLogRepository.create）
- ❌ 没有写 `visitor_profiles`（从未调用 VisitorRepository）

### 修复建议
在 `pipeline.py` 的流式对话结束时（约第 250 行附近，ChatLogRepository.create 之后），加入：
```python
# 在 pipeline.py 中注入 VisitorRepository 并在对话结束时写入
visitor_repo.upsert(
    session_id=request.session_id,
    interests=extract_interests_from_query(request.query),
    audience_type="general",  # 或从请求中获取
)
```

或者更简单：把 visitor 数据收集移到 `chat.py` 的端点处理层，在每次聊天响应后自动写入。

---

## 三、功能缺口 #3：多条表仅靠 admin sync 灌数据

以下表**不在**聊天管线中实时写入，只能通过 `POST /api/admin/sync-processed-data` 批量导入：

| 表 | 当前行数 | 写入方式 | 聊天管线写入？ |
|---|---------|----------|:---:|
| route_templates | 3 | `POST /api/admin/sync-processed-data` | ❌ |
| behavior_summaries | 1 | `POST /api/admin/sync-processed-data` | ❌ |
| knowledge_chunks | 66 | `POST /api/admin/sync-processed-data` | ❌ |
| faq_entries (批量) | 88 | `POST /api/admin/sync-processed-data` | ❌（但盲区解决可以增补一条） |
| knowledge_entries (批量) | 38 | `POST /api/admin/sync-processed-data` 直接写 session | ❌（但 CRUD API 可以单条增改）|

### 影响
- 如果管理员从未点"同步官方资料"，route_templates 和 behavior_summaries 是空的
- **Recommend API** (`POST /api/recommend/`) 依赖 `RouteRepository.list_all()`，没同步就没路线推荐
- RAG 向量索引 (`POST /api/admin/build-rag-index`) 依赖 `knowledge_chunks`，没同步就建不了向量索引

### 当前数据库状态
这些表已经有数据（之前同步过），所以不是紧急问题。但 `data/processed/` 目录并不存在（配置里指向 `backend/../data/processed/`），说明当前数据库里的数据可能来自 bootstrap 或手工导入。

### 修复建议
确认数据源文件的位置和可用性。如果没有外部数据源文件，考虑在 bootstrap 阶段塞入更多样例数据，让这些表在演示时不为空。

---

## 四、功能缺口 #4：Dashboard 趋势图硬编码 + avgLatency 缺后端字段

### 4.1 近 7 天柱状图
`frontend/src/views/admin/Dashboard.vue` 第 139-140 行：
```js
const trendDays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const trendValues = [42, 58, 35, 67, 89, 120, 75];  // 假数据
```

后端 `GET /api/insights/qa-trend` 已经返回近 30 天真实数据，但 Dashboard 没接。

**修复**: Dashboard.vue 在 onMounted 中 import fetchQATrend，用 daily_trend 替换硬编码数组。

### 4.2 avgLatency 缺后端字段
`AdminOverview` schema 没有 `avg_latency_ms` 字段。chat_logs 表有 `latency_ms` 列。

**修复**: 
1. `schemas/admin.py` 的 AdminOverview 加 `avg_latency_ms: float = 0`
2. `api/admin.py` 的 admin_overview 函数加 `AVG(ChatLog.latency_ms)` 查询

---

## 五、已修复问题（供上下文，无需处理）

1-11 见之前对话。包括：API 路径修正、图表内存泄漏、路由鉴权、分页、loading 态、Live2D 错误提示等。

---

## 六、修复优先级

| 优先级 | 问题 | 影响 |
|--------|------|------|
| **P0** | 知识盲区始终为空 | 盲区管理、盲区Top10功能无效 |
| **P0** | 用户画像无法增长 | 游客画像数始终接近0，游客分析饼图无效 |
| **P1** | avgLatency 缺后端字段 | 数据大屏平均延迟显示 "--" |
| **P1** | Dashboard 趋势图硬编码 | 演示数据与实际不符 |
| **P2** | 多条表仅 admin sync 写入 | 正常（已有数据），确保演示前跑一次 sync |

---

## 七、关键代码位置速查

```
漏洞 #1（盲区空）:
  backend/app/services/qa/pipeline.py:130-135  ← blind_spot_tracker.record() 调用点
  backend/app/services/qa/blind_spot_tracker.py:21-47  ← record() 实现

漏洞 #2（画像空）:
  backend/app/services/qa/pipeline.py:207,256  ← ChatLog 写入处（应在此加 Visitor 写入）
  backend/app/repositories/visitor.py:19-33  ← upsert() 实现
  backend/app/api/recommend.py:21  ← 唯一现有调用点

漏洞 #4.2（avgLatency）:
  backend/app/schemas/admin.py:6-14  ← AdminOverview（需加字段）
  backend/app/api/admin.py:64-74  ← admin_overview（需加查询）
  backend/app/models/chat_log.py:21  ← latency_ms 列已存在

漏洞 #4.1（趋势图）:
  frontend/src/views/admin/Dashboard.vue:139-140  ← 硬编码
  backend/app/api/insights.py:124-159  ← qa-trend 已实现
```
