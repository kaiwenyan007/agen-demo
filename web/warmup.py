"""Web 端预热封装（复用 agent.startup_bootstrap）。"""

from __future__ import annotations

from collections.abc import Callable

from agent.startup_bootstrap import (
    current_bootstrap_phase,
    is_bootstrap_ready,
    run_startup_bootstrap,
    schedule_startup_bootstrap,
    wait_bootstrap_ready,
)

# 兼容旧命名
warm_agent_stack = run_startup_bootstrap
schedule_agent_warmup = schedule_startup_bootstrap
is_agent_ready = is_bootstrap_ready
current_warm_phase = current_bootstrap_phase
wait_agent_ready = wait_bootstrap_ready

__all__ = [
    "warm_agent_stack",
    "schedule_agent_warmup",
    "is_agent_ready",
    "current_warm_phase",
    "wait_agent_ready",
    "schedule_startup_bootstrap",
]
