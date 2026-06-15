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

from agent.startup_bootstrap import configure_startup_logging, schedule_startup_bootstrap

configure_startup_logging()
schedule_startup_bootstrap()

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
        "auth_mode": "login",
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


def _enter_app(user_id: int) -> None:
    """登录/注册成功后进入主界面，并恢复最近会话。"""
    from db.auth import get_username
    from db.conversations import list_conversations

    st.session_state.user_id = user_id
    st.session_state.username = get_username(user_id)
    st.session_state.page = "chat"
    convs = list_conversations(user_id)
    st.session_state.conversation_id = convs[0]["id"] if convs else None
    st.rerun()


def render_auth() -> None:
    from web.theme import render_hack_logo

    render_hack_logo()
    st.title("AGENT DEMO")
    st.caption("// SECURE ACCESS · RAG NEURAL INTERFACE v0.7")

    st.radio(
        "auth_tab",
        options=["login", "register"],
        format_func=lambda v: "[ LOGIN ]" if v == "login" else "[ REGISTER ]",
        horizontal=True,
        label_visibility="collapsed",
        key="auth_mode",
    )

    st.markdown("---")

    if st.session_state.auth_mode == "login":
        username = st.text_input("USERNAME", key="login_user", placeholder="root@local")
        password = st.text_input("PASSWORD", type="password", key="login_pass")
        if st.button(">> AUTHENTICATE", use_container_width=True, type="primary", key="login_btn"):
            from db.auth import login_user

            user_id, msg = login_user(username, password)
            if user_id:
                _enter_app(user_id)
            else:
                st.error(f"[DENIED] {msg}")
    else:
        new_user = st.text_input("NEW USER", key="reg_user", placeholder="hacker007")
        new_pass = st.text_input("PASSWORD", type="password", key="reg_pass")
        new_pass2 = st.text_input("CONFIRM", type="password", key="reg_pass2")
        if st.button(">> CREATE ACCOUNT", use_container_width=True, type="primary", key="register_btn"):
            from db.auth import register_user

            if new_pass != new_pass2:
                st.error("[ERR] 两次密码不一致")
            else:
                ok, msg, user_id = register_user(new_user, new_pass)
                if ok and user_id:
                    _enter_app(user_id)
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
    if st.sidebar.button("📚 KNOWLEDGE", use_container_width=True):
        st.session_state.page = "knowledge"
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


