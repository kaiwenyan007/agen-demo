import sys

from rich.console import Console
from agent.memory import ConversationMemory
from agent.llm import chat_stream

console = Console()


def run_chat() -> None:
    memory = ConversationMemory()
    console.print("[bold green]Agent Demo 聊天[/]（输入 quit 退出，/clear 清空历史）\n")

    while True:
        user_input = console.input("[bold cyan]你> [/]")
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if user_input.strip() == "/clear":
            memory.clear()
            console.print("[yellow]对话历史已清空[/]\n")
            continue

        memory.add_user(user_input)
        console.print("[bold magenta]AI> [/]", end="")
        for token in chat_stream(memory):
            console.print(token, end="")
        console.print("\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_chat()
