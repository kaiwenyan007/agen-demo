# Agent Demo

Python AI Agent 演示项目：**多轮对话、工具调用、RAG 知识库、Streamlit Web UI**，支持本机个人 md 知识库与按用户隔离。

## 快速开始

### Web UI（推荐）

```powershell
cd agent-demo
pip install -r requirements.txt
py -m streamlit run web/app.py
```

或使用 `run_web.ps1`。浏览器打开 `http://localhost:8501`。

流程：**注册 → 登录 → API CONFIG →（可选）KNOWLEDGE 配置本机 md → CHAT**。

### CLI 模式

```powershell
copy .env.example .env
py main.py
```

## 功能一览

### 对话与 Agent

| 能力 | 说明 |
|------|------|
| 多轮对话 | Web + CLI，SQLite 持久化，多会话 |
| 双模式 | LangChain（默认）/ ReAct（`USE_LANGCHAIN=0`） |
| 流式回复 | Web 逐字输出 +「正在调用：xxx」状态 |
| 启动预热 | 后台加载 Agent/Embedding，终端结构化日志 |

### 工具

| 工具 | 说明 |
|------|------|
| 时间 | 含中文星期 |
| 计算 | 四则运算 |
| 文件 | 读/列项目内文件 |
| 知识库 | RAG（公共 + 个人 md） |
| 天气 | 中国城市今日天气（Open-Meteo） |

### RAG 与知识库

| 能力 | 说明 |
|------|------|
| 公共库 | `knowledge/` |
| 个人库 | KNOWLEDGE 页配置本机路径（含文件夹选择器） |
| 用户隔离 | `.chroma/users/{user_id}/` |
| 索引 | 扫描 md、重建索引 |

### Web 用户体系

| 能力 | 说明 |
|------|------|
| 注册登录 | bcrypt，按用户隔离 |
| 记住登录 | 本机文件 + 浏览器密码管理器 |
| API 配置 | 每人 Key / URL / Model |
| 统计 | Token、RAG 命中率、Chroma 缓存 |
| 界面 | 暗色黑客风，响应式 |

### CLI 命令

| 输入 | 说明 |
|------|------|
| `quit` / `q` | 退出 |
| `/clear` | 清空历史 |
| `/reindex` | 重建公共知识库索引 |

## 环境变量

见 `.env.example`：`OPENAI_API_KEY`、`USE_LANGCHAIN`、`USE_LOCAL_EMBEDDING` 等。Web 模式 API 以用户 **API CONFIG** 为准。

## 项目结构

```
agent-demo/
├── main.py
├── web/                    # Streamlit UI
├── agent/                  # Agent、RAG、工具、启动预热
├── db/                     # SQLite
├── knowledge/              # 公共 md 知识库
├── data/                   # app.db（gitignore）
├── .chroma/                # 向量索引（gitignore）
└── doc/                    # 文档
```

## 文档

| 文档 | 内容 |
|------|------|
| [extensions-v1.md](doc/extensions-v1.md) | 用户体系 + Web 初版 |
| [extensions-v2.md](doc/extensions-v2.md) | 个人知识库、天气、流式、统计 |
| [demo-script.md](doc/demo-script.md) | 演示脚本 |
| [learning-roadmap.md](doc/learning-roadmap.md) | 学习路线 |

## 技术栈

Python 3.13 · Streamlit · LangChain · Chroma · SQLite · Open-Meteo · 本地 Embedding（bge-small-zh）
