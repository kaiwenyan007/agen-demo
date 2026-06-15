"""本机记住登录账号（可选密码），仅用于本地 Streamlit Demo。"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REMEMBER_FILE = PROJECT_ROOT / "data" / ".login_remember.json"


def load_remembered() -> dict[str, str] | None:
    if not REMEMBER_FILE.is_file():
        return None
    try:
        data = json.loads(REMEMBER_FILE.read_text(encoding="utf-8"))
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username:
            return None
        return {"username": username, "password": password}
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def save_remembered(username: str, password: str) -> None:
    REMEMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "username": username.strip(),
        "password": password,
    }
    REMEMBER_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_remembered() -> None:
    if REMEMBER_FILE.is_file():
        REMEMBER_FILE.unlink(missing_ok=True)
