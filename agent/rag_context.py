"""RAG 请求上下文（供 search_knowledge 关联到当前用户/对话）。"""

import threading
from dataclasses import dataclass


@dataclass
class RagRequestContext:
    user_id: int | None = None
    conversation_id: int | None = None


_local = threading.local()


def set_rag_context(
    user_id: int | None = None,
    conversation_id: int | None = None,
) -> RagRequestContext | None:
    """设置当前线程的 RAG 上下文，返回旧值供 reset 恢复。"""
    previous = getattr(_local, "ctx", None)
    _local.ctx = RagRequestContext(user_id, conversation_id)
    return previous


def reset_rag_context(token: RagRequestContext | None) -> None:
    _local.ctx = token
    return None


def get_rag_context() -> RagRequestContext | None:
    return getattr(_local, "ctx", None)
