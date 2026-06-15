# 一周 Agent Demo 学习计划

> 目标：7 天内从零搭建一个可演示的 Python AI Agent，具备**对话、工具调用、简单 RAG** 能力。  
> 参考：[ai-agent-learning-guide.md](./ai-agent-learning-guide.md)

---

## 最终交付物

| 能力 | 说明 |
|------|------|
| 多轮对话 | 带历史记录的 CLI 聊天 |
| 工具调用 | 查时间、读文件、搜索（至少 2 个） |
| ReAct 循环 | 模型自主决定何时调工具 |
| 框架整合 | LangChain Agent 编排 |
| 简单 RAG | 基于项目内 Markdown 文档问答 |
| 可演示 | 一条命令启动，有示例问题清单 |

---

## 版本迭代路线

```
v0.1 环境 + 首个对话
  ↓
v0.2 流式输出 + 对话记忆
  ↓
v0.3 Function Calling（单工具）
  ↓
v0.4 多工具 + ReAct 循环
  ↓
v0.5 LangChain Agent 重构
  ↓
v0.6 简单 RAG
  ↓
v0.7 打磨 + Demo 脚本
```

每日对应一个版本，详见 [iterations/](./iterations/) 目录。

---

## 每日安排总览

| 天 | 版本 | 主题 | 预计时间 | 文档 |
|----|------|------|----------|------|
| Day 1 | v0.1 | 环境搭建 + 首个 LLM 对话 | 2–3h | [v0.1](./iterations/v0.1-day1-setup-and-first-chat.md) |
| Day 2 | v0.2 | 流式输出 + 对话历史 | 2–3h | [v0.2](./iterations/v0.2-day2-streaming-and-memory.md) |
| Day 3 | v0.3 | Function Calling 单工具 | 2–3h | [v0.3](./iterations/v0.3-day3-function-calling.md) |
| Day 4 | v0.4 | 多工具 + ReAct 循环 | 3–4h | [v0.4](./iterations/v0.4-day4-multi-tool-react.md) |
| Day 5 | v0.5 | LangChain Agent 重构 | 3–4h | [v0.5](./iterations/v0.5-day5-langchain-agent.md) |
| Day 6 | v0.6 | 简单 RAG 知识库问答 | 3–4h | [v0.6](./iterations/v0.6-day6-simple-rag.md) |
| Day 7 | v0.7 | 整合打磨 + Demo 演示 | 2–3h | [v0.7](./iterations/v0.7-day7-polish-and-demo.md) |

---

## 技术选型

| 项目 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | AI 生态最成熟 |
| LLM | OpenAI 兼容 API | DeepSeek / 通义 / OpenAI 均可 |
| 框架 | LangChain + LangGraph（Day 5 起） | 社区大、文档全 |
| 向量库 | Chroma（本地、零配置） | 适合 Demo |
| 界面 | CLI（`rich` 美化） | 最快可演示 |

---

## 目标项目结构（Day 7 完成时）

```
agent-demo/
├── .env                    # API Key（不提交 Git）
├── .env.example
├── requirements.txt
├── README.md
├── main.py                 # 入口：启动 Agent CLI
├── agent/
│   ├── __init__.py
│   ├── llm.py              # LLM 客户端封装
│   ├── tools/              # 工具定义
│   │   ├── datetime_tool.py
│   │   ├── file_reader.py
│   │   └── rag_tool.py
│   ├── memory.py           # 对话历史
│   ├── react_agent.py      # ReAct 循环（v0.4）
│   └── langchain_agent.py  # LangChain 版（v0.5+）
├── knowledge/              # RAG 文档目录
│   └── *.md
└── doc/
    ├── ai-agent-learning-guide.md
    ├── learning-roadmap.md
    └── iterations/         # 每日学习笔记
```

---

## 前置要求

- [ ] 已安装 Python 3.11+
- [ ] 已安装 Git
- [ ] 有一个大模型 API Key（推荐 DeepSeek 或通义，成本低）
- [ ] 会用终端 / PowerShell 基本命令
- [ ] 有 Python 基础（函数、类、字典、列表）

---

## 学习方式

1. **每天只做当天版本**，完成验收清单再进入下一天
2. **跟着文档逐步敲代码**，不要一次复制全部
3. **遇到问题先自己调试**，再问我；把踩坑记进当天 md 的「学习笔记」区
4. **每完成一天**，在 iterations 对应文件底部勾选验收项

---

## 下一步

从 **[Day 1 / v0.1](./iterations/v0.1-day1-setup-and-first-chat.md)** 开始。  
在对话里对我说：**「开始 Day 1」**，我会带你逐步执行。

---

## 扩展阶段（7 天之后，已完成）

一周 CLI 路线完成后，项目继续扩展为**本机 Web 应用**：

| 阶段 | 文档 | 主要内容 |
|------|------|----------|
| 扩展 v1 | [extensions-v1.md](./extensions-v1.md) | 用户注册登录、SQLite 持久化、Streamlit Web UI、每人独立 API 配置 |
| 扩展 v2 | [extensions-v2.md](./extensions-v2.md) | 流式聊天、个人 md 知识库、天气工具、RAG/Token 统计、登录记住、启动预热 |

当前功能总览见项目根目录 [README.md](../README.md)，演示话术见 [demo-script.md](./demo-script.md)。
