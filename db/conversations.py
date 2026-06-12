from db.database import get_db


def create_conversation(user_id: int, title: str = "新对话") -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )
        conn.commit()
        return cur.lastrowid


def list_conversations(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(user_id: int, conversation_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def update_conversation_title(user_id: int, conversation_id: int, title: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE conversations SET title = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (title, conversation_id, user_id),
        )
        conn.commit()


def touch_conversation(conversation_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()


def delete_conversation(user_id: int, conversation_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def add_message(conversation_id: int, role: str, content: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()
        return cur.lastrowid


def get_messages(conversation_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def messages_to_chat_history(messages: list[dict]) -> list:
    """将 DB 消息转为 LangChain chat_history 格式（不含当前轮）。"""
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(("human", msg["content"]))
        elif msg["role"] == "assistant":
            history.append(("ai", msg["content"]))
    return history
