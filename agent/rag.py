"""
RAG（检索增强生成）模块 —— 让 Agent 能「查资料再回答」。

整体流程：
  1. 读取 knowledge/ 目录下的 Markdown 文档
  2. 把长文档切成小块（chunk）
  3. 用 Embedding 模型把每块文字变成向量（一串数字）
  4. 向量存入 Chroma 本地数据库（.chroma/ 目录）
  5. 用户提问时，把问题也变成向量，在 Chroma 里找最相似的片段
  6. 把找到的片段返回给 Agent，作为回答依据

对外主要接口：
  - build_vectorstore()  构建或加载向量库（程序启动时调用）
  - search_knowledge()   根据问题检索知识库（Agent 工具内部调用）
  - reset_vectorstore()  清空向量库（/reindex 重建时内部使用）
"""

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

# 从项目根目录的 .env 文件读取 API Key 等配置
load_dotenv()

# ── 路径常量 ──────────────────────────────────────────────────────────
# Path(__file__) 是当前文件路径；.parent.parent 向上两级 = 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"   # 原始 Markdown 文档所在目录
CHROMA_DIR = PROJECT_ROOT / ".chroma"        # Chroma 向量库持久化目录（已在 .gitignore 中）

# ── 模块级缓存（单例模式）────────────────────────────────────────────
# 这些变量在进程内只初始化一次，避免重复加载模型或重复连接数据库
_embeddings: Embeddings | None = None          # Embedding 模型实例
_vectorstore: Chroma | None = None             # Chroma 向量库实例
_keyword_chunks: list[Document] | None = None   # 文档切块缓存（关键词回退模式用）
_use_keyword_fallback = False                    # 是否已切换到关键词检索（无 Embedding API 时）

# 降级回退时捕获的可预期异常（网络、依赖缺失、索引损坏等），避免裸 except Exception
_RECOVERABLE_ERRORS = (
    ImportError,
    OSError,
    RuntimeError,
    ValueError,
    ConnectionError,
    TimeoutError,
)


