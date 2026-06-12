"""
Agent Demo 主入口 —— 启动交互式聊天，支持 RAG 知识库问答。

启动时会预热向量库（首次较慢，之后读 .chroma/ 缓存）。
聊天中可用 /reindex 重建知识库索引（修改 knowledge/ 文档后使用）。
"""

import os
import sys

from rich.console import Console
from rich.markdown import Markdown

console = Console()
# USE_LANGCHAIN=1（默认）走 LangChain Agent + RAG；=0 走手写 ReAct Agent（无 RAG）
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "1") == "1"


def run_chat() -> None:
    chat_history: list = []

    if USE_LANGCHAIN:
        from agent.langchain_agent import run_agent
        from agent.rag import build_vectorstore

        # 预热：首次启动会从 knowledge/ 建索引并写入 .chroma/，后续启动直接加载
        console.print("[dim]正在加载知识库...[/]")
        build_vectorstore()
        console.print("[dim]知识库就绪[/]\n")

        mode = "LangChain Agent + RAG"
        invoke = lambda text: run_agent(text, chat_history=chat_history, verbose=True)
    else:
        from agent.react_agent import ReactAgent

        react_agent = ReactAgent()
        mode = "手写 ReAct Agent"
        invoke = lambda text: react_agent.run(text, verbose=True)

        def clear_history() -> None:
            react_agent.memory.clear()

    console.print(
        f"[bold green]Agent Demo 聊天[/] [dim]({mode})[/]\n"
        "quit 退出 | /clear 清空历史 | /reindex 重建知识库索引\n"
    )

    while True:
        user_input = console.input("[bold cyan]你> [/]")
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if user_input.strip() == "/clear":
            if USE_LANGCHAIN:
                chat_history.clear()
            else:
                clear_history()
            console.print("[yellow]对话历史已清空[/]\n")
            continue
        if user_input.strip() == "/reindex":
            if USE_LANGCHAIN:
                from agent.rag import build_vectorstore

                # force_rebuild=True：删除 .chroma/ 并重新从 knowledge/ 全量索引
                build_vectorstore(force_rebuild=True)
                console.print("[yellow]知识库索引已重建[/]\n")
            else:
                console.print("[yellow]RAG 仅在 LangChain 模式下可用（USE_LANGCHAIN=1）[/]\n")
            continue

        reply = invoke(user_input)
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_chat()
