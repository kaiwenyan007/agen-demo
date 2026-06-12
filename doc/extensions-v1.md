# 扩展 v1：用户体系 + Web UI

> 在 7 天 Demo 基础上的第一步工程化扩展。

## 新增能力

| 功能 | 实现 |
|------|------|
| 用户注册/登录 | `db/auth.py` + bcrypt 密码哈希 |
| 数据隔离 | 所有表按 `user_id` 过滤 |
| 用户 API 配置 | `db/api_config.py`，每人独立 Key/URL/Model |
| 模型动态下拉 | `agent/model_fetcher.py` 调用 `/v1/models` |
| Token 成本统计 | `db/token_stats.py` + `agent/token_callback.py` |
| 对话持久化 | SQLite `conversations` + `messages` 表 |
| Web UI | Streamlit `web/app.py` |

## 启动 Web UI

```powershell
cd agent-demo
.\.venv\Scripts\Activate.ps1
pip install streamlit
streamlit run web/app.py
```

浏览器打开 `http://localhost:8501`

## 数据库

- 路径：`data/app.db`（自动创建，已加入 `.gitignore`）
- 表：`users`、`user_api_configs`、`conversations`、`messages`、`token_usage`

## 使用流程

1. 注册账号 → 登录
2. 进入「API 设置」，填入 Key / Base URL，点「刷新模型列表」，选择 Model，保存
3. 回到「聊天」，新建对话开始提问
4. 「Token 统计」查看用量和预估成本

## CLI 仍可用

```powershell
python main.py
```

CLI 模式继续使用 `.env` 全局配置，不依赖用户登录。

---

## 下一步：多 Agent 协作（提示）

当你准备进入多 Agent 阶段，建议按以下路线：

### 1. 角色分工（CrewAI / LangGraph）

```
用户任务
    ↓
[规划 Agent] 拆解任务
    ↓
[研究员 Agent] 调 RAG / 搜索工具
    ↓
[写手 Agent] 生成报告
    ↓
[审稿 Agent] 检查质量
    ↓
输出最终结果
```

### 2. 推荐技术选型

| 方案 | 适合场景 |
|------|----------|
| **LangGraph** | 需要精细控制状态机、循环、人工审批 |
| **CrewAI** | 快速搭建角色化团队，配置驱动 |
| **AutoGen** | 多 Agent 对话式协作 |

### 3. 接入你现有项目的方式

- 在 `agent/` 下新建 `multi_agent/` 目录
- 每个 Agent 复用现有 `TOOLS` 和 `UserApiConfig`
- 用户级数据隔离不变：每个 Agent 的 token 仍记入 `token_usage`
- Web UI 增加「Agent 模式」切换：单 Agent / 多 Agent 团队

### 4. 示例任务

> 「调研 Agent Demo 项目功能，写一份 500 字介绍，并列出 3 个改进建议」

- 研究员：调用 `query_knowledge_base` + `read_file`
- 写手：基于检索结果写稿
- 审稿：检查事实是否与知识库一致

### 5. 建议学习顺序

1. 先读 LangGraph 官方「Plan-and-Execute」示例
2. 把现有 `run_agent` 封装为一个「执行 Agent」节点
3. 加一个「监督 Agent」节点负责拆任务和验收
4. 在 Streamlit 中展示每个 Agent 的中间输出（可观测性）

准备好了可以说 **「开始多 Agent 扩展」**，我会带你逐步实现。
