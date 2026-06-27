# 阶段 A1 实施报告：游客端主动选择前端闭环

- 日期：2026-06-12
- 状态：本切片已完成并通过构建/回归，等待用户确认下一切片
- 对应主线：`设计文档/10-最终总体设计与开发主线.md` 主线阶段 A / 轨道 A1
- 前置能力：`GET /api/quick-select/bootstrap` 已完成并通过回归

## 一、本切片目标

将已完成的主动选择 bootstrap API 接入游客端，使游客可以先选择交互目标、景点、话题或路线，再发送文本问题。

本切片完成后：

1. 页面启动时获取可用话题、景点和路线。
2. 游客可在自由提问、景点讲解、话题探索和路线规划之间切换。
3. 当前选择通过面包屑展示。
4. 选择状态由独立 Pinia store 管理并保存到 `localStorage`。
5. 每次聊天请求携带完整 `SelectionContext`。

## 二、明确不做

1. 不修改后端 `QAPipeline`。
2. 不实现选择冲突解析和 metadata 检索过滤。
3. 不实现回答后的快捷追问。
4. 不实现连续多轮的服务端上下文事件。
5. 不实现真实语音录制、FAQ L3 或 Reranker 调参。

因此本切片中的选择功能负责收集和传递上下文，但暂时不会改变后端检索结果。界面会明确标注“检索增强将在下一切片接入”，避免误导。

## 三、最小实现方案

### 3.1 API

新增 `frontend/src/api/quickSelect.js`，只封装：

```text
GET /api/quick-select/bootstrap
```

### 3.2 Interaction Store

新增 `frontend/src/stores/interaction.js`：

1. 保存 bootstrap 数据、加载状态和错误状态。
2. 保存当前 mode、景点ID、话题key和路线ID。
3. 提供选择、清空、校验和序列化方法。
4. 使用固定版本的 `localStorage` key 保存状态。
5. bootstrap 加载后剔除已经不存在或被禁用的选择。

### 3.3 选择组件

新增 `frontend/src/components/interaction/GoalSelector.vue`：

1. 四种目标：自由提问、景点讲解、话题探索、路线规划。
2. 景点模式展示真实景点下拉选择，并允许附加话题。
3. 话题模式展示后端话题按钮。
4. 路线模式展示真实路线卡片。
5. 显示加载失败、重试、空数据和当前选择面包屑。
6. 使用当前项目的浅色卡片风格，不引入新视觉依赖。

### 3.4 聊天请求

`chatStore.sendMessage` 新增可选 `selection` 参数，并写入现有 SSE 请求体。

`ChatView` 初始化 interaction store，并在发送消息时传入 `selectionPayload`。

## 四、预计文件改动

新增：

1. `frontend/src/api/quickSelect.js`
2. `frontend/src/stores/interaction.js`
3. `frontend/src/components/interaction/GoalSelector.vue`

修改：

1. `frontend/src/stores/chat.js`
2. `frontend/src/views/tourist/ChatView.vue`

不修改后端业务代码。

## 五、风险与控制

### 风险 1：本地缓存包含失效选择

控制：加载bootstrap后校验景点、话题和路线ID，不存在则清空对应字段。

### 风险 2：自由提问仍携带旧字段

控制：切换到 `free_chat` 时清空全部结构化选择。

### 风险 3：选择状态与聊天store耦合

控制：interaction store独立维护；chat store只接收普通对象参数。

### 风险 4：后端尚未消费选择

控制：本轮只验证请求携带和前端状态，不宣称检索已增强。

### 风险 5：移动端空间不足

控制：目标按钮和路线卡片使用响应式网格，小屏改为单列。

## 六、验收标准

1. bootstrap加载成功时展示8个话题、22个景点和3条路线（当前数据基线）。
2. API失败时页面可见错误且可以重试，聊天文本输入仍可使用。
3. 选择景点、话题或路线后面包屑立即更新。
4. 刷新页面后选择能够恢复。
5. 后端数据不存在时，失效选择自动清理。
6. 自由提问模式发送 `mode=free_chat`，不携带旧实体ID。
7. 聊天POST请求携带结构化 `selection`。
8. `npm run build` 通过。
9. 后端完整测试继续通过。
10. 范围审查确认未修改 `QAPipeline`。

## 七、分步审查

1. API和store完成后先运行前端构建。
2. 组件和聊天页完成后再次运行前端构建。
3. 最后运行后端完整测试并核对修改范围。

## 八、实际完成结果

已完成：

1. 新增 quick-select API 封装。
2. 新增独立 interaction Pinia store。
3. 支持 bootstrap 加载、错误重试、localStorage 恢复和失效 ID 清理。
4. 新增目标、景点、话题、路线选择组件。
5. 新增当前选择面包屑与聊天输入区上下文提示。
6. 聊天请求已携带完整 `selection` 对象。
7. 自由提问会清空旧景点、话题和路线。
8. 景点选择清空值会规范化为 `null`，不会生成 ID 0。

未进入：

1. 未修改后端 `QAPipeline`、RAG 或缓存。
2. 未新增依赖。
3. 未实现选择感知检索和冲突解析。
4. 未实现快捷追问。

## 九、验证证据

```text
前端 npm run build：通过
Vite transformed modules：1688
后端完整回归：22 passed
SelectionContext 请求序列化：通过
dist index 与 JS bundle：存在且可读取
```

构建仍报告现有单一 JS chunk 大于 500kB 的警告，不影响本切片功能；代码分包留到前端整体优化阶段。

当前会话没有可用的应用内浏览器控制接口，因此未完成自动化点击与截图级视觉检查。该项属于验证缺口，不影响构建和后端回归结论；后续可在服务启动后的人工验收或具备浏览器工具的会话中补做。

## 十、结论

本切片完成了“前端采集并传递选择上下文”的闭环，但后端尚未消费该上下文。下一切片应单独实现服务端选择校验、文字实体优先冲突规则和选择感知检索，不能把当前页面展示误认为检索已经增强。
