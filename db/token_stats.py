from db.database import get_db

# 估算单价（元 / 百万 token），可按模型扩展
MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 1.0, "output": 2.0},
    "deepseek-reasoner": {"input": 4.0, "output": 16.0},
    "gpt-4o": {"input": 18.0, "output": 72.0},
    "gpt-4o-mini": {"input": 1.0, "output": 4.0},
    "default": {"input": 2.0, "output": 8.0},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    return (
        prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]
    ) / 1_000_000


def record_token_usage(
    user_id: int,
    conversation_id: int | None,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    total = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO token_usage
                (user_id, conversation_id, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, conversation_id, model, prompt_tokens, completion_tokens, total, cost),
        )
        conn.commit()


def get_user_token_summary(user_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(SUM(estimated_cost), 0) AS estimated_cost,
                COUNT(*) AS request_count
            FROM token_usage WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row)


def get_user_token_by_model(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT model,
                   SUM(prompt_tokens) AS prompt_tokens,
                   SUM(completion_tokens) AS completion_tokens,
                   SUM(total_tokens) AS total_tokens,
                   SUM(estimated_cost) AS estimated_cost,
                   COUNT(*) AS request_count
            FROM token_usage WHERE user_id = ?
            GROUP BY model ORDER BY total_tokens DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_usage(user_id: int, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT model, prompt_tokens, completion_tokens, total_tokens,
                   estimated_cost, created_at
            FROM token_usage WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
