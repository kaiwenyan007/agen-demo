"""
Agent Demo CLI 入口（保留命令行模式，使用 .env 全局配置）。
Web UI 请使用：py -m streamlit run web/app.py
"""

import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

from agent.startup_bootstrap import configure_startup_logging, run_startup_bootstrap

configure_startup_logging()

console = Console()
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "1") == "1"
_rag_ready = False


def _ensure_rag(console: Console, *, force: bool = False) -> None:
    """首次需要 RAG 时再加载，并显示趣味等待动画。"""
    global _rag_ready
    from agent.rag import build_vectorstore
    from agent.startup_splash import run_with_cli_splash

    if _rag_ready and not force:
        return

    def _load():
        build_vectorstore(force_rebuild=force)

    run_with_cli_splash(_load, console=console)
    _rag_ready = True
    if force:
        console.print("[yellow]知识库索引已重建[/]\n")
    else:
        console.print("[dim green]知识库就绪[/]\n")


def run_chat() -> None:
    if USE_LANGCHAIN:
        from agent.langchain_agent import run_agent
        from db.api_config import UserApiConfig

        config = UserApiConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
        )

        chat_history: list = []
        mode = "LangChain Agent + RAG (CLI)"

        def invoke(text: str) -> str:
            global _rag_ready
            if not _rag_ready:
                _ensure_rag(console)
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
        "[dim]知识库将在首次提问或 /reindex 时加载[/]\n"
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
                _ensure_rag(console, force=True)
            else:
                console.print("[yellow]RAG 仅在 LangChain 模式下可用[/]\n")
            continue

        reply = invoke(user_input)
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_startup_bootstrap()
    if not result.ok:
        console.print(f"[red]启动预热失败: {result.error}[/]")
    run_chat()
