"""
LangChain Agent 模块 —— 支持用户级 API 配置与 Token 统计。
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Generator

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
from agent.tools.datetime_tool import get_current_time as _format_current_time
from agent.tools.weather_tool import get_today_weather as _fetch_today_weather
from db.api_config import UserApiConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@tool
def get_current_time() -> str:
    """获取当前日期、时间和星期几。用户问几点、今天几号、星期几时必须调用，并原样引用工具返回的星期。"""
    return _format_current_time()


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
    """列出项目内目录下的文件名。path 为相对项目根的路径，如 knowledge。不能用于用户本机个人知识库路径。"""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return "错误：不允许访问项目外路径"
    if not target.is_dir():
        return f"错误：目录不存在 {path}"
    return ", ".join(f.name for f in target.iterdir()) or "（空目录）"


@tool
def list_knowledge_files() -> str:
    """列出当前用户在 KNOWLEDGE 页配置的知识库目录中的文档。用户问知识库有哪些文件时必须调用。"""
    from agent.rag import describe_knowledge_files
    from agent.rag_context import get_rag_context

    ctx = get_rag_context()
    user_id = ctx.user_id if ctx else None
    return describe_knowledge_files(user_id)


@tool
def query_knowledge_base(question: str) -> str:
    """从用户配置的知识库检索文档片段。问笔记、文档内容时优先使用。"""
    return search_knowledge(question)


@tool
def get_today_weather(city: str) -> str:
    """查询中国城市今日天气。用户问天气时必须传入 city（如北京、上海）；未提供城市时请先询问用户。"""
    return _fetch_today_weather(city)


TOOLS = [
    get_current_time,
    calculate_tool,
    read_file,
    list_files,
    list_knowledge_files,
    query_knowledge_base,
    get_today_weather,
]

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
            "回答日期、星期几时，必须原样使用 get_current_time 工具返回的星期，禁止自行推算。"
            "用户问天气时，必须调用 get_today_weather 并传入中国城市名；若用户未说明城市，请先追问要查哪座城市，禁止编造天气。"
            "用户问个人知识库、笔记目录有哪些文件时，必须调用 list_knowledge_files，禁止用 list_files(path='knowledge') 代替。"
            "回答文档内容检索时，优先调用 query_knowledge_base 检索用户配置的知识库，不要编造结果。"
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
        output = result.get("output", "")
        return str(output), handler.usage
    finally:
        reset_rag_context(ctx_token)


def stream_agent_reply(
        user_input: str,
        config: UserApiConfig,
        chat_history: list | None = None,
        verbose: bool = False,
        user_id: int | None = None,
        conversation_id: int | None = None,
) -> tuple[Iterator[str], TokenUsageCallbackHandler]:
    """流式运行 Agent，yield 回复片段；返回 handler 供统计 token。"""
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
) -> tuple[Generator[tuple[str, str], None, None], TokenUsageCallbackHandler]:
    """流式 yield 回复正文片段，供 Web UI 展示。"""
    handler = TokenUsageCallbackHandler()
    last_output = ""

    def _gen() -> Generator[tuple[str, str], None, None]:
        nonlocal last_output
        executor = build_agent_executor(config, verbose=verbose)

        invoke_config: RunnableConfig = {"callbacks": [handler]}
        ctx_token: RagRequestContext | None = set_rag_context(user_id, conversation_id)
        try:
            for chunk in executor.stream(
                    {"input": user_input, "chat_history": chat_history or []},
                    config=invoke_config,
            ):
                if not isinstance(chunk, dict):
                    continue
                output = chunk.get("output")
                if not output:
                    continue
                text = str(output)
                if text.startswith(last_output):
                    delta = text[len(last_output):]
                    if delta:
                        yield "content", delta
                    last_output = text
                else:
                    yield "content", text
                    last_output = text
        finally:
            reset_rag_context(ctx_token)

    return _gen(), handler
