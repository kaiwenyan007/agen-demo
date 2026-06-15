"""
启动等待时的趣味提示（B 站风格）与 CLI / Streamlit 加载动画。
"""

from __future__ import annotations

import random
import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

# 随机轮换的调皮提示语
SPLASH_MESSAGES: tuple[str, ...] = (
    "核反应堆正在预热，请勿靠近…",
    "正在给仓鼠轮子抹润滑油…",
    "向量维度对齐中，请勿打扰…",
    "知识库文档正在列队入场…",
    "Embedding 模型刚从午睡中醒来…",
    "Chroma 索引正在做伸展运动…",
    "正在贿赂 GPU 让它加个班…",
    "Tokenizer 正在逐字辨认中…",
    "Agent 大脑皮层正在通电…",
    "正在从平行宇宙同步知识…",
    "缓存命中率祈祷仪式进行中…",
    "RAG 检索器正在穿靴子…",
    "神经网络突触连接中…",
    "正在检查知识库里有没有摸鱼的文档…",
    "量子隧穿效应加载向量中…",
    "提示词工程团队正在开会…",
    "正在给 LLM 倒一杯热茶…",
    "磁盘上的 .chroma 文件夹正在伸懒腰…",
    "语义空间坐标系校准中…",
    "最后 1% 的进度需要 99% 的时间…",
)


def pick_splash_message() -> str:
    return random.choice(SPLASH_MESSAGES)


def _run_task_in_background(
    task: Callable[[], T],
) -> tuple[list[T], list[BaseException], threading.Event, threading.Thread]:
    """在后台线程执行任务，返回结果容器与停止信号。"""
    stop = threading.Event()
    result: list[T] = []
    error: list[BaseException] = []

    def worker() -> None:
        try:
            result.append(task())
        except BaseException as exc:
            error.append(exc)
        finally:
            stop.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return result, error, stop, thread


def _finalize_task(result: list[T], error: list[BaseException], thread: threading.Thread) -> T:
    thread.join(timeout=5)
    if error:
        raise error[0]
    return result[0]


def _rotate_messages(
    stop: threading.Event,
    interval: float,
    on_message: Callable[[str], None],
) -> None:
    """按间隔轮换趣味提示，直到 stop 被触发。"""
    idx = 0
    while not stop.is_set():
        on_message(SPLASH_MESSAGES[idx % len(SPLASH_MESSAGES)])
        idx += 1
        stop.wait(interval)


def run_with_cli_splash(
    task: Callable[[], T],
    console=None,
    interval: float = 0.65,
) -> T:
    """CLI：后台执行任务，前台轮换趣味提示（Rich Spinner）。"""
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner

    console = console or Console()
    result, error, stop, thread = _run_task_in_background(task)

    with Live(console=console, refresh_per_second=10) as live:
        def _show_message(msg: str) -> None:
            live.update(Spinner("dots", text=f"[bold cyan]{msg}[/]"))

        _rotate_messages(stop, interval, _show_message)

    return _finalize_task(result, error, thread)


def run_with_streamlit_splash(
    task: Callable[[], T],
    placeholder=None,
    interval: float = 0.65,
) -> T:
    """Streamlit：后台执行任务，前台轮换趣味提示。"""
    import streamlit as st

    placeholder = placeholder or st.empty()
    result, error, stop, thread = _run_task_in_background(task)

    def _show_message(msg: str) -> None:
        placeholder.markdown(f"### ⚡ {msg}")

    _rotate_messages(stop, interval, _show_message)
    placeholder.empty()
    return _finalize_task(result, error, thread)
