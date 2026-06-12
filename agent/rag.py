import os
import re
import shutil
from pathlib import Path

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
_vectorstore: Chroma | None = None
_keyword_chunks: list[Document] | None = None
_use_keyword_fallback = False


class _KeywordEmbeddings(Embeddings):
    """离线回退：用简单词频向量代替 Embedding API。"""

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


def _load_documents() -> list[Document]:
    loader = DirectoryLoader(
        str(KNOWLEDGE_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        raise FileNotFoundError(f"知识库目录为空: {KNOWLEDGE_DIR}")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_documents(docs)


def get_embeddings() -> Embeddings:
    global _embeddings, _use_keyword_fallback
    if _embeddings is not None:
        return _embeddings

    if os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings

    if os.getenv("USE_LOCAL_EMBEDDING", "0") == "1":
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            _embeddings = HuggingFaceEmbeddings(
                model_name=os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            )
            return _embeddings
        except Exception:
            _use_keyword_fallback = True
            _embeddings = _KeywordEmbeddings()
            return _embeddings

    try:
        _embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return _embeddings
    except Exception:
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings


def reset_vectorstore() -> None:
    global _vectorstore, _embeddings, _keyword_chunks, _use_keyword_fallback
    _vectorstore = None
    _embeddings = None
    _keyword_chunks = None
    _use_keyword_fallback = False
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)


def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    global _vectorstore, _keyword_chunks
    if force_rebuild:
        reset_vectorstore()

    if _vectorstore is not None:
        return _vectorstore

    chunks = _load_documents()
    _keyword_chunks = chunks
    embeddings = get_embeddings()

    if CHROMA_DIR.exists() and not force_rebuild:
        try:
            _vectorstore = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=embeddings,
            )
            if _vectorstore._collection.count() > 0:
                return _vectorstore
        except Exception:
            if CHROMA_DIR.exists():
                shutil.rmtree(CHROMA_DIR)

    _vectorstore = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    return _vectorstore


def _keyword_search(query: str, k: int = 3) -> list[Document]:
    chunks = _keyword_chunks or _load_documents()
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
    if _use_keyword_fallback or os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        results = _keyword_search(query, k=k)
    else:
        try:
            vs = build_vectorstore()
            results = vs.similarity_search(query, k=k)
        except Exception:
            results = _keyword_search(query, k=k)

    if not results:
        return "知识库中未找到相关内容。"
    parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[片段{i} | {source}]\n{doc.page_content}")
    return "\n\n".join(parts)
