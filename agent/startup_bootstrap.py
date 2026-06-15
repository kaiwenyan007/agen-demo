"""
项目启动预热：加载配置、初始化 DB、预加载 Agent/RAG，并输出结构化日志。

日志命名空间：agent_demo.startup（输出到 stderr，Streamlit / CLI 终端可见）
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger("agent_demo.startup")

_bootstrap_lock = threading.Lock()
_bootstrap_scheduled = False
_bootstrap_done = threading.Event()
_bootstrap_phase = "等待启动预热…"
_bootstrap_steps_done: list[tuple[str, float]] = []
_bootstrap_started_at: float | None = None
_logging_configured = False


@dataclass
class BootstrapResult:
    ok: bool
    elapsed_s: float
    steps: list[tuple[str, float]] = field(default_factory=list)
    error: str | None = None


def configure_startup_logging(*, level: int = logging.INFO) -> None:
    """配置启动日志（幂等，仅初始化一次）。"""
    global _logging_configured
    if _logging_configured:
        return
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    root = logging.getLogger("agent_demo")
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)
    _logging_configured = True


def _set_phase(phase: str) -> None:
    global _bootstrap_phase
    _bootstrap_phase = phase


def _mask_secret(value: str) -> str:
    if not value:
        return "(未配置)"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}…{value[-4:]}"


def _log_config_summary() -> None:
    use_lc = os.getenv("USE_LANGCHAIN", "1")
    use_local = os.getenv("USE_LOCAL_EMBEDDING", "0")
    use_kw = os.getenv("USE_KEYWORD_FALLBACK", "0")
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    embed_model = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    api_key = _mask_secret(os.getenv("OPENAI_API_KEY", ""))

    logger.info("========== Agent Demo 启动预热 ==========")
    logger.info("[config] USE_LANGCHAIN=%s", use_lc)
    logger.info("[config] USE_LOCAL_EMBEDDING=%s USE_KEYWORD_FALLBACK=%s", use_local, use_kw)
    logger.info("[config] OPENAI_MODEL=%s", model)
    logger.info("[config] OPENAI_BASE_URL=%s", base_url)
    logger.info("[config] OPENAI_API_KEY=%s", api_key)
    if use_local.lower() in ("1", "true", "yes"):
        path = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
        logger.info(
            "[config] LOCAL_EMBEDDING=%s path=%s",
            embed_model,
            path or "(自动下载/缓存)",
        )


def _step(name: str, fn: Callable[[], None], steps: list[tuple[str, float]]) -> None:
    _set_phase(name)
    logger.info("[warmup] %s …", name)
    t0 = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - t0
    steps.append((name, elapsed))
    _bootstrap_steps_done.append((name, elapsed))
    logger.info("[warmup] %s 完成 (%.2fs)", name, elapsed)


def run_startup_bootstrap(
    *,
    init_database: bool = True,
    log_config: bool = True,
    preload_agent: bool = True,
    preload_embeddings: bool = True,
    preload_chroma: bool = True,
    on_phase: Callable[[str], None] | None = None,
) -> BootstrapResult | None:
    """同步执行启动预热；供 CLI 或后台线程调用。"""
    configure_startup_logging()
    if _bootstrap_done.is_set():
        logger.debug("[warmup] 已预热，跳过")
        return BootstrapResult(ok=True, elapsed_s=0.0)

    with _bootstrap_lock:
        if _bootstrap_done.is_set():
            return BootstrapResult(ok=True, elapsed_s=0.0)

        global _bootstrap_steps_done, _bootstrap_started_at
        _bootstrap_steps_done = []
        _bootstrap_started_at = time.perf_counter()

        steps: list[tuple[str, float]] = []
        t_all = time.perf_counter()
        result: BootstrapResult

        def phase(msg: str) -> None:
            _set_phase(msg)
            if on_phase:
                on_phase(msg)

        try:
            if log_config:
                phase("读取运行配置…")
                _log_config_summary()

            if init_database:
                def _db() -> None:
                    from db.database import init_db

                    init_db()
                    from db.database import DB_PATH

                    logger.info("[db] SQLite 就绪: %s", DB_PATH)

                _step("初始化 SQLite 数据库", _db, steps)

            if preload_chroma:
                def _chroma() -> None:
                    from agent.rag import CHROMA_DIR, get_knowledge_base_info

                    info = get_knowledge_base_info(load_vectorstore=False)
                    logger.info(
                        "[rag] 向量库元数据: chunks=%d ready=%s dir=%s（仅用户配置知识库，首次 RAG/重建时加载）",
                        info["chunk_count"],
                        info["chroma_ready"],
                        CHROMA_DIR,
                    )

                _step("检查向量库配置", _chroma, steps)

            if preload_agent:
                def _agent() -> None:
                    from agent import langchain_agent  # noqa: F401

                    logger.info("[agent] LangChain Agent 模块已加载")

                _step("加载 LangChain Agent 模块", _agent, steps)

            if preload_embeddings and os.getenv("USE_LOCAL_EMBEDDING", "0").lower() in ("1", "true", "yes"):
                def _embed() -> None:
                    from agent.rag import get_embeddings

                    get_embeddings()
                    logger.info("[embedding] 本地 Embedding 模型已加载")

                _step("加载本地 Embedding 模型", _embed, steps)

            elapsed = time.perf_counter() - t_all
            _set_phase("引擎就绪")
            logger.info("[warmup] 全部完成，总耗时 %.2fs", elapsed)
            logger.info("==========================================")
            result = BootstrapResult(ok=True, elapsed_s=elapsed, steps=steps)
        except Exception as exc:
            elapsed = time.perf_counter() - t_all
            logger.exception("[warmup] 预热失败 (%.2fs): %s", elapsed, exc)
            result = BootstrapResult(ok=False, elapsed_s=elapsed, steps=steps, error=str(exc))
        finally:
            _bootstrap_done.set()
        return result


def schedule_startup_bootstrap(
    *,
    init_database: bool = True,
    log_config: bool = True,
    preload_agent: bool = True,
    preload_embeddings: bool = True,
    preload_chroma: bool = True,
) -> None:
    """后台线程触发预热（每个进程仅调度一次）。"""
    global _bootstrap_scheduled
    configure_startup_logging()
    with _bootstrap_lock:
        if _bootstrap_scheduled:
            return
        _bootstrap_scheduled = True

    logger.info("[warmup] 已调度后台预热线程")

    def _worker() -> None:
        run_startup_bootstrap(
            init_database=init_database,
            log_config=log_config,
            preload_agent=preload_agent,
            preload_embeddings=preload_embeddings,
            preload_chroma=preload_chroma,
        )

    threading.Thread(target=_worker, name="agent-demo-bootstrap", daemon=True).start()


def ensure_full_bootstrap_scheduled() -> None:
    """登录后调度全量预热（未调度时触发）。"""
    schedule_startup_bootstrap()


def get_bootstrap_progress() -> dict:
    """供 Web 启动画面轮询的预热进度。"""
    elapsed = 0.0
    if _bootstrap_started_at is not None:
        elapsed = time.perf_counter() - _bootstrap_started_at
    return {
        "ready": _bootstrap_done.is_set(),
        "scheduled": _bootstrap_scheduled,
        "phase": current_bootstrap_phase(),
        "steps": list(_bootstrap_steps_done),
        "elapsed_s": elapsed,
    }


def is_bootstrap_ready() -> bool:
    return _bootstrap_done.is_set()


def current_bootstrap_phase() -> str:
    return _bootstrap_phase if not _bootstrap_done.is_set() else "引擎就绪"


def wait_bootstrap_ready(
    on_phase: Callable[[str], None] | None = None,
    *,
    timeout: float = 120.0,
    poll: float = 0.35,
) -> bool:
    if _bootstrap_done.is_set():
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        if on_phase:
            on_phase(current_bootstrap_phase())
        if _bootstrap_done.wait(timeout=poll):
            return True
    return _bootstrap_done.is_set()
