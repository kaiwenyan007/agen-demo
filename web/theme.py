"""暗色黑客风 UI 主题（Streamlit 自定义 CSS，支持桌面/手机响应式）。"""

from __future__ import annotations

import streamlit as st

BG = "#06080d"
PANEL = "#0d1117"
BORDER = "#1f2937"
GREEN = "#00ff41"
CYAN = "#00e5ff"
TEXT = "#c9d1d9"
MUTED = "#6b7280"

# 响应式：手机端 column 自动纵向堆叠
_RESPONSIVE_CSS = """
@media (max-width: 768px) {
    section.main .block-container {
        padding: 1rem 0.75rem 2rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        font-size: 0.75rem !important;
    }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.25rem !important; }
    .hack-logo { font-size: 0.52rem !important; }
}

@media (min-width: 769px) and (max-width: 1100px) {
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: calc(50% - 0.5rem) !important;
        flex: 1 1 calc(50% - 0.5rem) !important;
    }
}
"""

_BASE_CSS = f"""
<style>
html, body, [class*="css"] {{
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
}}

.stApp {{
    background: radial-gradient(ellipse at 20% 0%, #0a1628 0%, {BG} 45%, #030508 100%);
    color: {TEXT};
}}

.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 255, 65, 0.015) 2px,
        rgba(0, 255, 65, 0.015) 4px
    );
}}

/* 登录后主内容区：占满可用宽度，避免桌面布局挤压 */
section.main .block-container {{
    position: relative;
    z-index: 1;
    max-width: 100% !important;
    padding: 1.25rem 1.75rem 2rem !important;
}}

section.main .block-container > div {{
    max-width: 1100px;
    margin-left: auto;
    margin-right: auto;
}}

h1, h2, h3, h4 {{
    color: {GREEN} !important;
    text-shadow: 0 0 12px rgba(0, 255, 65, 0.35);
    letter-spacing: 0.06em;
    word-break: break-word;
}}

[data-testid="stCaptionContainer"] {{
    color: {MUTED} !important;
}}

.hack-logo {{
    font-family: 'Consolas', 'Courier New', monospace;
    color: {GREEN};
    font-size: clamp(0.52rem, 1.6vw, 0.75rem);
    line-height: 1.35;
    white-space: pre;
    overflow-x: auto;
    text-shadow: 0 0 8px rgba(0, 255, 65, 0.5);
    margin-bottom: 0.75rem;
}}

.stTextInput input, .stTextArea textarea {{
    background-color: #0a0f18 !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 2px !important;
    font-family: 'Consolas', monospace !important;
    width: 100% !important;
}}

.stTextInput input:focus {{
    border-color: {GREEN} !important;
    box-shadow: 0 0 8px rgba(0, 255, 65, 0.25) !important;
}}

.stButton > button, .stFormSubmitButton > button {{
    background: transparent !important;
    color: {GREEN} !important;
    border: 1px solid {GREEN} !important;
    border-radius: 2px !important;
    font-family: 'Consolas', monospace !important;
    letter-spacing: 0.06em;
    white-space: normal !important;
    word-break: break-word;
}}

.stButton > button:hover {{
    background: rgba(0, 255, 65, 0.12) !important;
    box-shadow: 0 0 16px rgba(0, 255, 65, 0.35) !important;
}}

.stButton > button[kind="primary"], .stFormSubmitButton > button {{
    background: rgba(0, 255, 65, 0.15) !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 4px;
}}

.stTabs [data-baseweb="tab"] {{
    color: {MUTED} !important;
    font-family: 'Consolas', monospace;
}}

.stTabs [aria-selected="true"] {{
    color: {GREEN} !important;
    background: rgba(0, 255, 65, 0.08) !important;
}}

[data-testid="stChatMessage"] {{
    background: rgba(13, 17, 23, 0.85) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 4px !important;
    max-width: 100%;
    overflow-wrap: anywhere;
}}

.agent-status {{
    color: {MUTED};
    font-size: 0.82rem;
    margin: 0 0 0.25rem 0;
    letter-spacing: 0.03em;
}}

.agent-status span {{
    color: {CYAN};
}}

[data-testid="stMetric"] {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 0.75rem;
    min-width: 0;
}}

[data-testid="stMetricValue"] {{
    color: {CYAN} !important;
    font-family: 'Consolas', monospace !important;
    font-size: clamp(1rem, 3vw, 1.45rem) !important;
    overflow-wrap: anywhere;
}}

[data-testid="stMetricLabel"] {{
    overflow-wrap: anywhere;
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0a0f18 0%, {BG} 100%) !important;
    border-right: 1px solid {BORDER} !important;
    min-width: 16rem;
}}

[data-testid="stSidebar"] .block-container {{
    padding: 1rem !important;
}}

[data-testid="stSidebar"] .stButton > button {{
    border-color: {BORDER} !important;
    color: {TEXT} !important;
}}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    overflow-x: auto;
}}

#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
    background: rgba(6, 8, 13, 0.9) !important;
    border-bottom: 1px solid {BORDER};
}}

{_RESPONSIVE_CSS}
</style>
"""

_AUTH_CSS = f"""
<style>
[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

section.main .block-container {{
    max-width: min(480px, 94vw) !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: 2rem 1rem 1.5rem !important;
}}

section.main .block-container > div {{
    max-width: 100% !important;
}}

section.main [data-testid="stTabs"] {{
    background: linear-gradient(145deg, {PANEL} 0%, #0a0f18 100%);
    border: 1px solid {GREEN};
    border-radius: 4px;
    padding: 0.75rem;
    box-shadow: 0 0 24px rgba(0, 255, 65, 0.1);
}}
</style>
"""

_LOGO_ASCII = r"""
┌─ AGENT://DEMO ────────┐
│ [SYS] LINK STANDBY... │
│ [RAG] DB ... OFFLINE  │
│ [AUTH] AWAIT LOGIN    │
└───────────────────────┘
"""


def inject_hacker_theme(*, auth_mode: bool = False) -> None:
    """注入黑客风 CSS；auth_mode 时居中窄屏登录布局。"""
    css = _BASE_CSS + (_AUTH_CSS if auth_mode else "")
    st.markdown(css, unsafe_allow_html=True)


def render_hack_logo() -> None:
    st.markdown(f'<div class="hack-logo">{_LOGO_ASCII}</div>', unsafe_allow_html=True)
