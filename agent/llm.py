import json
import os
from collections.abc import Iterator

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from dotenv import load_dotenv

from agent.memory import ConversationMemory
from agent.tools.registry import TOOL_SCHEMAS, execute_tool

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")


def _function_tool_call_to_param(
    tc: ChatCompletionMessageFunctionToolCall,
) -> ChatCompletionMessageFunctionToolCallParam:
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        },
    }


def chat(user_message: str, system_prompt: str = "你是一个有帮助的 AI 助手，请用中文回答。") -> str:
    system_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": system_prompt,
    }
    user_message_param: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": user_message,
    }
    messages: list[ChatCompletionMessageParam] = [system_message, user_message_param]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    return response.choices[0].message.content


def chat_with_memory(memory: ConversationMemory) -> str:
    """非流式，返回完整回复并写入 memory。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=memory.to_api_messages(),
    )
    reply = response.choices[0].message.content
    memory.add_assistant(reply)
    return reply


def chat_stream(memory: ConversationMemory) -> Iterator[str]:
    """流式生成，yield 每个 token 片段。"""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=memory.to_api_messages(),
        stream=True,
    )
    full_reply: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_reply.append(delta)
            yield delta
    memory.add_assistant("".join(full_reply))


def chat_with_tools(memory: ConversationMemory, max_rounds: int = 5) -> str:
    """支持工具调用的对话：模型决策 → 执行工具 → 再生成回答。"""
    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=MODEL,
            messages=memory.to_api_messages(),
            tools=TOOL_SCHEMAS,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            reply = msg.content or ""
            memory.add_assistant(reply)
            return reply

        tool_calls: list[ChatCompletionMessageFunctionToolCallParam] = []
        for tc in msg.tool_calls:
            if isinstance(tc, ChatCompletionMessageFunctionToolCall):
                tool_calls.append(_function_tool_call_to_param(tc))
        assistant_msg: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": tool_calls,
        }
        memory.messages.append(assistant_msg)

        for tc in msg.tool_calls:
            if not isinstance(tc, ChatCompletionMessageFunctionToolCall):
                continue
            args = json.loads(tc.function.arguments or "{}")
            result = execute_tool(tc.function.name, args)
            tool_msg: ChatCompletionToolMessageParam = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
            memory.messages.append(tool_msg)

    return "工具调用轮次超限，请重试。"
