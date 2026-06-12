"""
Agent Demo CLI 入口（保留命令行模式，使用 .env 全局配置）。
Web UI 请使用：streamlit run web/app.py
"""

import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

console = Console()
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "1") == "1"


def run_chat() -> None:
    if USE_LANGCHAIN:
        from agent.langchain_agent import run_agent
        from agent.rag import build_vectorstore
        from db.api_config import UserApiConfig
        config = UserApiConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
        )

        console.print("[dim]正在加载知识库...[/]")
        build_vectorstore()
        console.print("[dim]知识库就绪[/]\n")

        chat_history: list = []
        mode = "LangChain Agent + RAG (CLI)"

        def invoke(text: str) -> str:
            reply, usage = run_agent(text, config, chat_history=chat_history, verbose=True)
            chat_history.append(("human", text))
            chat_history.append(("ai", reply))
            return reply

        def clear_history() -> None:
            chat_history.clear()
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
            clear_history()
            console.print("[yellow]对话历史已清空[/]\n")
            continue
        if user_input.strip() == "/reindex":
            if USE_LANGCHAIN:
                from agent.rag import build_vectorstore

                build_vectorstore(force_rebuild=True)
                console.print("[yellow]知识库索引已重建[/]\n")
            else:
                console.print("[yellow]RAG 仅在 LangChain 模式下可用[/]\n")
            continue

        reply = invoke(user_input)
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_chat()
