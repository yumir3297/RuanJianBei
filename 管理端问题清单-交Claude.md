# 管理端问题清单 · 交 Claude 修复

> 项目: 数字人智能导览系统
> 架构: Vue 3 + Element Plus (frontend/) / FastAPI + SQLAlchemy (backend/)
> 日期: 2026-06-21

---

## 〇、关键文件路径速查

```
frontend/src/
  api/admin.js            -- 管理端 API 调用
  api/insights.js         -- 数据洞察 API 调用
  api/knowledge.js        -- 知识库 CRUD
  stores/admin.js         -- Pinia store
  views/admin/Dashboard.vue
  views/admin/AnalyticsReport.vue
  views/admin/AvatarConfig.vue
  views/admin/BlindSpotManage.vue
  views/admin/KnowledgeManage.vue
  views/admin/AdminLogin.vue   -- 新增登录页
  stores/auth.js               -- 新增 auth store

backend/app/
  api/router.py           -- 路由注册
  api/admin.py            -- /api/admin/* 端点
  api/insights.py         -- /api/insights/* 端点
  api/knowledge.py        -- /api/knowledge/* 端点
  schemas/admin.py        -- AdminOverview, AnalyticsItem 等
  schemas/insights.py     -- SpotAttentionItem, QATrend 等
  models/chat_log.py      -- ChatLog 表 (有 latency_ms 列)
  models/visitor.py       -- VisitorProfile 表
  models/avatar_config.py -- AvatarConfig 表
  models/knowledge.py     -- KnowledgeEntry 表
```

---

## 一、数据真实性核验结论

### 1.1 有真实后端支撑（✅ 无需修改）

以下指标均来自后端 SQL 实时查询，数据可靠：

| 页面 | 指标 | 后端端点 | 数据来源 |
|------|------|----------|----------|
| Dashboard | 知识条目/FAQ/游客/日志数 | `GET /api/admin/overview` | 各 Repository.count() |
| Dashboard | analytics 详细列表 | `GET /api/admin/analytics` | 各表 count |
| AnalyticsReport | 景点关注度 Top10 | `GET /api/insights/spot-attention` | chat_logs.sources JSON 聚合 |
| AnalyticsReport | 游客群体饼图 | `GET /api/insights/visitor-groups` | visitor_profiles.audience_type 分组 |
| AnalyticsReport | 近30天问答趋势 | `GET /api/insights/qa-trend` | chat_logs.created_at GROUP BY date |
| AnalyticsReport | 命中路径分布 | `GET /api/insights/qa-trend` | chat_logs.hit_level 分组 |
| AnalyticsReport | 盲区 Top10 表格 | `GET /api/insights/blind-spot-top` | knowledge_blind_spots |
| BlindSpotManage | 盲区列表 | `GET /api/admin/blind-spots` | knowledge_blind_spots |
| KnowledgeManage | CRUD | `GET/POST/PUT/DELETE /api/knowledge/` | knowledge_entries |
| Dashboard | 知识资产饼图 | 同 overview | 各 Repository.count() |

### 1.2 缺乏真实支撑（❌ 需修复）

| 位置 | 问题 | 根因 |
|------|------|------|
| **Dashboard 近7天柱状图** | 硬编码 `[42,58,35,67,89,120,75]` | 未对接 `/insights/qa-trend` |
| **AnalyticsReport avgLatency** | 当前返回 `"--"` | AdminOverview schema 无 avg_latency_ms 字段 |
| **AvatarConfig 配置持久化** | API 路径对不上 | 前端调 `/admin/avatar-config`，后端是 `/admin/avatar-configs/active` |

---

## 二、已修复问题（供上下文，无需处理）

以下 11 个问题已经修复，Claude 不需要处理：

1. `insights.js` 所有 API 路径有双重 `/api` 前缀 → 已去掉
2. `AnalyticsReport.vue` 4 个 ECharts 实例无 `onBeforeUnmount` 清理 → 已加
3. `HomePage.vue` 管理端入口跳 `/admin/blind-spots` → 改为 `/admin/dashboard`
4. `BlindSpotManage.vue` FAQ ID 含中文/空格/特殊字符 → 正则净化
5. `AnalyticsReport.vue` avgLatency 硬编码 2.3 → 改为读 overview.avg_latency_ms
6. `AvatarConfig.vue` 仅存 localStorage → 已加后端 API 调用（路径需修正，见下文）
7. 管理端零鉴权 → 已加 `AuthLogin.vue` + `stores/auth.js` + 路由守卫
8. `insights.js` 和 `admin.js` 重复 `fetchOverview` → 删 insights 版
9. `AnalyticsReport` 各图表无独立 loading → 加 skeleton
10. `AvatarConfig` Live2D 加载失败无提示 → 加 ElMessage + 覆盖层
11. `KnowledgeManage`/`BlindSpotManage` 无分页 → 加 el-pagination

---

## 三、待修复问题

### 🔴 P0：AvatarConfig API 路径 + 数据格式不匹配

**文件**: `frontend/src/api/admin.js` + `frontend/src/views/admin/AvatarConfig.vue`

**现状**:
```js
// admin.js 中我刚加的两个函数 —— 路径错误
export async function fetchAvatarConfig() {
  const { data } = await http.get("/admin/avatar-config");  // ← 错误
  return data;
}
export async function saveAvatarConfig(payload) {
  const { data } = await http.put("/admin/avatar-config", payload);  // ← 错误
  return data;
}
```

