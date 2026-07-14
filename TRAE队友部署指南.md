# TRAE 队友部署指南

你是一个运行在队友电脑上的 TRAE AI 助手。你收到的代码仓库是一个完整的项目，包含 Python 后端和 Vue 前端。请按照以下步骤帮队友完成环境搭建并启动项目。

---

## 项目概述

此项目是一个"数字人智能导览系统"（A5 Scenic Guide AI），用于景区智能导览。

- 后端：Python FastAPI，运行在 `http://localhost:8000`
- 前端：Vue 3 + Vite，运行在 `http://localhost:5173`
- 数据库：SQLite（自动创建）
- 向量库：ChromaDB（本地持久化）
- AI 模型：BGE Embedding + BGE Reranker（本地运行，首次自动下载）
- LLM：DeepSeek API（需要 API Key）
- TTS：阿里百炼 DashScope CosyVoice（需要 API Key）
- ASR：阿里百炼 DashScope Paraformer（需要 API Key，可选）

---

## 第一步：确认电脑基础环境

在开始之前，先检查队友电脑上是否已安装以下工具。按顺序检查，缺什么装什么。

### 1.1 检查 Git

```bash
git --version
```

如果未安装，去 https://git-scm.com 下载安装。

### 1.2 检查 Python（需要 3.10 或更高版本）

```bash
python --version
```

如果未安装或版本太低，去 https://www.python.org/downloads/ 下载 Python 3.10+。安装时勾选 "Add Python to PATH"。

### 1.3 检查 Node.js（需要 18 或更高版本）

```bash
node --version
npm --version
```

如果未安装，去 https://nodejs.org 下载 LTS 版本（18.x 或 20.x）。

---

## 第二步：克隆仓库并进入项目目录

```bash
git clone https://github.com/[队友的GitHub用户名]/[仓库名].git
cd [仓库名]
```

> 注意：`[仓库名]` 是 GitHub 上的仓库名称，队友需要从 GitHub 仓库页面获取实际的克隆地址。如果不知道仓库地址，请先询问队友。

---

## 第三步：搭建后端（Python / FastAPI）

### 3.1 进入后端目录

```bash
cd backend
```

### 3.2 创建 Python 虚拟环境

```bash
python -m venv .venv
```

### 3.3 激活虚拟环境

Windows PowerShell：
```bash
.venv\Scripts\Activate.ps1
```

如果遇到执行策略问题，先执行：
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

macOS / Linux：
```bash
source .venv/bin/activate
```

### 3.4 安装 Python 依赖

```bash
pip install -r requirements.txt
```

> 注意：`requirements.txt` 中指定了 CPU 版本的 PyTorch。安装过程可能较慢，因为需要下载 torch（~200MB）、sentence-transformers 等大型包。

### 3.5 配置环境变量（.env 文件）

项目根目录有一个 `.env.example` 模板文件。复制它创建 `.env`：

```bash
copy .env.example .env
```

现在打开 `.env` 文件，阅读其中的配置项。**最重要的配置项如下：**

| 配置项 | 说明 | 是否必须 |
|--------|------|----------|
| `LLM_API_KEY` | DeepSeek API Key，用于大模型问答 | **必须** |
| `LLM_BASE_URL` | DeepSeek API 地址，默认 https://api.deepseek.com | 保持默认 |
| `LLM_MODEL` | 模型名称，默认 deepseek-v4-pro | 保持默认 |
| `TTS_API_KEY` | 阿里百炼 DashScope API Key，用于文字转语音 | **必须** |
| `TTS_PROVIDER` | TTS 提供商，默认 bailian | 保持默认 |
| `ASR_API_KEY` | 阿里百炼 DashScope API Key，用于语音识别 | 可选（默认 stub 模式不启用） |
| `VISION_API_KEY` | 阿里百炼 Qwen API Key，用于图片识别 | 可选（默认 stub 模式不启用） |

**请向队友索要以下 API Key：**
1. DeepSeek API Key → 填入 `LLM_API_KEY`
2. 阿里百炼 DashScope API Key → 填入 `TTS_API_KEY`（和 `ASR_API_KEY` 如需语音输入）

如果队友暂时没有 API Key，可以让队友去以下地址申请：
- DeepSeek：https://platform.deepseek.com
- 阿里百炼：https://bailian.console.aliyun.com

### 3.6 验证后端依赖安装成功

在 `backend` 目录下运行：

```bash
python -c "import fastapi; import uvicorn; import sqlalchemy; print('Backend deps OK')"
```

如果输出了 "Backend deps OK"，说明依赖安装成功。

### 3.7 启动后端

```bash
python main.py
```

或者：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端启动后会在 `http://localhost:8000` 运行。

**首次启动注意事项：**
- 服务器会自动创建 SQLite 数据库文件（`app.db`）
- 首次启动会自动下载 Embedding 模型 `BAAI/bge-small-zh-v1.5`（约 500MB）
- 首次启动会自动下载 Reranker 模型 `BAAI/bge-reranker-base`（约 1GB）
- 模型会缓存到 `backend/../.cache/huggingface/` 目录
- 模型下载需要联网，可能需要几分钟时间
- 如果看到模型下载进度条，请耐心等待

验证后端是否正常启动：
```bash
curl http://localhost:8000/health
```

应该返回类似这样的响应：
```json
{"status":"ok","service":"A5 Scenic Guide AI"}
```

---

## 第四步：搭建前端（Vue 3 / Vite）

### 4.1 打开新的终端窗口，进入前端目录

保持后端在运行，新开一个终端窗口：

