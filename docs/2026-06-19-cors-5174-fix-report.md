# 修复版前端 5174 CORS 接入报告

## 1. 修改

已更新 `backend/.env`：

```text
CORS_ORIGINS=
http://localhost:5173,
http://127.0.0.1:5173,
http://localhost:5174,
http://127.0.0.1:5174
```

保留原有 5173，同时加入修复版前端 5174。

## 2. 启动

后端模型预加载需要约 30 秒。等待完成后：

```text
GET /health -> 200
service = A5 Scenic Guide AI
```

## 3. CORS 验证

以下 Origin 对 `POST /api/chat/stream` 的 OPTIONS 预检均通过：

```text
http://127.0.0.1:5173 -> 200
http://localhost:5173 -> 200
http://127.0.0.1:5174 -> 200
http://localhost:5174 -> 200
```

每个响应均返回与请求 Origin 一致的 `Access-Control-Allow-Origin`。

## 4. 结论

修复版前端 `http://127.0.0.1:5174/` 已可访问后端 8000，不再因 CORS 显示 `Failed to fetch`。

本轮自动验证使用的后端子进程在测试命令结束后被执行环境回收，没有作为常驻服务保留。使用页面前需在本地终端启动：

```powershell
cd D:\桌面\软件杯\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

模型预加载约需 30–40 秒，看到 `Application startup complete` 后再刷新前端。
