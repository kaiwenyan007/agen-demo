import os
from collections.abc import Iterator

from openai import OpenAI
from dotenv import load_dotenv

from agent.memory import ConversationMemory

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")


def chat(user_message: str, system_prompt: str = "你是一个有帮助的 AI 助手，请用中文回答。") -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
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
