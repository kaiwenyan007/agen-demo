from dataclasses import dataclass

from db.database import get_db


@dataclass
class UserApiConfig:
    api_key: str
    base_url: str
    model: str


def get_user_api_config(user_id: int) -> UserApiConfig:
    with get_db() as conn:
        row = conn.execute(
            "SELECT api_key, base_url, model FROM user_api_configs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return UserApiConfig(api_key="", base_url="https://api.deepseek.com", model="deepseek-chat")
    return UserApiConfig(
        api_key=row["api_key"] or "",
        base_url=row["base_url"] or "https://api.deepseek.com",
        model=row["model"] or "deepseek-chat",
    )


def save_user_api_config(user_id: int, api_key: str, base_url: str, model: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_api_configs (user_id, api_key, base_url, model, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                api_key = excluded.api_key,
                base_url = excluded.base_url,
                model = excluded.model,
                updated_at = datetime('now')
            """,
            (user_id, api_key.strip(), base_url.strip().rstrip("/"), model.strip()),
        )
        conn.commit()


def is_api_configured(user_id: int) -> bool:
    cfg = get_user_api_config(user_id)
    return bool(cfg.api_key and cfg.base_url and cfg.model)
