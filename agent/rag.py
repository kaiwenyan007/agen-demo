"""
RAG（检索增强生成）模块 —— 让 Agent 能「查资料再回答」。

知识来源：
  - 项目公共库：knowledge/（可选）
  - 用户本机目录：Web 配置的路径（如 C:\\Users\\xxx\\notes，本机 Streamlit 可读）

向量索引按用户隔离：.chroma/users/{user_id}/；CLI 无 user_id 时用 .chroma/
"""

import os
import re
import shutil
from pathlib import Path

from agent.rag_context import get_rag_context
from db.rag_stats import record_chroma_event, record_rag_query
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CHROMA_DIR = PROJECT_ROOT / ".chroma"

_embeddings: Embeddings | None = None
_vectorstores: dict[str, Chroma] = {}
_keyword_chunks_map: dict[str, list[Document]] = {}
_use_keyword_fallback = False

_RECOVERABLE_ERRORS = (
    ImportError,
    OSError,
    RuntimeError,
    ValueError,
    ConnectionError,
    TimeoutError,
)


def _scope_key(user_id: int | None) -> str:
    return f"user:{user_id}" if user_id is not None else "global"


def user_chroma_dir(user_id: int) -> Path:
    return CHROMA_DIR / "users" / str(user_id)


def _chroma_dir_for_scope(user_id: int | None) -> Path:
    return user_chroma_dir(user_id) if user_id is not None else CHROMA_DIR


def _vectorstore_chunk_count(vs: Chroma) -> int:
    """返回向量库中的 chunk 数量（使用 Chroma 公开 API，避免访问 _collection）。"""
    return len(vs.get(include=[])["ids"])


def get_knowledge_dirs(user_id: int | None = None) -> list[Path]:
    """解析当前 scope 应索引的 md 目录列表。"""
    dirs: list[Path] = []
    if user_id is not None:
        from db.user_knowledge import get_user_knowledge_config, validate_knowledge_path

        cfg = get_user_knowledge_config(user_id)
        if cfg.knowledge_dir.strip():
            ok, resolved = validate_knowledge_path(cfg.knowledge_dir)
            if ok:
                dirs.append(Path(resolved))
        if cfg.include_project and KNOWLEDGE_DIR.is_dir():
            dirs.append(KNOWLEDGE_DIR)
    elif KNOWLEDGE_DIR.is_dir():
        dirs.append(KNOWLEDGE_DIR)
    return dirs


def _resolve_local_model_path(raw_path: str) -> str | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve()) if path.is_dir() else None


class _LazyEmbeddings(Embeddings):
    def __init__(self, loader=None):
        self._loader = loader or get_embeddings
        self._inner: Embeddings | None = None

    def _get(self) -> Embeddings:
        if self._inner is None:
            self._inner = self._loader()
        return self._inner

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._get().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._get().embed_query(text)


class _KeywordEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vectorize(text)

    @staticmethod
    def _vectorize(text: str) -> list[float]:
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower())
        if not tokens:
            return [0.0]
        bucket_count = 64
        vec = [0.0] * bucket_count
        for token in tokens:
            vec[hash(token) % bucket_count] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


