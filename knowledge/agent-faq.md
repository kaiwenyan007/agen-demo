# Agent 常见问题

## 什么是 ReAct？

ReAct 是推理（Reasoning）与行动（Acting）结合的 Agent 模式，模型交替进行思考和工具调用，直到完成任务。

## 什么是 RAG？

RAG（检索增强生成）先从知识库检索相关内容，再让 LLM 基于检索结果回答，减少幻觉，适合基于文档的问答场景。

## RAG 和直接读文件有什么区别？

- **读文件**：整份文件塞进上下文，大文件费 token，无法跨文档检索。
- **RAG**：切块向量化，按语义检索相关片段，更精准省 token。

## 这个项目有哪些功能？

### 基础

- 多轮对话（Web + CLI），SQLite 持久化
- 工具：时间、计算、文件、**中国城市天气**、知识库检索
- RAG 向量检索；LangChain / ReAct 双模式

### Web UI

- 注册登录、独立 API 配置、流式聊天
- **KNOWLEDGE**：本机 md 文件夹 + 重建索引
- **TOKEN STATS**：Token、RAG 命中率、Chroma 缓存
- 记住登录、暗色主题

### 知识库来源

1. 公共 `knowledge/`（如本 FAQ）
2. 用户在本机 KNOWLEDGE 页配置的 md 目录

## 问天气要注意什么？

必须提供**中国城市名**。数据来自 Open-Meteo，免 API Key。

## 数据存在哪里？

- 用户与对话：`data/app.db`
- 向量：`.chroma/` 或 `.chroma/users/{id}/`
- 均为本机文件，非远程数据库。
