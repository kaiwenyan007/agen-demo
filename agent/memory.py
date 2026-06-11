from dataclasses import dataclass, field

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)


@dataclass
class ConversationMemory:
    system_prompt: str = "你是一个有帮助的 AI 助手，请用中文回答。"
    messages: list[ChatCompletionMessageParam] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        msg: ChatCompletionUserMessageParam = {"role": "user", "content": content}
        self.messages.append(msg)

    def add_assistant(self, content: str) -> None:
        msg: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": content}
        self.messages.append(msg)

    def to_api_messages(self) -> list[ChatCompletionMessageParam]:
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": self.system_prompt,
        }
        return [system_message] + self.messages

    def clear(self) -> None:
        self.messages.clear()
