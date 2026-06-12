"""
Agent Demo Web UI（Streamlit）

功能：用户注册/登录、API 配置、多轮对话、SQLite 持久化、Token 成本统计。
启动：streamlit run web/app.py
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from agent.langchain_agent import run_agent
from agent.model_fetcher import fetch_available_models
from agent.rag import build_vectorstore
from db.api_config import get_user_api_config, is_api_configured, save_user_api_config
from db.auth import get_username, login_user, register_user
from db.conversations import (
    add_message,
    create_conversation,
    delete_conversation,
    get_messages,
    list_conversations,
    messages_to_chat_history,
    update_conversation_title,
)
from db.database import init_db
from db.token_stats import get_recent_usage, get_user_token_by_model, get_user_token_summary, record_token_usage

st.set_page_config(page_title="Agent Demo", page_icon="🤖", layout="wide")

# 初始化数据库 & 预热 RAG（全局共享知识库）
init_db()


@st.cache_resource
def _warmup_rag():
    build_vectorstore()
    return True


_warmup_rag()


def _init_session():
    defaults = {
        "user_id": None,
        "username": None,
        "page": "chat",
        "conversation_id": None,
        "model_options": [],
        "model_fetch_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_session()


def render_auth():
    st.title("🤖 Agent Demo")
    st.caption("注册登录后，每位用户拥有独立的 API 配置、对话记录与 Token 统计")

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("用户名", key="login_user")
            password = st.text_input("密码", type="password", key="login_pass")
            if st.form_submit_button("登录", use_container_width=True):
                user_id, msg = login_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = get_username(user_id)
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("用户名", key="reg_user")
            new_pass = st.text_input("密码", type="password", key="reg_pass")
            new_pass2 = st.text_input("确认密码", type="password", key="reg_pass2")
            if st.form_submit_button("注册", use_container_width=True):
                if new_pass != new_pass2:
                    st.error("两次密码不一致")
                else:
                    ok, msg = register_user(new_user, new_pass)
                    if ok:
                        st.success(msg + "，请切换到登录页")
                    else:
                        st.error(msg)


def render_sidebar():
    st.sidebar.title(f"👤 {st.session_state.username}")

    if st.sidebar.button("💬 聊天", use_container_width=True):
        st.session_state.page = "chat"
    if st.sidebar.button("⚙️ API 设置", use_container_width=True):
        st.session_state.page = "settings"
    if st.sidebar.button("📊 Token 统计", use_container_width=True):
        st.session_state.page = "stats"

    st.sidebar.divider()

    if st.session_state.page == "chat":
        st.sidebar.subheader("对话列表")
        if st.sidebar.button("➕ 新对话", use_container_width=True):
            cid = create_conversation(st.session_state.user_id)
            st.session_state.conversation_id = cid
            st.rerun()

        convs = list_conversations(st.session_state.user_id)
        for c in convs:
            label = c["title"][:20] + ("…" if len(c["title"]) > 20 else "")
            if st.sidebar.button(
                f"{'📌 ' if c['id'] == st.session_state.conversation_id else ''}{label}",
                key=f"conv_{c['id']}",
                use_container_width=True,
            ):
                st.session_state.conversation_id = c["id"]
                st.rerun()

        if st.session_state.conversation_id:
            if st.sidebar.button("🗑️ 删除当前对话", use_container_width=True):
                delete_conversation(st.session_state.user_id, st.session_state.conversation_id)
                st.session_state.conversation_id = None
                st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("退出登录", use_container_width=True):
        logout()
        st.rerun()


def render_settings():
    st.header("⚙️ API 配置")
    st.caption("每位用户独立配置，数据互不影响")

    cfg = get_user_api_config(st.session_state.user_id)

    api_key = st.text_input("OPENAI_API_KEY", value=cfg.api_key, type="password")
    base_url = st.text_input("OPENAI_BASE_URL", value=cfg.base_url)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("刷新模型列表", use_container_width=True):
            models, err = fetch_available_models(api_key, base_url)
            st.session_state.model_options = models
            st.session_state.model_fetch_error = err

    if not st.session_state.model_options:
        models, err = fetch_available_models(api_key, base_url)
        st.session_state.model_options = models
        st.session_state.model_fetch_error = err

    if st.session_state.model_fetch_error:
        st.warning(st.session_state.model_fetch_error)

    model_options = st.session_state.model_options
    current_index = model_options.index(cfg.model) if cfg.model in model_options else 0
    model = st.selectbox("OPENAI_MODEL", options=model_options, index=current_index)

    if st.button("保存配置", type="primary"):
        save_user_api_config(st.session_state.user_id, api_key, base_url, model)
        st.success("配置已保存")
        st.session_state.model_options = []
        st.rerun()


def render_stats():
    st.header("📊 Token 成本统计")

    summary = get_user_token_summary(st.session_state.user_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总 Token", f"{summary['total_tokens']:,}")
    c2.metric("输入 Token", f"{summary['prompt_tokens']:,}")
    c3.metric("输出 Token", f"{summary['completion_tokens']:,}")
    c4.metric("预估成本", f"¥{summary['estimated_cost']:.4f}")

    st.subheader("按模型统计")
    by_model = get_user_token_by_model(st.session_state.user_id)
    if by_model:
        st.dataframe(by_model, use_container_width=True)
    else:
        st.info("暂无使用记录")

    st.subheader("最近请求")
    recent = get_recent_usage(st.session_state.user_id)
    if recent:
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("暂无使用记录")


def render_chat():
    if not is_api_configured(st.session_state.user_id):
        st.warning("请先在「API 设置」中配置 API Key、Base URL 和模型")
        return

    if st.session_state.conversation_id is None:
        convs = list_conversations(st.session_state.user_id)
        if convs:
            st.session_state.conversation_id = convs[0]["id"]
        else:
            st.session_state.conversation_id = create_conversation(st.session_state.user_id)

    conv_id = st.session_state.conversation_id
    messages = get_messages(conv_id)

    st.subheader("💬 对话")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("输入消息..."):
        cfg = get_user_api_config(st.session_state.user_id)
        add_message(conv_id, "user", prompt)

        # 首条消息自动设为对话标题
        if len(messages) == 0:
            title = prompt[:30] + ("…" if len(prompt) > 30 else "")
            update_conversation_title(st.session_state.user_id, conv_id, title)

        history = messages_to_chat_history(messages)

        with st.spinner("思考中..."):
            try:
                reply, usage = run_agent(prompt, cfg, chat_history=history, verbose=False)
            except Exception as e:
                reply = f"调用失败: {e}"
                usage = None

        add_message(conv_id, "assistant", reply)

        if usage and usage.total_tokens > 0:
            record_token_usage(
                st.session_state.user_id,
                conv_id,
                cfg.model,
                usage.prompt_tokens,
                usage.completion_tokens,
            )

        st.rerun()


def main():
    if st.session_state.user_id is None:
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
