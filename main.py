import sys

from rich.console import Console
from rich.markdown import Markdown
from agent.memory import ConversationMemory
from agent.llm import chat_with_tools

console = Console()


def run_chat() -> None:
    memory = ConversationMemory(
        system_prompt=(
            "你是一个能使用工具的 AI 助手。"
            "仅在用户明确询问当前时间或日期时调用 get_current_time；"
            "仅在用户需要做数学计算时调用 calculate；"
            "其他问题直接回答。请用中文回答。"
        ),
    )
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
        reply = chat_with_tools(memory)
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run_chat()
