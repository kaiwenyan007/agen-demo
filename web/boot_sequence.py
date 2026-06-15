"""登录后引擎预热启动画面（非阻塞 fragment 轮询刷新）。"""

from __future__ import annotations

import html
import random
import time
from datetime import timedelta

import streamlit as st

from agent.startup_bootstrap import get_bootstrap_progress, is_bootstrap_ready

_BOOT_CSS = """
<style>
.boot-wrap {
    max-width: 640px;
    margin: 0 auto;
    font-family: 'Consolas', 'Courier New', monospace;
}
.boot-header {
    color: #00ff41;
    font-size: 0.78rem;
    line-height: 1.45;
    text-shadow: 0 0 10px rgba(0, 255, 65, 0.45);
    margin-bottom: 1rem;
    white-space: pre;
}
.boot-panel {
    background: linear-gradient(145deg, #0d1117 0%, #0a0f18 100%);
    border: 1px solid #00ff41;
    border-radius: 4px;
    padding: 1rem 1.1rem;
    box-shadow: 0 0 28px rgba(0, 255, 65, 0.12);
    position: relative;
    overflow: hidden;
}
.boot-panel::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 255, 65, 0.03) 2px,
        rgba(0, 255, 65, 0.03) 4px
    );
    animation: boot-scan 3.5s linear infinite;
}
@keyframes boot-scan {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}
.boot-bar-track {
    height: 6px;
    background: #1f2937;
    border-radius: 3px;
    overflow: hidden;
    margin: 0.85rem 0 0.65rem;
}
.boot-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #00e5ff, #00ff41);
    box-shadow: 0 0 12px rgba(0, 255, 65, 0.6);
    transition: width 0.45s ease;
}
.boot-phase {
    color: #00e5ff;
    font-size: 0.88rem;
    letter-spacing: 0.04em;
    min-height: 1.4rem;
}
.boot-phase .cursor {
    display: inline-block;
    width: 0.55em;
    animation: boot-blink 0.9s step-end infinite;
    color: #00ff41;
}
@keyframes boot-blink {
    50% { opacity: 0; }
}
.boot-log {
    margin-top: 0.75rem;
    font-size: 0.72rem;
    line-height: 1.55;
    color: #6b7280;
    max-height: 9rem;
    overflow-y: auto;
}
.boot-log .done { color: #00ff41; }
.boot-log .active { color: #00e5ff; }
.boot-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: #6b7280;
    margin-top: 0.55rem;
}
.boot-flavor {
    margin-top: 0.9rem;
    font-size: 0.7rem;
    color: #4b5563;
    font-style: italic;
    letter-spacing: 0.02em;
}
</style>
"""

_PHASE_HINTS = [
    "读取运行配置…",
    "初始化 SQLite 数据库",
    "检查向量库配置",
    "加载 LangChain Agent 模块",
    "加载本地 Embedding 模型",
    "引擎就绪",
]

_FLAVOR_LINES = [
    "正在握手 RAG 神经链路…",
    "同步知识向量矩阵…",
    "校准 Agent 推理核心…",
    "挂载本地 Embedding 子系统…",
    "建立安全会话隧道…",
    "编译工具调用协议栈…",
]


def _phase_percent(phase: str, steps_done: int) -> int:
    for i, hint in enumerate(_PHASE_HINTS):
        if hint in phase or phase.startswith(hint.replace("…", "")):
            return min(98, int((i + 1) / len(_PHASE_HINTS) * 100))
    if steps_done:
        return min(95, 12 + steps_done * 18)
    if "等待" in phase:
        return 4
    return 10


def _build_log_lines(steps: list[tuple[str, float]], phase: str) -> str:
    lines: list[str] = []
    for name, elapsed in steps:
        lines.append(
            f'<div class="done">[OK] {html.escape(name)} '
            f'<span style="color:#4b5563">({elapsed:.2f}s)</span></div>'
        )
    if phase and phase != "引擎就绪" and not any(name == phase for name, _ in steps):
        lines.append(f'<div class="active">[>>] {html.escape(phase)} …</div>')
    if not lines:
        lines.append('<div class="active">[>>] 等待调度预热任务…</div>')
    return "\n".join(lines)


def render_boot_sequence() -> None:
    """登录成功后展示引擎启动动画，预热完成自动进入主界面。"""
    from web.theme import render_hack_logo

    render_hack_logo()
    st.markdown(_BOOT_CSS, unsafe_allow_html=True)

    username = html.escape(st.session_state.get("username") or "operator")
    boot_start = st.session_state.setdefault("_boot_start_ts", time.time())

    st.markdown(
        f"""<div class="boot-wrap">
<div class="boot-header">┌─ NEURAL BOOT SEQUENCE ─────────┐
│ [AUTH] GRANTED · USER {username:<16} │
│ [SYS]  ENGINE COLD START IN PROGRESS │
└──────────────────────────────────┘</div>""",
        unsafe_allow_html=True,
    )

    if st.button("跳过等待，先进入（聊天可能稍慢）", type="secondary"):
        st.session_state.boot_skipped = True
        st.session_state.pop("_boot_start_ts", None)
        st.rerun()

    @st.fragment(run_every=timedelta(milliseconds=420))
    def _boot_tick() -> None:
        progress = get_bootstrap_progress()
        phase = progress["phase"]
        steps = progress["steps"]
        pct = _phase_percent(phase, len(steps))
        elapsed = time.time() - boot_start
        flavor = random.choice(_FLAVOR_LINES)

        log_html = _build_log_lines(steps, phase)
        st.markdown(
            f"""<div class="boot-wrap"><div class="boot-panel">
<div class="boot-phase">// {html.escape(phase)}<span class="cursor">_</span></div>
<div class="boot-bar-track"><div class="boot-bar-fill" style="width:{pct}%"></div></div>
<div class="boot-meta">
  <span>PROGRESS {pct:>3}%</span>
  <span>ELAPSED {elapsed:>5.1f}s</span>
</div>
<div class="boot-log">{log_html}</div>
<div class="boot-flavor">// {html.escape(flavor)}</div>
</div></div>""",
            unsafe_allow_html=True,
        )

        if is_bootstrap_ready():
            st.session_state.pop("_boot_start_ts", None)
            st.session_state.pop("boot_skipped", None)
            st.rerun()

    _boot_tick()
