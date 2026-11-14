# 文档资源库整理与旧文档处置清单

状态：本地总集成候选。线上旧文档尚未删除。

## 目标结构

| 入口 | 作用 |
|---|---|
| `docs/TECHNICAL_ARCHITECTURE_AND_INNOVATION.md` | 技术架构、框架组合、亮点、创新表述和边界总览 |
| `docs/frontend/` | 游客端/管理端前端设计和边界 |
| `docs/testing/` | 测试、验收层级、模拟边界和生产门槛 |
| `docs/integration/` | 当前整合过程、功能验收和本地演示证据 |
| `docs/deployment/` | 目标机、发布、回滚、备份和放量门槛 |

## 历史资料处置

- `docs/design/*`：保留原稿，由前端总入口引用。
- `docs/competition/*`：由技术架构/创新总览和测试入口承接，原稿暂不删除。
- `docs/plans/*`：保留历史计划，当前状态以验收总表为准。
- `docs/research/*`：保留研究依据，不作为实现验收证据。
- `docs/superpowers/*`：保留设计和过程追溯，不直接覆盖当前实现。
- `docs/selling-points/*`：保留证据型卖点，规划项继续标明未实现。

线上旧文件的移动和删除要在本地候选审阅后执行，并先检查相对链接、README 引用和回滚方式。
