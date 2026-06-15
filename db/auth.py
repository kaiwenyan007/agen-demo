import bcrypt

from db.database import get_db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def register_user(username: str, password: str) -> tuple[bool, str, int | None]:
    username = username.strip()
    if len(username) < 2:
        return False, "用户名至少 2 个字符", None
    if len(password) < 6:
        return False, "密码至少 6 个字符", None

    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )
            user_id = cur.lastrowid
            conn.execute(
                "INSERT INTO user_api_configs (user_id) VALUES (?)",
                (user_id,),
            )
            conn.commit()
        return True, "注册成功", user_id
    except Exception as e:
        if "UNIQUE" in str(e):
            return False, "用户名已存在", None
        return False, f"注册失败: {e}", None


def login_user(username: str, password: str) -> tuple[int | None, str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row:
        return None, "用户不存在"
    if not verify_password(password, row["password_hash"]):
        return None, "密码错误"
    return row["id"], "登录成功"


def get_username(user_id: int) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["username"] if row else ""
