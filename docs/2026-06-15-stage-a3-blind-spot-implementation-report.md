# 阶段 A3.2 知识盲区后端闭环实施报告

- 日期：2026-06-15
- 状态：已完成并通过测试
- 执行摘要：`docs/2026-06-15-stage-a3-blind-spot-execution-summary.md`
- 主线依据：`设计文档/10-最终总体设计与开发主线.md`

## 完成内容

1. 新增 `knowledge_blind_spots` 表，字段与批准方案一致。
2. `normalized_query` 使用唯一索引，`status` 使用普通索引。
3. RAG 无证据时自动记录盲区；FAQ、缓存或 RAG 有证据时不记录。
4. 相同规范化问题自动累加 `hit_count`，最多保留 5 个去重原始问题样本。
5. 超过 500 字符的规范化问题使用“前缀 + SHA-256”生成稳定聚合键，避免截断碰撞。
6. 盲区记录异常只写日志，不阻断游客收到证据不足降级回答。
7. 新增管理查询和 FAQ 解决接口。
8. 解决时可创建或更新 FAQ，并自动合并管理员别名与盲区原始样本。
9. 答案来源强制非空，系统不自动编写景区事实。
10. FAQ 与盲区状态在同一数据库事务中提交，随后刷新 L1/L2/L3 运行时索引。
11. 官方资料再次同步时，自动保护被已解决盲区引用的人工 FAQ，不会将其清空。

## 新增接口

```text
GET /api/admin/blind-spots?status=open&limit=50
POST /api/admin/blind-spots/{id}/resolve-with-faq
```

`resolve-with-faq` 请求字段：

```text
faq_id: 1-120 字符
category: 1-50 字符
aliases: 1-20 个非空别名
answer: 非空答案
sources: 1-20 个非空来源
```

列表默认只返回 `open`，可传 `status=resolved`；结果按命中次数、最近出现时间和 ID 倒序排列。

## 状态与审计

解决后保留原记录并写入：

```text
status = resolved
resolution_type = faq
resolved_faq_id = 管理员提交的 FAQ ID
resolved_at = 解决时间
category = 管理员提交的 FAQ 分类
```

不物理删除盲区记录，不在盲区表复制最终答案。

## 验证结果

1. 盲区聚合、长问题键、Pipeline 无证据记录专项测试通过。
2. 管理查询、排序、输入校验、404、FAQ 创建和 FAQ 更新测试通过。
3. 补录后原始问题可由 `FAQMatcher` 精确命中。
4. 官方 FAQ 再同步后，人工解决 FAQ 仍保留；88 条官方 FAQ + 1 条人工 FAQ = 89 条。
5. 后端完整回归：`52 passed`。
6. 评测工具回归：`3 passed`。
7. `compileall` 通过。
8. 真实 `app.db` 已通过 `create_all` 创建 12 列新表。
9. 真实 `GET /api/admin/blind-spots` 返回 HTTP 200。
10. OpenAPI 已注册两个盲区管理端点。

## 分段审查结论

1. 模块性：ORM、仓储、跟踪、解决服务和 API Schema 分离。
2. 可添加性：保留 `resolved_knowledge_id`，后续可单独增加 `link-knowledge`。
3. 可阅读性：Pipeline 只调用跟踪服务，不包含 SQL 或 JSON 聚合逻辑。
4. 可靠性：记录失败不影响回答；唯一索引和冲突重试降低并发重复记录风险。
5. 事实安全：必须由管理员提交答案和来源，不让模型自动填补知识盲区。
6. 持久性：资料同步保护已解决盲区关联的 FAQ。

## 明确未做

1. 未实现 `POST /api/admin/blind-spots/{id}/link-knowledge`。
2. 未开发管理端前端页面，该页面归入阶段 C 管理后台。
3. 未触发或隐式重建 Chroma。
4. 未修改依赖、模型供应商、多模态、ASR、TTS 或 Avatar。

## 当前停止点

A3.2 后端最小闭环完成。按照执行摘要停止，不自动进入下一阶段。