def render_knowledge() -> None:
    from agent.rag import build_vectorstore, get_knowledge_base_info, get_knowledge_dirs, reset_vectorstore, user_chroma_dir
    from db.user_knowledge import (
        count_md_files,
        get_user_knowledge_config,
        resolve_knowledge_dirs,
        save_user_knowledge_config,
    )

    user_id = st.session_state.user_id
    cfg = get_user_knowledge_config(user_id)

    st.header("📚 LOCAL KNOWLEDGE")
    st.caption("// 本机 Streamlit：可索引 C 盘等本地 md 目录 · 每人独立向量库")

    st.info(
        "在本机运行 `streamlit run web/app.py` 时，Python 进程可直接读取你填写的 Windows 路径。"
        "可点击「选择文件夹」用系统对话框选取目录。修改 md 文件后请点击「重建索引」。"
    )

    draft_key = f"knowledge_dir_draft_{user_id}"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = cfg.knowledge_dir

    pick_col, input_col = st.columns([1, 3])
    with pick_col:
        if st.button("📁 选择文件夹", use_container_width=True):
            from web.local_folder import pick_local_folder

            picked = pick_local_folder(title="选择 Markdown 知识库目录")
            if picked:
                st.session_state[draft_key] = picked
                st.rerun()
            else:
                st.warning("未选择文件夹（或当前环境不支持对话框）")
    with input_col:
        knowledge_dir = st.text_input(
            "KNOWLEDGE_DIR",
            key=draft_key,
            placeholder=r"C:\Users\你的用户名\Documents\notes",
            help="可手动输入路径，或用左侧按钮选择文件夹",
        )
    include_project = st.checkbox(
        "同时索引项目公共库 knowledge/",
        value=cfg.include_project,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("SAVE PATH", use_container_width=True):
            ok, msg = save_user_knowledge_config(user_id, knowledge_dir, include_project)
            if ok:
                reset_vectorstore(user_id)
                st.success(f"[OK] {msg}，请重建索引")
            else:
                st.error(f"[ERR] {msg}")
    with col2:
        if st.button("SCAN", use_container_width=True):
            dirs = resolve_knowledge_dirs(knowledge_dir, include_project)
            if not dirs:
                st.warning("请先填写有效目录，或勾选公共库")
            else:
                n = count_md_files(*dirs)
                st.success(f"发现 {n} 个 .md 文件")
                for d in dirs:
                    st.caption(str(d))
    with col3:
        rebuild = st.button("REBUILD INDEX", type="primary", use_container_width=True)

    if rebuild:
        dirs = get_knowledge_dirs(user_id)
        if not dirs:
            st.error("没有可索引的目录。请填写本机路径或勾选公共库。")
        else:
            save_user_knowledge_config(user_id, knowledge_dir, include_project)
            status = st.empty()
            try:
                status.markdown("⏳ 正在扫描 md 并构建向量索引…")
                build_vectorstore(user_id=user_id, force_rebuild=True)
                info = get_knowledge_base_info(user_id)
                status.success(
                    f"[OK] 索引完成：{info['doc_count']} 篇 md → {info['chunk_count']} 个片段"
                )
            except Exception as e:
                status.error(f"[FAIL] 索引失败: {e}")

    st.divider()
    st.subheader("STATUS")
    dirs = get_knowledge_dirs(user_id)
    if dirs:
        for d in dirs:
            st.markdown(f"- `{d}`")
    else:
        st.markdown("- _未配置目录_")

    c1, c2, c3 = st.columns(3)
    c1.metric("DOCS", cfg.doc_count)
    c2.metric("CHUNKS", cfg.chunk_count)
    c3.metric("LAST INDEX", cfg.last_indexed_at or "—")

    chroma_path = user_chroma_dir(user_id)
    st.caption(f"向量库路径: `{chroma_path}`")


def render_stats() -> None:
    from db.rag_stats import get_chroma_cache_summary, get_recent_rag_queries, get_user_rag_summary
    from db.token_stats import get_recent_usage, get_user_token_by_model, get_user_token_summary

    st.header("📊 TOKEN & RAG METRICS")

    summary = get_user_token_summary(st.session_state.user_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL TOKENS", f"{summary['total_tokens']:,}")
    c2.metric("PROMPT", f"{summary['prompt_tokens']:,}")
    c3.metric("COMPLETION", f"{summary['completion_tokens']:,}")
    c4.metric("COST ¥", f"{summary['estimated_cost']:.4f}")

    _render_kb_metrics_fragment()

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


@st.fragment
def _render_kb_metrics_fragment() -> None:
    """知识库统计单独 fragment 加载，不阻塞 Token 指标先显示。"""
    from agent.rag import get_knowledge_base_info
    from db.rag_stats import get_chroma_cache_summary, get_user_rag_summary

    st.subheader("KNOWLEDGE BASE & CACHE")
    with st.spinner("正在读取向量库…"):
        kb = get_knowledge_base_info(st.session_state.user_id)
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
    if kb.get("source_dirs"):
        st.caption("sources: " + " | ".join(kb["source_dirs"]))


def render_chat() -> None:
    from db.api_config import get_user_api_config, is_api_configured
    from db.conversations import (
        add_message,
        create_conversation,
        get_messages,
        list_conversations,
        update_conversation_title,
    )

    if not is_api_configured(st.session_state.user_id):
        st.warning("[WARN] 请先在 API CONFIG 中配置 Key / URL / Model")
        st.chat_input(">> 输入指令...", disabled=True)
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

    from web.warmup import current_warm_phase, is_agent_ready

    if not is_agent_ready():
        st.caption(f"⏳ {current_warm_phase()} · 首条消息可能稍慢，请稍候")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pending_reply
    if pending and pending.get("conv_id") == conv_id:
        from agent.langchain_agent import iter_agent_reply_events
        from db.conversations import messages_to_chat_history
        from db.token_stats import record_token_usage
        from web.warmup import wait_agent_ready

        user_id = st.session_state.user_id
        cfg = get_user_api_config(user_id)
        history = messages_to_chat_history(messages[:-1])
        prompt_text = pending["prompt"]

        with st.chat_message("assistant"):
            status_ph = st.empty()
            answer_ph = st.empty()
            reply_parts: list[str] = []

            def _show_status(text: str) -> None:
                status_ph.markdown(
                    f'<p class="agent-status">⏳ <span>{text}</span></p>',
                    unsafe_allow_html=True,
                )

            _show_status("正在准备 Agent 引擎…")
            wait_agent_ready(on_phase=_show_status)

            events, token_handler = iter_agent_reply_events(
                prompt_text,
                cfg,
                chat_history=history,
                verbose=False,
                user_id=user_id,
                conversation_id=conv_id,
            )

            try:
                for kind, text in events:
                    if kind == "status":
                        _show_status(text)
                    else:
                        reply_parts.append(text)
                        if reply_parts:
                            status_ph.empty()
                        answer_ph.markdown("".join(reply_parts))
            except Exception as e:
                status_ph.empty()
                reply_parts = [f"[FAIL] 调用失败: {e}"]
                answer_ph.markdown(reply_parts[0])

            reply = "".join(reply_parts).strip()
            if not reply:
                status_ph.empty()
                reply = "[FAIL] 模型未返回内容"
                answer_ph.markdown(reply)
            usage = token_handler.usage

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
        st.rerun()

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
    elif page == "knowledge":
        render_knowledge()
    elif page == "stats":
        render_stats()
    else:
        render_chat()


if __name__ == "__main__":
    main()