def _load_documents(dirs: list[Path] | None = None) -> list[Document]:
    dirs = dirs or get_knowledge_dirs(None)
    if not dirs:
        raise FileNotFoundError("未配置任何知识库目录")

    all_docs: list[Document] = []
    for directory in dirs:
        loader = DirectoryLoader(
            str(directory),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        try:
            docs = loader.load()
        except _RECOVERABLE_ERRORS:
            continue
        for doc in docs:
            doc.metadata.setdefault("source", doc.metadata.get("source", str(directory)))
            doc.metadata["knowledge_root"] = str(directory)
        all_docs.extend(docs)

    if not all_docs:
        raise FileNotFoundError(f"知识库目录中没有 .md 文件: {[str(d) for d in dirs]}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_documents(all_docs)


def _ensure_keyword_chunks(user_id: int | None = None) -> list[Document]:
    key = _scope_key(user_id)
    if key not in _keyword_chunks_map:
        _keyword_chunks_map[key] = _load_documents(get_knowledge_dirs(user_id))
    return _keyword_chunks_map[key]


def get_embeddings() -> Embeddings:
    global _embeddings, _use_keyword_fallback
    if _embeddings is not None:
        return _embeddings

    if os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings

    if os.getenv("USE_LOCAL_EMBEDDING", "0") == "1":
        from langchain_huggingface import HuggingFaceEmbeddings

        model_path = _resolve_local_model_path(
            os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
        )
        if not model_path:
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
            try:
                from modelscope import snapshot_download

                model_path = snapshot_download(
                    model_name,
                    cache_dir=str(PROJECT_ROOT / "models"),
                )
            except _RECOVERABLE_ERRORS:
                os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
                model_path = model_name

        _embeddings = HuggingFaceEmbeddings(model_name=model_path)
        return _embeddings

    try:
        _embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return _embeddings
    except _RECOVERABLE_ERRORS:
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings


def reset_vectorstore(user_id: int | None = None) -> None:
    """清空指定 scope 的向量库与内存缓存。"""
    global _embeddings, _use_keyword_fallback
    key = _scope_key(user_id)
    _vectorstores.pop(key, None)
    _keyword_chunks_map.pop(key, None)

    chroma_path = _chroma_dir_for_scope(user_id)
    if chroma_path.exists():
        shutil.rmtree(chroma_path)

    if user_id is None:
        _embeddings = None
        _use_keyword_fallback = False


def build_vectorstore(user_id: int | None = None, force_rebuild: bool = False) -> Chroma:
    key = _scope_key(user_id)
    chroma_path = _chroma_dir_for_scope(user_id)

    if force_rebuild:
        reset_vectorstore(user_id)

    if key in _vectorstores:
        record_chroma_event("memory_hit")
        return _vectorstores[key]

    if chroma_path.exists() and not force_rebuild:
        try:
            vs = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=_LazyEmbeddings(),
            )
            if _vectorstore_chunk_count(vs) > 0:
                _vectorstores[key] = vs
                record_chroma_event("disk_hit")
                return vs
        except _RECOVERABLE_ERRORS:
            _vectorstores.pop(key, None)
            if chroma_path.exists():
                shutil.rmtree(chroma_path)

    dirs = get_knowledge_dirs(user_id)
    chunks = _load_documents(dirs)
    _keyword_chunks_map[key] = chunks
    embeddings = get_embeddings()
    chroma_path.parent.mkdir(parents=True, exist_ok=True)
    vs = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=str(chroma_path),
    )
    _vectorstores[key] = vs
    record_chroma_event("rebuild")

    if user_id is not None:
        from db.user_knowledge import count_md_files, update_index_stats

        doc_count = count_md_files(*dirs)
        update_index_stats(user_id, doc_count, _vectorstore_chunk_count(vs))

    return vs


def _keyword_search(query: str, k: int = 3, user_id: int | None = None) -> list[Document]:
    chunks = _ensure_keyword_chunks(user_id)
    query_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", query.lower()))
    scored: list[tuple[int, Document]] = []
    for doc in chunks:
        text_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", doc.page_content.lower()))
        score = len(query_tokens & text_tokens)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:k]]


def search_knowledge(query: str, k: int = 3) -> str:
    ctx = get_rag_context()
    user_id = ctx.user_id if ctx else None

    dirs = get_knowledge_dirs(user_id)
    if not dirs:
        return "尚未配置知识库。请在 KNOWLEDGE 页面设置本机 md 目录并点击「重建索引」。"

    if _use_keyword_fallback or os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        results = _keyword_search(query, k=k, user_id=user_id)
        search_mode = "keyword"
    else:
        try:
            vs = build_vectorstore(user_id=user_id)
            results = vs.similarity_search(query, k=k)
            search_mode = "vector"
        except _RECOVERABLE_ERRORS:
            results = _keyword_search(query, k=k, user_id=user_id)
            search_mode = "keyword"

    record_rag_query(
        user_id=user_id,
        conversation_id=ctx.conversation_id if ctx else None,
        query=query,
        hit=bool(results),
        result_count=len(results),
        search_mode=search_mode,
    )

    if not results:
        return "知识库中未找到相关内容。"
    parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[片段{i} | {source}]\n{doc.page_content}")
    return "\n\n".join(parts)


def get_knowledge_base_info(user_id: int | None = None) -> dict:
    dirs = get_knowledge_dirs(user_id)
    from db.user_knowledge import count_md_files

    md_count = count_md_files(*dirs) if dirs else 0
    chunk_count = 0
    chroma_path = _chroma_dir_for_scope(user_id)
    try:
        vs = build_vectorstore(user_id=user_id)
        chunk_count = _vectorstore_chunk_count(vs)
    except _RECOVERABLE_ERRORS:
        pass
    return {
        "doc_count": md_count,
        "chunk_count": chunk_count,
        "chroma_ready": chroma_path.exists() and chunk_count > 0,
        "source_dirs": [str(d) for d in dirs],
    }