class _KeywordEmbeddings(Embeddings):
    """
    简易 Embedding 回退方案（不需要联网、不需要 GPU）。

    正常 RAG 用神经网络把文字映射成高维语义向量；
    这里用「词频哈希」做一个粗糙替代品，仅用于 Demo / 离线调试。
    类名前缀 _ 表示仅供本模块内部使用，外部不应直接调用。
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量把多段文字转成向量（建索引时用）。"""
        return [self._vectorize(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """把单条查询转成向量（搜索时用）。"""
        return self._vectorize(text)

    @staticmethod
    def _vectorize(text: str) -> list[float]:
        """
        把一段文字变成一个 64 维向量：
          - 用正则提取中文词和英文单词
          - 每个词 hash 到 0~63 的某个「桶」，计数 +1
          - 最后归一化，使向量长度为 1
        """
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
    """
    从 knowledge/ 目录加载所有 .md 文件，并切分成小块。

    为什么要切块？
      整篇文档太长，Embedding 和检索都不精准；
      切成小块后，可以只返回与问题最相关的段落。

    返回的每个 Document 包含：
      - page_content: 文本内容
      - metadata: 元数据（如 source=文件路径）
    """
    loader = DirectoryLoader(
        str(KNOWLEDGE_DIR),
        glob="**/*.md",                          # 递归匹配所有 .md 文件
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        raise FileNotFoundError(f"知识库目录为空: {KNOWLEDGE_DIR}")

    # chunk_size=500  每块约 500 字符
    # chunk_overlap=50 相邻块重叠 50 字符，避免句子被截断在边界处
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_documents(docs)


def get_embeddings() -> Embeddings:
    """
    获取 Embedding 模型（只创建一次，之后复用）。

    优先级（可通过 .env 控制）：
      1. USE_KEYWORD_FALLBACK=1  → 简易词频向量（完全离线）
      2. USE_LOCAL_EMBEDDING=1   → 本地 HuggingFace 模型（如 bge-small-zh）
      3. 默认                    → OpenAI 兼容 API（需 OPENAI_API_KEY）
      4. API 失败                → 自动降级到关键词回退
    """
    global _embeddings, _use_keyword_fallback
    if _embeddings is not None:
        return _embeddings

    # 模式 1：显式要求关键词回退
    if os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings

    # 模式 2：本地 Embedding 模型（适合没有 Embedding API 或想离线运行）
    if os.getenv("USE_LOCAL_EMBEDDING", "0") == "1":
        from langchain_huggingface import HuggingFaceEmbeddings

        model_path = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
        if not model_path:
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
            # 优先从 ModelScope 下载（国内网络更稳定）
            try:
                from modelscope import snapshot_download

                model_path = snapshot_download(
                    model_name,
                    cache_dir=str(PROJECT_ROOT / "models"),
                )
            except _RECOVERABLE_ERRORS:
                # ModelScope 未安装或下载失败时，走 HuggingFace 镜像
                os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
                model_path = model_name

        _embeddings = HuggingFaceEmbeddings(model_name=model_path)
        return _embeddings

    # 模式 3：OpenAI 兼容 Embedding API（默认）
    try:
        _embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return _embeddings
    except _RECOVERABLE_ERRORS:
        # 模式 4：API 不可用时自动降级
        _use_keyword_fallback = True
        _embeddings = _KeywordEmbeddings()
        return _embeddings


def reset_vectorstore() -> None:
    """
    彻底清空向量库：删除 .chroma/ 目录并重置内存缓存。

    调用时机：用户执行 /reindex 且 force_rebuild=True 时。
    注意：修改 knowledge/ 下的文档后，需要重建索引才能生效。
    """
    global _vectorstore, _embeddings, _keyword_chunks, _use_keyword_fallback
    _vectorstore = None
    _embeddings = None
    _keyword_chunks = None
    _use_keyword_fallback = False
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)  # 递归删除整个 .chroma/ 文件夹


def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    """
    构建或加载 Chroma 向量库（核心入口）。

    逻辑分支：
      force_rebuild=True  → 先 reset，再全量重建
      内存已有实例        → 直接返回（避免重复初始化）
      .chroma/ 存在且有效  → 从磁盘加载，跳过 Embedding（启动快）
      否则                → 读文档 → 切分 → 向量化 → 写入 .chroma/

    参数：
      force_rebuild  是否强制重建（/reindex 命令传入 True）

    返回：
      Chroma 实例，可用于 similarity_search() 等检索操作
    """
    global _vectorstore, _keyword_chunks
    if force_rebuild:
        reset_vectorstore()

    # 进程内已有实例，直接复用
    if _vectorstore is not None:
        return _vectorstore

    # 始终加载文档切块（关键词回退模式也需要）
    chunks = _load_documents()
    _keyword_chunks = chunks
    embeddings = get_embeddings()

    # 尝试从磁盘加载已有索引（避免每次启动都重新 Embedding）
    if CHROMA_DIR.exists() and not force_rebuild:
        try:
            _vectorstore = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=embeddings,  # 查询时仍需要 Embedding 模型
            )
            # count() > 0 确保不是空目录被误判为「已有索引」
            if _vectorstore._collection.count() > 0:
                return _vectorstore
        except _RECOVERABLE_ERRORS:
            # 索引文件损坏时，删掉重建
            if CHROMA_DIR.exists():
                shutil.rmtree(CHROMA_DIR)

    # 全量建索引：文档切块 → 向量化 → 持久化到 .chroma/
    _vectorstore = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    return _vectorstore


def _keyword_search(query: str, k: int = 3) -> list[Document]:
    """
    关键词匹配检索（Embedding 不可用时的回退方案）。

    原理：统计问题和文档片段中「共同出现的关键词」数量，
    共同词越多，认为越相关。不如向量语义搜索精准，但零依赖。

    参数：
      query  用户问题
      k      返回最相关的前 k 个片段（默认 3）
    """
    chunks = _keyword_chunks or _load_documents()
    query_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", query.lower()))
    scored: list[tuple[int, Document]] = []
    for doc in chunks:
        text_tokens = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", doc.page_content.lower()))
        score = len(query_tokens & text_tokens)  # 集合交集 = 共同关键词数
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)  # 按分数从高到低排序
    return [doc for _, doc in scored[:k]]


def search_knowledge(query: str, k: int = 3) -> str:
    """
    根据用户问题检索知识库，返回格式化的文本片段。

    这是 Agent 工具 query_knowledge_base 的底层实现：
      LangChain Agent 决定调用工具 → 工具调用此函数 → 返回检索结果给 LLM

    参数：
      query  用户的问题，如「什么是 ReAct？」
      k      返回片段数量，默认 3

    返回：
      多段文本，每段标注序号和来源文件；无结果时返回提示语
    """
    if _use_keyword_fallback or os.getenv("USE_KEYWORD_FALLBACK", "0") == "1":
        # 关键词模式：不访问 Chroma，直接在内存中的 chunks 里匹配
        results = _keyword_search(query, k=k)
    else:
        try:
            vs = build_vectorstore()
            # 把问题向量化，在 Chroma 中找余弦距离最近的 k 个片段
            results = vs.similarity_search(query, k=k)
        except _RECOVERABLE_ERRORS:
            # 向量检索失败（如 API 超时），降级到关键词匹配
            results = _keyword_search(query, k=k)

    if not results:
        return "知识库中未找到相关内容。"
    parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[片段{i} | {source}]\n{doc.page_content}")
    return "\n\n".join(parts)
