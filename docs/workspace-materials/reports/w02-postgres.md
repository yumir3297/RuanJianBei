# W02 PostgreSQL 隔离验证

2026-10-30：验证受沙箱阻止，未能启动 PostgreSQL，未执行多 worker、租约或旧 fence 的 PostgreSQL 测试，因此不能声称这些路径已在 PostgreSQL 通过。

尝试使用 `/opt/homebrew/opt/postgresql@17/bin/initdb`，数据目录为新建的 `/private/tmp/codex-w02-pg.orfaF2/data`，认证仅用于临时实例。初始化在 bootstrap 阶段失败：`could not create shared memory segment: Operation not permitted`，失败系统调用为 `shmget`；`initdb` 自动移除了未完成的数据目录。没有启动服务、分配端口、访问现有数据库、读取真实密钥或调用供应商。按任务限制停止，没有请求提权。空的临时父目录保留，未删除其他文件。

建议在允许 PostgreSQL 共享内存的隔离运行环境中补测：新建临时实例与随机端口、运行迁移；两个独立连接并发领取同一任务，断言恰好一个成功；让租约过期并由维护任务重排后重新领取，验证 fence 递增、旧 worker 无法完成；外部调用标记后模拟崩溃，断言等待人工确认且不重复调用 fake provider；最后停止专用实例。以上是待验证方案，SQLite 结果不替代 PostgreSQL 锁和并发语义。
