"""
LangChain Agent 模块 —— 支持用户级 API 配置与 Token 统计。
"""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.rag import search_knowledge
from agent.rag_context import RagRequestContext, reset_rag_context, set_rag_context
from agent.token_callback import TokenUsageCallbackHandler
from agent.tools.calculator_tool import calculate
from db.api_config import UserApiConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@tool
def get_current_time() -> str:
    """获取当前日期和时间。用户问几点、今天几号时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculate_tool(operation: str, a: float, b: float) -> str:
    """执行基础四则运算（加减乘除）。operation 为 add/subtract/multiply/divide。"""
    return calculate(operation, a, b)


@tool
def read_file(path: str) -> str:
    """读取项目内文本文件。path 为相对项目根的路径，如 knowledge/project-intro.md。"""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return "错误：不允许访问项目外路径"
    if not target.exists():
        return f"错误：文件不存在 {path}"
    return target.read_text(encoding="utf-8")[:8000]


@tool
def list_files(path: str = ".") -> str:
    """列出目录下的文件名。path 为相对路径，如 knowledge。"""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return "错误：不允许访问项目外路径"
    if not target.is_dir():
        return f"错误：目录不存在 {path}"
    return ", ".join(f.name for f in target.iterdir()) or "（空目录）"


@tool
def query_knowledge_base(question: str) -> str:
    """从项目知识库检索与问题相关的文档片段。用户问项目功能、概念、FAQ、ReAct、RAG 时优先使用。"""
    return search_knowledge(question)


TOOLS = [get_current_time, calculate_tool, read_file, list_files, query_knowledge_base]

_TOOL_LABELS = {
    "get_current_time": "获取时间",
    "calculate_tool": "计算器",
    "read_file": "读文件",
    "list_files": "列目录",
    "query_knowledge_base": "知识库检索",
}


def build_agent_executor(config: UserApiConfig, verbose: bool = False) -> AgentExecutor:
    llm = ChatOpenAI(
        model=config.model,
        api_key=SecretStr(config.api_key) if config.api_key else None,
        base_url=config.base_url,
        temperature=0,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个能使用工具的 AI 助手。"
            "需要查时间、做计算、读文件、列目录时请调用相应工具。"
            "回答项目概念、FAQ、功能介绍时，优先调用 query_knowledge_base 检索知识库，不要编造结果。"
            "请用中文回答。",
        ),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=verbose, max_iterations=8)


def run_agent(
        user_input: str,
        config: UserApiConfig,
        chat_history: list | None = None,
        verbose: bool = False,
        user_id: int | None = None,
        conversation_id: int | None = None,
) -> tuple[str, Any] | None:
    """运行 Agent，返回 (回复文本, token 用量)。"""
    handler = TokenUsageCallbackHandler()
    executor = build_agent_executor(config, verbose=verbose)
    invoke_config: RunnableConfig = {"callbacks": [handler]}
    ctx_token: RagRequestContext | None = set_rag_context(user_id, conversation_id)
    try:
        result: dict[str, Any] = executor.invoke(
            {"input": user_input, "chat_history": chat_history or []},
            config=invoke_config,
        )
    finally:
        reset_rag_context(ctx_token)

    output = result.get("output", "")
    return str(output), handler.usage


def stream_agent_reply(
        user_input: str,
        config: UserApiConfig,
        chat_history: list | None = None,
        verbose: bool = False,
        user_id: int | None = None,
        conversation_id: int | None = None,
) -> tuple[Iterator[str], TokenUsageCallbackHandler]:
    """流式运行 Agent，yield 工具状态与最终回复片段；返回 handler 供统计 token。"""
    events, handler = iter_agent_reply_events(
        user_input,
        config,
        chat_history=chat_history,
        verbose=verbose,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    def _text_only() -> Iterator[str]:
        for kind, text in events:
            if kind == "content":
                yield text

    return _text_only(), handler


def iter_agent_reply_events(
        user_input: str,
        config: UserApiConfig,
        chat_history: list | None = None,
        verbose: bool = False,
        user_id: int | None = None,
        conversation_id: int | None = None,
) -> tuple[Iterator[tuple[Literal["status", "content"], str]], TokenUsageCallbackHandler]:
    """按阶段 yield 状态提示与回复正文，供 Web UI 分区域展示。"""
    handler = TokenUsageCallbackHandler()
    seen_tools: set[str] = set()
    last_output = ""

    def _gen() -> Iterator[tuple[Literal["status", "content"], str]]:
        nonlocal last_output
        yield ("status", "正在初始化 Agent 引擎…")
        executor = build_agent_executor(config, verbose=verbose)
        yield ("status", f"正在连接模型 `{config.model}` …")
        yield ("status", "正在理解问题并规划步骤…")

        invoke_config: RunnableConfig = {"callbacks": [handler]}
        ctx_token: RagRequestContext | None = set_rag_context(user_id, conversation_id)
        try:
            for chunk in executor.stream(
                    {"input": user_input, "chat_history": chat_history or []},
                    config=invoke_config,
            ):
                if not isinstance(chunk, dict):
                    continue
                actions = chunk.get("actions") or []
                for action in actions:
                    tool = getattr(action, "tool", None) or "tool"
                    if tool in seen_tools:
                        continue
                    seen_tools.add(tool)
                    label = _TOOL_LABELS.get(tool, tool)
                    yield ("status", f"正在调用：{label}")
                output = chunk.get("output")
                if not output:
                    continue
                text = str(output)
                if not last_output and text:
                    yield ("status", "正在生成回复…")
                if text.startswith(last_output):
                    delta = text[len(last_output):]
                    if delta:
                        yield ("content", delta)
                    last_output = text
                else:
                    yield ("content", text)
                    last_output = text
        finally:
            reset_rag_context(ctx_token)

    return _gen(), handler
