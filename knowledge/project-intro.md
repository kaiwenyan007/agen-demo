# Agent Demo 项目介绍

这是一个 Python AI Agent 演示项目：从一周 CLI 学习迭代，扩展到带用户体系的 **Streamlit Web UI** 本机应用。

## 核心能力

### 对话与 Agent

- 多轮对话（Web + CLI），SQLite 持久化
- **LangChain Agent**（默认）与**手写 ReAct**（`USE_LANGCHAIN=0`）双模式
- Web 聊天：流式回复、工具调用阶段提示、启动预热

### 工具调用

| 工具 | 能力 |
|------|------|
| 时间 | 日期、时刻、**中文星期** |
| 计算 | 加减乘除 |
| 文件 | 读取 / 列出项目内文件 |
| 知识库 | RAG 语义检索 |
| 天气 | **中国城市**今日天气（需用户提供城市名） |

### RAG 知识库

- **公共库**：项目 `knowledge/` 目录
- **个人库**：Web KNOWLEDGE 页配置的本机 md 文件夹（含 C 盘路径）
- 向量库按用户隔离：`.chroma/users/{user_id}/`

### Web 用户体系

- 注册 / 登录，每人独立 API 与 Token 统计
- 可记住本机账号密码
- RAG / Chroma 缓存命中率统计

## 文档

详见项目 `README.md` 与 `doc/extensions-v2.md`。
