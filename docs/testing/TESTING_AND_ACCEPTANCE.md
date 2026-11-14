# 测试、验收与边界总表

本文档是测试和验收总入口。详细日志保留在各功能文档中；本表不把模拟、stub、fake 数据库或静态检查写成真实环境通过。

## 当前验收矩阵

| 范围 | 当前本地证据 | 未覆盖边界 |
|---|---|---|
| 双端入口与构建 | 游客/管理独立构建、边界和 build isolation 检查 | 真实 HTTPS origin、TLS、NGINX 和 CDN |
| 知识管理 | 草稿隔离、稳定景点编号、发布 revision、游客目录和来源核对 | 真实资料、生产数据库和完整管理 UI 逐页验收 |
| 游客问答 | 已发布资料普通问答、来源显示、流式取消和安全暂停 | 真实模型质量、真实供应商和多设备音频 |
| CASS | 模拟预警、确认、显式恢复、迟到响应隔离 | 真实预警源、GPS、接警和现场求助 |
| 行程提案 | 独立 worker、预览、确认保存、幂等重放和来源标识 | 真实模型、目标数据库、多实例竞争和真机弱网 |
| 离线陪游 | 游客构建、缓存、断网、地图、求助、恢复提示 16/16 | 真机蜂窝网络、生产发布升级和代理 |
| GuideMatch | 训练包完整性、CPU 小模型续训、候选权重受限加载 | CUDA 正式训练、独立真实测试集、当前问答链路接入 |
| 数据库/部署 | SQLite/Alembic、部分临时 PostgreSQL、发布锁专项 | 目标 PostgreSQL、真实备份恢复、Docker/NGINX/服务器 |

## 验收分层

1. 静态核对：文件、路由、schema、配置和代码地图存在且链接有效。
2. 单元/服务测试：隔离 SQLite、fake provider 或内存替身验证协议和状态边界。
3. 本地浏览器联调：真实本机 API、worker、两个 Vite origin 和 Chrome 串联。
4. 真实环境验收：真实资料、模型、数据库、供应商、设备、网络和目标服务器。

前一层通过不能替代后一层。任何 Must 项为“未测”时，生产结论保持暂缓。

## 统一本地演示

```sh
DEMO_SYNTHETIC_CONFIRM=1 DEMO_ADMIN_PASSWORD='<本地演示密码>' \
DEMO_PYTHON="$PWD/backend/.venv/bin/python" \
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
./scripts/run_local_competition_demo.sh
```

当前统一入口覆盖知识发布、普通问答、行程提案、GuideLoop、CASS 和离线陪游。它使用合成资料、stub 音频、固定哈希向量和模拟断网，不能替代真实验收。

## 详细证据入口

- [比赛总验收](../integration/ACCEPTANCE.md)
- [本地演示手册](../integration/LOCAL_DEMO_RUNBOOK.md)
- [最终部署验收](../deployment/FINAL_ACCEPTANCE.md)
- [兼容性矩阵](../COMPATIBILITY.md)
- [离线陪游验收](../integration/OFFLINE_COMPANION.md)
- [GuideMatch 训练验收](../integration/GUIDEMATCH_TRAINING.md)
