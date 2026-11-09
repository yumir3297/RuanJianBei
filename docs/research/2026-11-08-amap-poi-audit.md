# 高德 POI 批量校对

官方接口：[POI 搜索](https://lbs.amap.com/api/webservice/guide/api/search/)。需要高德开放平台的 **Web 服务 API** 类型 Key。JS API Key 不是这里约定的配置。

将 `AMAP_WEB_SERVICE_KEY` 配置在后端本地 `backend/.env` 或运行进程环境中，不写到前端 `VITE_` 变量，不提交真实 Key。脚本不会打印请求 URL 或保存 Key。

从仓库根目录运行：

```sh
node scripts/audit_amap_pois.mjs --name 灵山大佛
node scripts/audit_amap_pois.mjs
```

默认以滨湖区 adcode `320211` 和 citylimit 查询，每个名称请求第一页20条候选，保存 POI ID、GCJ-02 location、地址、类别、parent 等字段。没有结果、同名、多个候选、候选在拈花湾或仅为景区总POI时，需要继续人工复核；不是选第一条直接发布。详情页 URL 可打开来源核对。

结果默认在 `output/amap-poi-audit.json`；若候选总数超过20，应继续细化查询/分页，不认为第一页已穷尽。脚本是单次审核工具，不启动后端、更新数据库或自动改游客地图。

本次环境检查：项目本地 `.env` 与进程中均未发现 AMAP_WEB_SERVICE_KEY；因此没有发送真实 API 请求。已运行语法检查、帮助与缺少 Key 的预检。仍需配置 Key 后执行真实查询，不能把脚本准备完称为点位核验完。
