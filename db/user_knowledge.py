"""用户个人知识库配置（本机 md 目录路径）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from db.database import get_db


@dataclass
class UserKnowledgeConfig:
    user_id: int
    knowledge_dir: str
    include_project: bool
    last_indexed_at: str | None
    doc_count: int
    chunk_count: int


def _default_row(user_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_knowledge_configs (user_id)
            VALUES (?)
            """,
            (user_id,),
        )
        conn.commit()


def get_user_knowledge_config(user_id: int) -> UserKnowledgeConfig:
    _default_row(user_id)
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT user_id, knowledge_dir, include_project,
                   last_indexed_at, doc_count, chunk_count
            FROM user_knowledge_configs WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return UserKnowledgeConfig(
        user_id=row["user_id"],
        knowledge_dir=row["knowledge_dir"] or "",
        include_project=bool(row["include_project"]),
        last_indexed_at=row["last_indexed_at"],
        doc_count=row["doc_count"] or 0,
        chunk_count=row["chunk_count"] or 0,
    )


def save_user_knowledge_config(
    user_id: int,
    knowledge_dir: str,
    include_project: bool,
) -> tuple[bool, str]:
    path = knowledge_dir.strip()
    if path:
        ok, msg = validate_knowledge_path(path)
        if not ok:
            return False, msg
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_knowledge_configs (user_id, knowledge_dir, include_project, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                knowledge_dir = excluded.knowledge_dir,
                include_project = excluded.include_project,
                updated_at = datetime('now')
            """,
            (user_id, path, 1 if include_project else 0),
        )
        conn.commit()
    return True, "配置已保存"


def validate_knowledge_path(raw_path: str) -> tuple[bool, str]:
    """校验本机知识库目录（本机 Streamlit 场景下允许任意可读目录）。"""
    if not raw_path.strip():
        return False, "路径不能为空"
    try:
        path = Path(raw_path.strip()).expanduser().resolve()
    except OSError as e:
        return False, f"路径无效: {e}"
    if not path.exists():
        return False, f"目录不存在: {path}"
    if not path.is_dir():
        return False, f"不是目录: {path}"
    return True, str(path)


def resolve_knowledge_dirs(knowledge_dir: str, include_project: bool) -> list[Path]:
    """根据表单值预览/解析索引目录（无需先写入数据库）。"""
    from agent.rag import KNOWLEDGE_DIR

    dirs: list[Path] = []
    if knowledge_dir.strip():
        ok, resolved = validate_knowledge_path(knowledge_dir)
        if ok:
            dirs.append(Path(resolved))
    if include_project and KNOWLEDGE_DIR.is_dir():
        dirs.append(KNOWLEDGE_DIR)
    return dirs


def count_md_files(*dirs: Path) -> int:
    total = 0
    seen: set[Path] = set()
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.glob("**/*.md"):
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                total += 1
    return total


def update_index_stats(user_id: int, doc_count: int, chunk_count: int) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE user_knowledge_configs
            SET doc_count = ?, chunk_count = ?,
                last_indexed_at = datetime('now'),
                updated_at = datetime('now')
            WHERE user_id = ?
            """,
            (doc_count, chunk_count, user_id),
        )
        conn.commit()
