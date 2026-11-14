# 管理端/游客端发布矩阵

状态：**模板；当前没有目标服务器部署记录**。每次发布复制一行或另存带日期的记录，不预填推测的当前版本。

## 部署识别

| 字段 | 记录 |
|---|---|
| 发布 ID / 日期（UTC） | 未部署 |
| 环境 / 目标主机代号 | 未定 |
| OS / CPU / Docker Engine / Compose / NGINX | 未定 |
| 游客 HTTPS origin / TLS 终止点 | 未定 |
| 管理 HTTPS origin / TLS 终止点 | 未定 |
| 维护窗口 / 操作人与复核人 | 未安排 |
| 当前验收结论 | 未验收；不得放量 |

## 组件版本

| 组件 | 当前版本 | 候选版本 | 放量后版本 | 证据/备注 |
|---|---|---|---|---|
| Git commit / source SHA | 未部署 | 待干净提交 | 未部署 | 候选清单与 OCI revision label 必须一致 |
| 游客端 release ID / SHA-256 manifest | 未部署 | 待构建 | 未部署 | 单独 `current`/`previous`；真实 HTTPS 冒烟待验 |
| 管理端 release ID / SHA-256 manifest | 未部署 | 待构建 | 未部署 | 单独 `current`/`previous`；真实 HTTPS 冒烟待验 |
| 后端镜像 ID / schema head | 未部署 | 待目标平台构建 | 未部署 | Compose 命名 `api` image 与候选 metadata 必须匹配 |
| 后端 capabilities | 未部署 | 待接口审核 | 未部署 | 游客包要求 visitor config、chat SSE、feedback、guide context；管理包要求 admin runtime limits/auth/knowledge import |
| Python / wheel hash 锁 / OS 包 | 未部署 | 目标 CPU 未定 | 未部署 | 当前 requirements/Dockerfile 不构成完整平台锁证明 |
| PostgreSQL版本 / schema head | 未知 | 隔离副本验证 | 未部署 | 禁止由连接串推断版本或迁移安全 |
| 模型权重 / FFmpeg / ffprobe | 未知 | 目标机测量 | 未部署 | 记录路径、权重来源、校验和与可用磁盘 |

## 数据与回滚证据

| 项目 | 发布前证据 | 发布后/演练证据 | 状态 |
|---|---|---|---|
| PostgreSQL一致性快照 | 备份 ID/位置/校验和 | 隔离 `pg_restore` 报告及schema/业务计数对比 | 未测 |
| APP_STATE_ROOT归档 | 归档 ID/位置/manifest hashes | 隔离恢复目录、Chroma/revision/uploads一致性 | 未测 |
| 备份保留 / RPO / RTO | 运营批准的数字 | 保留扫描、故障恢复开始/结束UTC时间 | 未确认 |
| 游客A→B→A | 当前/候选 release ID | 每次URL、旧新asset HTTP状态、业务数据无变化证据 | 未测 |
| 管理A→B→A | 当前/候选 release ID | 登录/限额/知识管理冒烟、另一端不变证据 | 未测 |
| 后端失败路径 | 已确认维护窗口与备份 | 迁移/API/代理失败状态，停流量与恢复决策 | 未测 |
| 游客身份连续性 | 当前 origin 与cookie盘点 | 老匿名身份在新前端可继续，或经批准的迁移记录 | 未测 |

## 最终验收引用

| 门槛 | 证据位置 | 状态 |
|---|---|---|
| M1 环境与来源可追溯 | 目标机信息、image inspect、候选metadata、TLS/origin记录 | 未测 |
| M2 身份与数据边界 | 双 origin 浏览器/HTTP 测试、Cookie/CSRF/owner证据 | 未测 |
| M3 数据迁移与恢复 | 隔离 PostgreSQL与app-state实际恢复报告 | 未测 |
| M4 端到端业务 | 经许可景区资料 revision、真实供应商聊天/ASR/TTS结果 | 未测 |
| M5 独立发布回滚 | 两端独立 A→B→A 与实际HTTP资源证据 | 未测 |
| M6 运行容量与可靠性 | 批准SLO、压力轨迹、峰值资源和超限行为 | 未测 |
| M7 设备与降级 | 已批准设备/浏览器/WebView逐台记录 | 未测 |
| M8 备份目标 | 已批准保留/RPO/RTO及真实演练结果 | 未测 |

任何 Must 门槛为“失败”或“未测”，最终结论保持“暂缓放量”。
