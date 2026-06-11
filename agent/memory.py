from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    system_prompt: str = "你是一个有帮助的 AI 助手，请用中文回答。"
    messages: list[dict] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def to_api_messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.messages

    def clear(self) -> None:
        self.messages.clear()
