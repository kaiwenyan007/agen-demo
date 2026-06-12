from dataclasses import dataclass, field

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


class TokenUsageCallbackHandler(BaseCallbackHandler):
    """累计 Agent 多轮 LLM 调用的 token 消耗。"""

    usage: TokenUsage = field(default_factory=TokenUsage)

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if not response.llm_output:
            return
        token_usage = response.llm_output.get("token_usage")
        if not token_usage:
            return
        prompt = token_usage.get("prompt_tokens", 0) or 0
        completion = token_usage.get("completion_tokens", 0) or 0
        self.usage.add(prompt, completion)
