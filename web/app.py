"""
Agent Demo Web UI（Streamlit）

功能：用户注册/登录、API 配置、多轮对话、SQLite 持久化、Token 成本统计。
启动：py -m streamlit run web/app.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="Agent Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)


@st.cache_resource
def _ensure_db() -> bool:
    """数据库初始化只执行一次（跨页面刷新复用）。"""
    from db.database import init_db

    init_db()
    return True


_ensure_db()


def _init_session() -> None:
    defaults = {
        "user_id": None,
        "username": None,
        "page": "chat",
        "conversation_id": None,
        "model_options": None,
        "model_fetch_error": None,
        "pending_reply": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_session()


def render_auth() -> None:
    from web.theme import render_hack_logo

    render_hack_logo()
    st.title("AGENT DEMO")
    st.caption("// SECURE ACCESS · RAG NEURAL INTERFACE v0.7")

    tab_login, tab_register = st.tabs(["[ LOGIN ]", "[ REGISTER ]"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("USERNAME", key="login_user", placeholder="root@local")
            password = st.text_input("PASSWORD", type="password", key="login_pass")
            if st.form_submit_button(">> AUTHENTICATE", use_container_width=True):
                from db.auth import get_username, login_user

                user_id, msg = login_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = get_username(user_id)
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.error(f"[DENIED] {msg}")

    with tab_register:
        with st.form("register_form", clear_on_submit=False):
            new_user = st.text_input("NEW USER", key="reg_user", placeholder="hacker007")
            new_pass = st.text_input("PASSWORD", type="password", key="reg_pass")
            new_pass2 = st.text_input("CONFIRM", type="password", key="reg_pass2")
            if st.form_submit_button(">> CREATE ACCOUNT", use_container_width=True):
                from db.auth import get_username, register_user

                if new_pass != new_pass2:
                    st.error("[ERR] 两次密码不一致")
                else:
                    ok, msg, user_id = register_user(new_user, new_pass)
                    if ok and user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = get_username(user_id)
                        st.session_state.page = "chat"
                        st.rerun()
                    elif ok:
                        st.error("[ERR] 注册成功但无法自动登录")
                    else:
                        st.error(f"[ERR] {msg}")


def render_sidebar() -> None:
    st.sidebar.markdown(f"### // {st.session_state.username}")

    if st.sidebar.button("💬 CHAT", use_container_width=True):
        st.session_state.page = "chat"
    if st.sidebar.button("⚙️ API CONFIG", use_container_width=True):
        st.session_state.page = "settings"
    if st.sidebar.button("📊 TOKEN STATS", use_container_width=True):
        st.session_state.page = "stats"

    st.sidebar.divider()

    if st.session_state.page == "chat":
        from db.conversations import create_conversation, delete_conversation, list_conversations

        st.sidebar.markdown("**SESSIONS**")
        if st.sidebar.button("➕ NEW", use_container_width=True):
            cid = create_conversation(st.session_state.user_id)
            st.session_state.conversation_id = cid
            st.rerun()

        convs = list_conversations(st.session_state.user_id)
        for c in convs:
            label = c["title"][:20] + ("…" if len(c["title"]) > 20 else "")
            if st.sidebar.button(
                f"{'▸ ' if c['id'] == st.session_state.conversation_id else '  '}{label}",
                key=f"conv_{c['id']}",
                use_container_width=True,
            ):
                st.session_state.conversation_id = c["id"]
                st.rerun()

        if st.session_state.conversation_id:
            if st.sidebar.button("🗑️ DELETE", use_container_width=True):
                delete_conversation(st.session_state.user_id, st.session_state.conversation_id)
                st.session_state.conversation_id = None
                st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("LOGOUT", use_container_width=True):
        logout()
        st.rerun()


def render_settings() -> None:
    from agent.model_fetcher import fetch_available_models
    from db.api_config import get_user_api_config, save_user_api_config

    st.header("⚙️ API CONFIG")
    st.caption("// 独立密钥 · 独立模型 · 零交叉污染")

    cfg = get_user_api_config(st.session_state.user_id)

    api_key = st.text_input("OPENAI_API_KEY", value=cfg.api_key, type="password")
    base_url = st.text_input("OPENAI_BASE_URL", value=cfg.base_url)

    if st.button("FETCH MODELS", use_container_width=True):
        models, err = fetch_available_models(api_key, base_url)
        st.session_state.model_options = models
        st.session_state.model_fetch_error = err

    model_options = st.session_state.model_options
    if model_options is None:
        model_options = [cfg.model] if cfg.model else ["deepseek-chat"]
    elif cfg.model and cfg.model not in model_options:
        model_options = [cfg.model, *model_options]

    if st.session_state.model_fetch_error:
        st.warning(st.session_state.model_fetch_error)

    current_index = model_options.index(cfg.model) if cfg.model in model_options else 0
    model = st.selectbox("OPENAI_MODEL", options=model_options, index=current_index)

    if st.button("SAVE CONFIG", type="primary"):
        save_user_api_config(st.session_state.user_id, api_key, base_url, model)
        st.success("[OK] 配置已保存")
        st.session_state.model_options = None
        st.rerun()


def render_stats() -> None:
    from agent.rag import get_knowledge_base_info
    from agent.startup_splash import run_with_streamlit_splash
    from db.rag_stats import get_chroma_cache_summary, get_recent_rag_queries, get_user_rag_summary
    from db.token_stats import get_recent_usage, get_user_token_by_model, get_user_token_summary

    st.header("📊 TOKEN & RAG METRICS")

    summary = get_user_token_summary(st.session_state.user_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL TOKENS", f"{summary['total_tokens']:,}")
    c2.metric("PROMPT", f"{summary['prompt_tokens']:,}")
    c3.metric("COMPLETION", f"{summary['completion_tokens']:,}")
    c4.metric("COST ¥", f"{summary['estimated_cost']:.4f}")

    st.subheader("KNOWLEDGE BASE & CACHE")
    kb = run_with_streamlit_splash(get_knowledge_base_info, placeholder=st.empty())
    rag = get_user_rag_summary(st.session_state.user_id)
    cache = get_chroma_cache_summary()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("DOCS", kb["doc_count"])
    k2.metric("CHUNKS", kb["chunk_count"])
    k3.metric("RAG QUERIES", rag["query_count"])
    k4.metric("HIT RATE", f"{rag['hit_rate']:.1f}%")
    k5.metric("CACHE HIT", f"{cache['cache_hit_rate']:.1f}%")

    st.caption(
        f"memory={cache['memory_hit']} · disk={cache['disk_hit']} · rebuild={cache['rebuild']} · "
        f"vector={rag['vector_count']} · keyword={rag['keyword_count']}"
    )

    st.subheader("RAG LOG")
    rag_recent = get_recent_rag_queries(st.session_state.user_id)
    if rag_recent:
        st.dataframe(
            [
                {
                    "query": r["query"][:60] + ("…" if len(r["query"]) > 60 else ""),
                    "hit": "Y" if r["hit"] else "N",
                    "chunks": r["result_count"],
                    "mode": r["search_mode"],
                    "at": r["created_at"],
                }
                for r in rag_recent
            ],
            use_container_width=True,
        )
    else:
        st.info("[EMPTY] 暂无 RAG 检索记录")

    st.subheader("BY MODEL")
    by_model = get_user_token_by_model(st.session_state.user_id)
    if by_model:
        st.dataframe(by_model, use_container_width=True)
    else:
        st.info("[EMPTY] 暂无使用记录")

    st.subheader("RECENT")
    recent = get_recent_usage(st.session_state.user_id)
    if recent:
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("[EMPTY] 暂无使用记录")


def render_chat() -> None:
    from agent.langchain_agent import run_agent
    from agent.startup_splash import run_with_streamlit_splash
    from db.api_config import get_user_api_config, is_api_configured
    from db.conversations import (
        add_message,
        create_conversation,
        get_messages,
        list_conversations,
        messages_to_chat_history,
        update_conversation_title,
    )
    from db.token_stats import record_token_usage

    if not is_api_configured(st.session_state.user_id):
        st.warning("[WARN] 请先在 API CONFIG 中配置 Key / URL / Model")
        return

    if st.session_state.conversation_id is None:
        convs = list_conversations(st.session_state.user_id)
        if convs:
            st.session_state.conversation_id = convs[0]["id"]
        else:
            st.session_state.conversation_id = create_conversation(st.session_state.user_id)

    conv_id = st.session_state.conversation_id
    messages = get_messages(conv_id)

    st.subheader("💬 NEURAL CHAT")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pending_reply
    if pending and pending.get("conv_id") == conv_id:
        user_id = st.session_state.user_id
        cfg = get_user_api_config(user_id)
        history = messages_to_chat_history(messages[:-1])
        prompt_text = pending["prompt"]

        with st.chat_message("assistant"):
            splash = st.empty()

            def _invoke():
                # session_state 不可在后台线程访问，闭包捕获主线程变量
                return run_agent(
                    prompt_text,
                    cfg,
                    chat_history=history,
                    verbose=False,
                    user_id=user_id,
                    conversation_id=conv_id,
                )

            try:
                reply, usage = run_with_streamlit_splash(_invoke, placeholder=splash)
            except Exception as e:
                reply = f"[FAIL] 调用失败: {e}"
                usage = None
            st.markdown(reply)

        add_message(conv_id, "assistant", reply)
        if usage and usage.total_tokens > 0:
            record_token_usage(
                user_id,
                conv_id,
                cfg.model,
                usage.prompt_tokens,
                usage.completion_tokens,
            )
        st.session_state.pending_reply = None
        return

    if prompt := st.chat_input(">> 输入指令..."):
        add_message(conv_id, "user", prompt)

        if len(messages) == 0:
            title = prompt[:30] + ("…" if len(prompt) > 30 else "")
            update_conversation_title(st.session_state.user_id, conv_id, title)

        st.session_state.pending_reply = {"conv_id": conv_id, "prompt": prompt}
        st.rerun()


def main() -> None:
    from web.theme import inject_hacker_theme

    _init_session()
    is_auth = st.session_state.user_id is None
    inject_hacker_theme(auth_mode=is_auth)

    if is_auth:
        render_auth()
        return

    render_sidebar()

    page = st.session_state.page
    if page == "settings":
        render_settings()
    elif page == "stats":
        render_stats()
    else:
        render_chat()


if __name__ == "__main__":
    main()
