import json

from rich.console import Console
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)

from agent.llm import _function_tool_call_to_param, client, MODEL
from agent.memory import ConversationMemory
from agent.tools.registry import TOOL_SCHEMAS, execute_tool

console = Console()


class ReactAgent:
    def __init__(self, memory: ConversationMemory | None = None):
        self.memory = memory or ConversationMemory(
            system_prompt=(
                "你是一个能使用工具的 AI 助手。"
                "需要查时间、做计算、读文件、列目录时，请调用相应工具，不要编造结果。"
                "回答项目相关问题时，应先读取或检索项目文件。"
                "请用中文回答。"
            )
        )

    def run(self, user_input: str, max_rounds: int = 8, verbose: bool = True) -> str:
        self.memory.add_user(user_input)

        for _ in range(max_rounds):
            response = client.chat.completions.create(
                model=MODEL,
                messages=self.memory.to_api_messages(),
                tools=TOOL_SCHEMAS,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                reply = msg.content or ""
                self.memory.add_assistant(reply)
                return reply

            tool_calls = [
                _function_tool_call_to_param(tc)
                for tc in msg.tool_calls
                if isinstance(tc, ChatCompletionMessageFunctionToolCall)
            ]
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": tool_calls,
            }
            self.memory.messages.append(assistant_msg)

            for tc in msg.tool_calls:
                if not isinstance(tc, ChatCompletionMessageFunctionToolCall):
                    continue
                args = json.loads(tc.function.arguments or "{}")
                if verbose:
                    console.print(f"[dim]🔧 工具: {tc.function.name}({args})[/]")
                try:
                    result = execute_tool(tc.function.name, args)
                except Exception as e:
                    result = f"工具执行失败: {e}"
                if verbose:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    console.print(f"[dim]📋 结果: {preview}[/]")

                tool_msg: ChatCompletionToolMessageParam = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
                self.memory.messages.append(tool_msg)

        return "达到最大工具调用轮次，请简化问题后重试。"
