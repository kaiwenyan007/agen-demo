# 团队 Demo 演示脚本（约 5 分钟）

## 启动

```powershell
cd agent-demo
.\.venv\Scripts\Activate.ps1
py .\main.py
```

等待出现 `知识库就绪` 后开始演示。

---

## 1. 开场（30 秒）

> 「这是我们一周从零搭建的 Python AI Agent Demo。它能聊天、自主调用工具、还能查项目知识库回答问题。」

可简要展示项目结构：`agent/`、`knowledge/`、`doc/iterations/`。

---

## 2. 基础对话（30 秒）

```
你> 你好，请用三句话介绍一下你自己
```

展示：流畅中文回复、多轮对话能力。

---

## 3. 工具调用（1 分钟）

```
你> 现在几点了？
```

展示：终端 `verbose` 日志中调用 `get_current_time`。

```
你> 123 乘以 456 等于多少？
```

展示：调用 `calculate_tool`。

```
你> knowledge 目录下有哪些文件？
```

展示：调用 `list_files`。

---

## 4. RAG 知识库问答（1.5 分钟）

```
你> 什么是 ReAct？
```

展示：调用 `query_knowledge_base`，基于 `knowledge/agent-faq.md` 回答。

```
你> RAG 和直接读文件有什么区别？
```

展示：检索增强 vs 全文件读取的差异。

```
你> 这个项目有哪些功能？
```

展示：跨文档知识检索。

---

## 5. 多步推理（1 分钟）

```
你> 读一下 knowledge/project-intro.md，用三句话总结
```

展示：Agent 自主决定先 `read_file` 再总结。

---

## 6. 收尾（30 秒）

可补充说明：

- **7 天迭代路线**：对话 → 工具 → ReAct → LangChain → RAG
- **双模式切换**：`USE_LANGCHAIN=0` 可对比手写 ReAct
- **后续扩展**：Web UI（Streamlit）、MCP 工具、多 Agent 协作

```
你> quit
```

---

## 备用问题（防冷场）

| 问题 | 预期行为 |
|------|----------|
| 今天星期几？ | 调时间工具 |
| 100 除以 4 等于多少？ | 调计算工具 |
| /reindex | 重建知识库，无报错 |
| /clear | 清空对话历史 |
