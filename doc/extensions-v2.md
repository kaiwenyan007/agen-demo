# 扩展 v2：Web 体验 + 个人知识库 + 工具增强

> 在 [扩展 v1](extensions-v1.md)（用户体系 + Web UI）之上的工程化与体验迭代。

## 新增能力总览

| 模块 | 功能 | 实现位置 |
|------|------|----------|
| **Web UI** | 暗色黑客风主题、响应式布局 | `web/theme.py`、`.streamlit/config.toml` |
| **Web UI** | 聊天流式回复 + 阶段状态提示（预热/工具/生成） | `web/app.py`、`agent/langchain_agent.py` |
| **Web UI** | 发送后立即展示用户消息（pending 两阶段） | `web/app.py` |
| **Web UI** | 注册后静默登录、退出后记住账号密码 | `web/app.py`、`web/auth_remember.py` |
| **Web UI** | 浏览器 `autocomplete` 支持密码管理器 | 登录页 `text_input` |
| **启动** | 进程预热 + 结构化日志 | `agent/startup_bootstrap.py` |
| **RAG** | 用户本机 md 目录（可填 C 盘路径 / 文件夹选择器） | KNOWLEDGE 页、`db/user_knowledge.py` |
| **RAG** | 按用户隔离 Chroma（`.chroma/users/{id}/`） | `agent/rag.py` |
| **RAG** | 可选同时索引项目公共库 `knowledge/` | KNOWLEDGE 页勾选 |
| **RAG** | 扫描 md、重建索引、统计 doc/chunk | KNOWLEDGE 页 + `user_knowledge_configs` 表 |
| **统计** | RAG 检索命中率、Chroma 缓存命中 | `db/rag_stats.py`、TOKEN STATS 页 |
| **工具** | 今日天气（中国城市，Open-Meteo，免 Key） | `agent/tools/weather_tool.py` |
| **工具** | 时间含中文星期（防 LLM 猜错） | `agent/tools/datetime_tool.py` |

## Web 页面

| 侧边栏 | 说明 |
|--------|------|
| **CHAT** | 多轮对话，Agent 流式回复，会话列表 |
| **API CONFIG** | 每人独立 Key / URL / Model，动态拉取模型列表 |
| **KNOWLEDGE** | 本机 md 知识库路径、文件夹选择、重建索引 |
| **TOKEN STATS** | Token 用量、RAG 统计、Chroma 缓存、知识库状态 |

## 工具一览（LangChain / ReAct 共用）

| 工具 | 说明 |
|------|------|
| `get_current_time` | 当前日期时间 + 中文星期 |
| `calculate_tool` | 四则运算 |
| `read_file` / `list_files` | 读取项目内文件 |
| `query_knowledge_base` | RAG 检索（公共库 + 用户本机库） |
| `get_today_weather` | 查询**中国城市**今日天气（须传入城市名） |

## 个人知识库（本机 Streamlit）

适用：**在本机**执行 `py -m streamlit run web/app.py`。

1. 登录 → **KNOWLEDGE**
2. 填写 `C:\Users\xxx\notes` 或点 **选择文件夹**
3. 可选勾选「同时索引项目公共库 knowledge/」
4. **SCAN** → **REBUILD INDEX**
5. 回 **CHAT** 提问

存储：向量索引 `.chroma/users/{user_id}/`，配置在 `data/app.db`。

## 登录记住

- 勾选「记住账号密码」→ `data/.login_remember.json`
- 支持浏览器密码管理器（`autocomplete`）
- 公共电脑请勿勾选

## 启动与日志

```text
INFO [agent_demo.startup] ========== Agent Demo 启动预热 ==========
INFO [agent_demo.startup] [warmup] 全部完成，总耗时 X.XXs
```

## 数据库表（相对 v1 新增）

| 表 | 说明 |
|----|------|
| `user_knowledge_configs` | 知识库路径、是否含公共库、索引统计 |
| `rag_queries` | RAG 检索记录 |
| `chroma_cache_events` | memory_hit / disk_hit / rebuild |

## 下一步（可选）

- 个人库增量索引
- 多 Agent 协作（见 [extensions-v1.md](extensions-v1.md)）
- 服务器部署时改为上传 md 而非本机路径
