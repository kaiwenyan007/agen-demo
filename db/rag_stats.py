from db.database import get_db


def record_rag_query(
    user_id: int | None,
    conversation_id: int | None,
    query: str,
    hit: bool,
    result_count: int,
    search_mode: str,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO rag_queries
                (user_id, conversation_id, query, hit, result_count, search_mode)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                conversation_id,
                query[:500],
                1 if hit else 0,
                result_count,
                search_mode,
            ),
        )
        conn.commit()


def record_chroma_event(event_type: str) -> None:
    """event_type: memory_hit | disk_hit | rebuild"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chroma_cache_events (event_type) VALUES (?)",
            (event_type,),
        )
        conn.commit()


def get_user_rag_summary(user_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS query_count,
                COALESCE(SUM(hit), 0) AS hit_count,
                COALESCE(SUM(result_count), 0) AS total_chunks,
                SUM(CASE WHEN search_mode = 'vector' THEN 1 ELSE 0 END) AS vector_count,
                SUM(CASE WHEN search_mode = 'keyword' THEN 1 ELSE 0 END) AS keyword_count
            FROM rag_queries WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    data = dict(row)
    query_count = data["query_count"] or 0
    hit_count = data["hit_count"] or 0
    data["hit_rate"] = (hit_count / query_count * 100) if query_count else 0.0
    return data


def get_recent_rag_queries(user_id: int, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT query, hit, result_count, search_mode, created_at
            FROM rag_queries WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_chroma_cache_summary() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) AS cnt
            FROM chroma_cache_events
            GROUP BY event_type
            """
        ).fetchall()
    counts = {r["event_type"]: r["cnt"] for r in rows}
    memory = counts.get("memory_hit", 0)
    disk = counts.get("disk_hit", 0)
    rebuild = counts.get("rebuild", 0)
    total = memory + disk + rebuild
    cache_hits = memory + disk
    return {
        "memory_hit": memory,
        "disk_hit": disk,
        "rebuild": rebuild,
        "total_loads": total,
        "cache_hit_rate": (cache_hits / total * 100) if total else 0.0,
        "disk_hit_rate": (disk / total * 100) if total else 0.0,
    }
