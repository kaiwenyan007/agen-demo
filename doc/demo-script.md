# 团队 Demo 演示脚本（约 5 分钟）

## 启动（Web 推荐）

```powershell
cd agent-demo
pip install -r requirements.txt
py -m streamlit run web/app.py
```

浏览器 `http://localhost:8501` → 注册/登录 → **API CONFIG** 填 Key → **CHAT**。

CLI 备选：`py main.py`（见文末）。

---

## 1. 开场（30 秒）

> 「这是 Python AI Agent Demo：多轮对话、自主调工具、RAG 查知识库，还有 Web 用户体系和个人 md 知识库。」

可展示：侧边栏 CHAT / API CONFIG / KNOWLEDGE / TOKEN STATS。

---

## 2. 基础对话（30 秒）

```
今天星期几？现在几点？
```

展示：调用时间工具，星期正确。

---

## 3. 工具调用（1 分钟）

```
上海今天天气怎么样？
```

展示：调用天气工具，返回气温与天气。

```
123 乘以 456 等于多少？
```

展示：计算器工具 + 聊天状态「正在调用：计算器」。

---

## 4. RAG 知识库（1.5 分钟）

```
什么是 ReAct？
```

展示：`query_knowledge_base` 检索 `knowledge/agent-faq.md`。

```
这个项目有哪些功能？
```

展示：FAQ / project-intro 跨文档检索。

**（可选）个人知识库：**

1. 打开 **KNOWLEDGE**，选择本机 md 文件夹 → **REBUILD INDEX**
2. 提问与个人笔记相关的问题

---

## 5. 工程化亮点（1 分钟）

- **TOKEN STATS**：Token 用量、RAG 命中率、Chroma 缓存
- **记住登录**：勾选后下次自动填账号
- 终端启动日志：`agent_demo.startup` 预热完成

---

## 6. 收尾（30 秒）

- 7 天迭代 + 扩展 v1/v2 文档
- 后续：多 Agent、增量索引、服务器部署

---

## CLI 演示补充

```powershell
py main.py
```

| 输入 | 预期 |
|------|------|
| 现在几点？ | 时间工具 |
| 北京天气 | 天气工具 |
| 什么是 RAG？ | 知识库检索 |
| `/reindex` | 重建索引 |
| `/clear` | 清空历史 |

---

## 备用问题

| 问题 | 预期 |
|------|------|
| 100 除以 4 | 计算 |
| knowledge 有哪些文件 | list_files |
| 今天天气（不说城市） | 追问城市名 |
