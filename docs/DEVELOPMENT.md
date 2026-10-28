# 跨系统开发与验证

核验于 2026-10-28。所有命令标明 cwd；仓库相对路径适用于不同机器。
本页区分“可执行命令”和“已执行结果”：本次地图建设没有安装或启动业务环境。

## 1. 工具与运行条件

| 项目 | 要求及已知边界 |
|---|---|
| Node | [锁文件](../frontend/package-lock.json) 中 Vite/plugin-vue 要求 `^20.19.0 || >=22.12.0`；README 旧 `v20+` 条件过宽 |
| Python | README 以 3.13+ 为基线；原生包 wheel 是否支持所选 Python/OS/架构须另外核验，不能推导任意新版本都可装 |
| 后端依赖 | [requirements.txt](../backend/requirements.txt)；包含锁定的 `torch==2.12.0+cpu` 和 CPU 索引，macOS/ARM 等平台未验证能原样安装；如无匹配 wheel，应记录依赖兼容问题后另行调整，不擅自跳过依赖或替换版本 |
| 数据库 | [config.py](../backend/app/core/config.py) 默认 PostgreSQL；[session.py](../backend/app/db/session.py) 对 SQLite 有兼容分支，仍需分别验证迁移/查询 |
| 模型/数据 | 本地 embedding、reranker 缓存及处理数据不等于 Git 克隆内容；main lifespan 会预热模型 |
| ASR | 本地 SenseVoice 默认路径为 Windows `D:/...`；其他机器通过 `ASR_LOCAL_MODEL_DIR` 指向已准备好的模型目录 |
| 配置 | [backend/.env.example](../backend/.env.example) 为模板；实际 provider、数据库、模型路径须按运行环境配置，真实 key 不提交 |

## 2. 打开正确工作目录

建议把 `RuanJianBei` 仓库根目录作为 Codex 本地项目目录，从该目录开启新开发 chat。
当前 ChatGPT 项目外层目录和代码仓库是两层：外层 `sources/` 是只读同步参考；代码位于 `code/RuanJianBei/`。
如果仍从外层发起任务，应明确先读取仓库 `AGENTS.md` 以及所改目录的 AGENTS.md，不能假设后代文件会在启动时自动发现。

根 AGENTS.md 仅作短入口；[功能地图](REPO_MAP.md)、[架构](ARCHITECTURE.md)、[兼容性](COMPATIBILITY.md) 按任务读取。
其他 AI 工具可直接读取相同 Markdown；不要求安装 Codex 插件或专用索引服务。

## 3. 后端（cwd：仓库的 backend/）

macOS/Linux（`python3` 应指向选择的 Python 版本）：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，准备数据库/数据/模型，再启动
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell（`python` 应指向选择的 Python 版本）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，准备数据库/数据/模型，再启动
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

依赖安装须满足上一节的平台条件；命令不是“已保证全平台安装成功”。已有 `.env` 时跳过复制，避免覆盖。
直接调用 venv 解释器免去 PowerShell 激活脚本策略差异。`main:app` 是当前真实入口；旧计划中的 `app.main:app` 不适用。
启动会写数据库并加载本地模型；不要用启动来验证地图工具。

## 4. 前端（另开终端，cwd：frontend/）

各系统均可执行：

```sh
npm ci
npm run dev
```

通常访问 `http://localhost:5173`；端口被占用时以 Vite 输出为准。
现有锁文件优先用 `npm ci`；需要调整依赖时另行说明并更新锁文件。
生产构建 `npm run build`；`npm run preview` 仅预览构建，不自动复制 Vite dev 的后端代理配置。

## 5. 验证层级

| 层级 | cwd 与命令 | 能证明什么 |
|---|---|---|
| 地图链接/API | 根目录 `python scripts/check_repo_map.py` | 指定地图文档中的本地文件链接和显式 API 引用有效；不加载业务服务 |
| 地图工具回归 | 根目录 `python -m unittest discover -s scripts/tests -p "test_*.py"` | 工具能识别坏链接/失效 API，支持中文空格路径与 JSON 导出 |
| 前端构建 | frontend/ `npm run build` | 打包与模块解析；不等于手机权限、布局或音频实测 |
| 后端聚焦 | backend/ `<venv-python> -m pytest app/tests/test_chat_stream_api.py -q` | 该组测试结果；按 [功能地图](REPO_MAP.md) 换成相关文件 |
| 后端全量 | backend/ `<venv-python> -m pytest app/tests -q` | 当前环境下业务测试基线；记录实际失败，不套用历史通过数字 |
| 评测工具 | 根目录 `<venv-python> -m pytest eval/tests -q` | 评测工具自身回归；真实模型评测需另读脚本与服务条件 |
| 浏览器/真机 | [兼容性矩阵](COMPATIBILITY.md) | 具体设备、浏览器、网络条件下的用户行为 |

`<venv-python>` 替换为该系统虚拟环境 Python 的完整路径；`python` 是所选 Python 3，macOS/Linux 没有该命令时用 `python3`。
backend 测试通常依赖 `backend/` 在模块搜索路径中，优先从 backend/ 执行。
现有 [competition_check.ps1](../scripts/competition_check.ps1) 是 Windows 专用：依赖 Scripts/python.exe 和 cmd，不作为 macOS/Linux 入口。
前端 package.json 没有 test/lint 脚本，不能报告运行了 `npm test` 或 `npm run lint`。

## 6. 手机、平板访问开发机

- 手机和开发机处于可互通网络，用开发机 LAN IP 访问前端；手机的 `localhost` 指手机自身。
- Vite dev 默认代理到开发机的 `127.0.0.1:8000`，通常不用让每台手机直接连接后端端口。
- HTTP LAN 页面可能能显示文本 UI，但不能据此验收相机/录音/定位。需要浏览器信任的 HTTPS 及对应权限。
- 若配置 `VITE_API_BASE_URL`，值会进入前端构建，不能放秘密；跨源时同步检查 CORS、资源 URL、混合内容、SSE。
- 正式部署在服务端配置同源 `/api` 与 `/ui-assets`，保留流式响应，避免缓冲整段 SSE。

## 7. 维护地图

从根目录执行；三个系统共用相同 Python 脚本，工具只使用标准库，无需 npm、数据库、模型或 key：

```sh
python scripts/check_repo_map.py
python scripts/check_repo_map.py --json
git diff --check
```

JSON 实时解析 API 注册与处理函数，只输出相对路径，不保存过期索引。修改地图后通过检查再交付。
校验器只支持当前显式 APIRouter/装饰器注册模式；已知不支持的命令式 add_api_route/add_route、嵌套路由及动态路径会报错。其他注册机制改写也需人工复核并同步扩展工具，不能用静态索引替代运行时 OpenAPI。

若 Python 在脚本运行前就报 `No module named encodings`，先检查 `PYTHONHOME`/`PYTHONPATH` 是否指向其他 Python 版本。可临时用 `python -E -S scripts/check_repo_map.py` 排除环境变量与 site-packages 干扰；这只适合标准库地图工具，不代替业务虚拟环境。不要直接修改全局 Python 配置来掩盖问题。
