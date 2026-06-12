"""
LangChain Agent 模块 —— 把 LLM 和一组工具（Tool）组合成能「思考 + 行动」的助手。

工具列表见 TOOLS；其中 query_knowledge_base 负责 RAG 检索，
Agent 遇到概念/FAQ 类问题时会自动调用它，而不是直接编造答案。
"""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from agent.rag import search_knowledge
from agent.tools.calculator_tool import calculate

load_dotenv()

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
    """
    从项目知识库检索与问题相关的文档片段。
    用户问项目功能、概念、FAQ、ReAct、RAG 时优先使用。

    @tool 装饰器把这个函数注册为 Agent 可调用的工具；
    函数 docstring 会告诉 LLM「什么时候该用这个工具」。
    底层调用 agent/rag.py 的 search_knowledge()，在 Chroma 向量库中做语义检索。
    """
    return search_knowledge(question)


# Agent 可用的全部工具；LLM 会根据问题自动选择调用哪一个
TOOLS = [get_current_time, calculate_tool, read_file, list_files, query_knowledge_base]

# 单例：AgentExecutor 创建开销较大，进程内只建一次
_executor: AgentExecutor | None = None


def build_agent_executor(verbose: bool = True) -> AgentExecutor:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
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


def get_executor(verbose: bool = True) -> AgentExecutor:
    global _executor
    if _executor is None:
        _executor = build_agent_executor(verbose=verbose)
    return _executor


def run_agent(user_input: str, chat_history: list | None = None, verbose: bool = True) -> str:
    executor = get_executor(verbose=verbose)
    result = executor.invoke({
        "input": user_input,
        "chat_history": chat_history or [],
    })
    return result["output"]
