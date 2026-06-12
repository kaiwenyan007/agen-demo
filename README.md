# Agent Demo

一周学习的 Python AI Agent 演示项目，具备**多轮对话、工具调用、RAG 知识库问答**能力。

## 快速开始

```powershell
cd agent-demo
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env   # 填入 API Key
python main.py
```

## 功能一览

| 能力 | 说明 |
|------|------|
| 多轮对话 | CLI 交互，支持上下文记忆 |
| 工具调用 | 查时间、四则运算、读文件、列目录 |
| RAG 问答 | 基于 `knowledge/` 文档的向量检索问答 |
| 双模式 | LangChain Agent（默认）/ 手写 ReAct 可切换 |

## CLI 命令

| 输入 | 说明 |
|------|------|
| `quit` / `exit` / `q` | 退出 |
| `/clear` | 清空对话历史 |
| `/reindex` | 重建知识库向量索引（修改 `knowledge/` 后使用） |

## 环境变量

复制 `.env.example` 为 `.env`，主要配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | 大模型 API Key | `sk-...` |
| `OPENAI_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 对话模型 | `deepseek-chat` |
| `USE_LANGCHAIN` | `1` LangChain / `0` 手写 ReAct | `1` |
| `USE_LOCAL_EMBEDDING` | 使用本地 Embedding 模型 | `1` |
| `USE_KEYWORD_FALLBACK` | 离线关键词检索（无向量时用） | `0` |
| `LOCAL_EMBEDDING_MODEL_PATH` | 已下载模型本地路径 | `models/BAAI/bge-small-zh-v1___5` |

## 示例对话

```
你> 现在几点了？
AI> 现在是 2026 年 6 月 12 日 ...

你> 123 乘以 456 等于多少？
AI> 56,088

你> 什么是 ReAct？
AI> （从知识库检索后回答）

你> knowledge 目录有哪些文件？
AI> project-intro.md, agent-faq.md
```

## 项目结构

```
agent-demo/
├── main.py                 # CLI 入口
├── agent/
│   ├── llm.py              # LLM 客户端
│   ├── memory.py           # 对话记忆
│   ├── react_agent.py      # 手写 ReAct Agent
│   ├── langchain_agent.py  # LangChain Agent
│   ├── rag.py              # RAG 向量库
│   └── tools/              # 工具定义
├── knowledge/              # RAG 知识库文档
├── doc/                    # 学习文档（7 天迭代笔记）
├── .chroma/                # 向量库缓存（自动生成）
└── models/                 # 本地 Embedding 模型（自动生成）
```

## 团队 Demo

5 分钟演示脚本见 [doc/demo-script.md](doc/demo-script.md)。

## 学习文档

- [一周学习路线图](doc/learning-roadmap.md)
- [版本迭代笔记](doc/iterations/README.md)
- [AI Agent 学习指南](doc/ai-agent-learning-guide.md)

## 技术栈

- Python 3.13
- OpenAI 兼容 API（DeepSeek 等）
- LangChain + LangGraph 生态
- Chroma 向量库
- ModelScope 本地 Embedding（`bge-small-zh-v1.5`）