**后端实际**:
```python
# GET /api/admin/avatar-configs/active → 返回 {id, name, model_path, voice_type, is_active}
# PUT /api/admin/avatar-configs/{id}/activate → 激活某个配置
# 模型字段: id, name, model_path, voice_type, is_active  (没有 speechRate, volume)
```

**需要做的事（二选一）**:

**方案 A — 改前端对接现有端点（推荐，不动后端）**:
1. 修改 `admin.js` 的 `fetchAvatarConfig` 调用 `/admin/avatar-configs/active`
2. 修改 `admin.js` 的 `saveAvatarConfig` 改为调用 `/admin/avatar-configs/{id}/activate`（需先从 active 获取 id）
3. `AvatarConfig.vue` 的 `handleSave` 中 `modelKey` 映射到 `model_path`，`voiceType` 直接用
4. `speechRate` 和 `volume` 回到 localStorage（后端无此字段）

**方案 B — 后端新增兼容端点**:
在 `admin.py` 加:
```python
@router.get("/avatar-config")
async def get_active_avatar_config_simple(session): ...

@router.put("/avatar-config")  
async def save_avatar_config(payload: AvatarConfigSimpleRequest, session): ...
```
并在 `avatar_configs` 表加 `speech_rate` / `volume` / `model_key` 字段。

---

### 🔴 P0：AdminOverview 缺少 avg_latency_ms

**后端文件**: `backend/app/schemas/admin.py`, `backend/app/api/admin.py`
**前端文件**: `frontend/src/views/admin/AnalyticsReport.vue`

**需修改 3 处**:

1. `schemas/admin.py` — 给 AdminOverview 加字段:
```python
class AdminOverview(BaseModel):
    # ... 现有字段不动
    avg_latency_ms: float = 0   # 新增
```

2. `api/admin.py` — admin_overview 函数加查询:
```python
from sqlalchemy import func, select
from app.models.chat_log import ChatLog
# 在 admin_overview 里加:
avg_latency = session.execute(
    select(func.avg(ChatLog.latency_ms))
).scalar()
return AdminOverview(
    # ... 现有字段不动
    avg_latency_ms=round(float(avg_latency or 0), 1),
)
```

3. 前端 `AnalyticsReport.vue` 已有处理:
```js
// 已改为读取 overview.avg_latency_ms，无需再改
const avgLatency = computed(() => {
  const avg = overview.value.avg_latency_ms ?? overview.value.avg_latency;
  if (avg != null) return (Number(avg) / 1000).toFixed(1);
  return "0.0";
});
```

---

### 🟡 P1：Dashboard 近7天柱状图硬编码

**文件**: `frontend/src/views/admin/Dashboard.vue`

**现状**:
```js
const trendDays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const trendValues = [42, 58, 35, 67, 89, 120, 75];  // ← 假数据
```

**修复**:
1. 在 `Dashboard.vue` import `fetchQATrend` from `../../api/insights`
2. 在 `loadDashboard` 或 `onMounted` 里请求 `/insights/qa-trend`，取 `daily_trend`
3. 将 `daily_trend` 的 date/count 映射到 `trendDays`/`trendValues`
4. 图表已通过 echarts 注册 BarChart，无需改配置

**后端已有数据**: `GET /api/insights/qa-trend` 返回 `{ daily_trend: [{date: "2026-06-19", count: 42}, ...], hit_distribution: [...] }`

---

### 🟢 P2：（可选）登录无后端认证

当前 `stores/auth.js` 纯前端比较密码 `admin123`，无后端 JWT。
如需后端认证再处理；软件杯演示可接受。

---

## 四、API 端点对照（标记不匹配项）

| 前端调用 | 后端端点 | 匹配 |
|----------|----------|------|
| GET /admin/overview | GET /api/admin/overview | ✅ |
| GET /admin/analytics | GET /api/admin/analytics | ✅ |
| GET /admin/blind-spots | GET /api/admin/blind-spots | ✅ |
| POST /admin/blind-spots/{id}/resolve-with-faq | POST /api/admin/blind-spots/{id}/resolve-with-faq | ✅ |
| POST /admin/sync-processed-data | POST /api/admin/sync-processed-data | ✅ |
| POST /admin/build-rag-index | POST /api/admin/build-rag-index | ✅ |
| **GET /admin/avatar-config** | **GET /api/admin/avatar-configs/active** | ❌ |
| **PUT /admin/avatar-config** | **PUT /api/admin/avatar-configs/{id}/activate** | ❌ |
| GET /insights/spot-attention | GET /api/insights/spot-attention | ✅ |
| GET /insights/visitor-groups | GET /api/insights/visitor-groups | ✅ |
| GET /insights/qa-trend | GET /api/insights/qa-trend | ✅ |
| GET /insights/blind-spot-top | GET /api/insights/blind-spot-top | ✅ |
| CRUD /knowledge/ | CRUD /api/knowledge/ | ✅ |

---

## 五、相关数据表结构（供参考）

```python
# ChatLog
id, session_id, raw_query, normalized_query, answer, sources(Text/JSON),
hit_level(String), latency_ms(Integer), created_at(DateTime)

# VisitorProfile  
id, session_id, preference_tags(Text/JSON), audience_type(String), last_seen_at

# KnowledgeEntry
id, title, category, content, source, aliases(Text/JSON)

# AvatarConfig
id, name, model_path, voice_type, is_active
```
