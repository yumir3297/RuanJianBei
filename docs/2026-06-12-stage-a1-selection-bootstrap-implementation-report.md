# 阶段 A1 实施报告：主动选择数据契约与 Bootstrap API

- 日期：2026-06-12
- 状态：本切片已完成并通过回归，等待用户确认下一切片
- 对应主线：`设计文档/10-最终总体设计与开发主线.md` 主线阶段 A / 轨道 A1

## 一、本切片目标

只建立游客主动选择的后端数据契约和初始化读取接口，为下一切片的前端选择组件与 Pipeline 注入提供稳定基础。

本切片完成后：

1. `ChatRequest` 可以携带结构化 `SelectionContext`。
2. 话题按钮由数据库配置，不写死在前端。
3. 景点选项读取现有 `KnowledgeEntry`。
4. 路线选项读取现有 `RouteTemplate`。
5. 前端可以通过一个 bootstrap API 获取全部初始选择数据。

## 二、明确不做

1. 不修改 `QAPipeline` 的问答逻辑。
2. 不实现选择冲突解析、metadata 检索过滤和缓存键调整。
3. 不实现前端 GoalSelector、面包屑和快捷追问。
4. 不实现 FAQ L3、知识盲区或 Reranker 调参。
5. 不引入新依赖、Redis、SessionContext 或迁移框架。

## 三、接口与数据结构

### 3.1 SelectionContext

新增 `backend/app/schemas/selection.py`：

```python
class SelectionContext(BaseModel):
    mode: Literal["free_chat", "topic", "attraction", "route"] = "free_chat"
    attraction_id: int | None = None
    topic_key: str | None = None
    route_id: str | None = None
    interests: list[str] = Field(default_factory=list)
    audience_type: str | None = None
    available_hours: int | None = None
    avoid_crowded: bool | None = None
```

`ChatRequest` 新增：

```python
selection: SelectionContext | None = None
```

本切片只接收并校验该字段，不改变当前问答行为。

### 3.2 QuickTopic

新增 `quick_topics` 表，只保存 UI/领域配置：

1. `key`：稳定键。
2. `label`：游客可见名称。
3. `category`：`knowledge`、`recommend` 或 `faq`。
4. `icon`：前端图标键，不保存图片文件。
5. `sort_order`：显示顺序。
6. `is_enabled`：是否展示。

表中不保存景区事实、检索关键词或 LLM Prompt。

### 3.3 Bootstrap API

新增：

```text
GET /api/quick-select/bootstrap
```

返回：

1. `topics`：启用的话题配置。
2. `attractions`：`KnowledgeEntry.category == "景点信息"` 的真实景点。
3. `routes`：现有路线模板。

景点响应包含数据库 ID、标题、所属景区和资料中的稳定景点编码；不会返回完整知识正文。

## 四、预计文件改动

新增：

1. `backend/app/models/quick_topic.py`
2. `backend/app/repositories/quick_topic.py`
3. `backend/app/schemas/selection.py`
4. `backend/app/api/quick_select.py`
5. `backend/app/tests/test_quick_select.py`

修改：

1. `backend/app/models/__init__.py`
2. `backend/app/schemas/chat.py`
3. `backend/app/repositories/knowledge.py`
4. `backend/app/db/bootstrap.py`
5. `backend/app/api/router.py`
6. `backend/main.py`

## 五、风险与控制

### 风险 1：复制景区事实

控制：QuickTopic 不保存事实；景点和路线复用现有表。

### 风险 2：已有数据库无法自动增加表

控制：本轮只新增表，`create_all` 可以创建；不修改已有表字段。

### 风险 3：SelectionContext 字段互相矛盾

控制：本切片只做字段级校验；模式与实体一致性将在 Pipeline 注入切片统一处理，避免在 schema 和业务层重复规则。

### 风险 4：景点 metadata 格式异常

控制：API 安全解析 JSON；异常时只省略可选的景区名和稳定编码，不影响列表返回。

### 风险 5：破坏现有 ChatRequest

控制：`selection` 默认为 `None`，现有调用方无需修改，现有测试必须继续通过。

## 六、验收标准

1. 旧版 `ChatRequest` 仍可通过校验。
2. 新版 `ChatRequest` 可完整解析 `SelectionContext`，列表字段不共享默认值。
3. QuickTopic 默认数据可重复初始化且不产生重复记录。
4. bootstrap 只返回启用话题。
5. bootstrap 返回数据库中的 22 个景点和 3 条路线（以当前资料库为基线）。
6. 景点 ID 可回查现有 `KnowledgeEntry`。
7. API 不返回知识正文，不把按钮配置当作事实源。
8. 新增测试通过，现有后端测试全部通过。
9. `compileall` 通过。

## 七、分步审查点

1. 完成 schema/model/repository 后，先运行新增模块测试和静态编译。
2. 完成 API/路由/bootstrap 后，运行 endpoint 测试。
3. 最后运行完整后端测试，核对未进入本切片之外的功能。

## 八、实际完成结果

已完成：

1. 新增结构化 `SelectionContext`，并以可选字段接入 `ChatRequest`。
2. 新增 `quick_topics` 表和按显示顺序读取启用话题的仓储。
3. 新增 8 个默认话题配置，重复启动不会产生重复记录。
4. 新增 `GET /api/quick-select/bootstrap`。
5. 景点从现有 `KnowledgeEntry(category="景点信息")` 读取。
6. 路线从现有 `RouteTemplate` 读取。
7. 景点 metadata 异常时安全降级，不影响列表主体。
8. 新增 schema、仓储和 API 自动化测试。

未进入：

1. 未修改 `QAPipeline`。
2. 未修改前端。
3. 未实现选择检索、冲突处理、快捷追问或缓存键。
4. 未引入新依赖。

## 九、验证证据

```text
新增专项测试：2 passed
完整后端回归：22 passed
compileall：通过
真实应用接口：HTTP 200
真实 bootstrap：8 topics / 22 attractions / 3 routes
```

结论：本切片满足既定验收标准，可以停止并等待下一步确认。
