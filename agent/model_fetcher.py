"""根据用户的 API Key 和 Base URL 动态获取可用模型列表。"""

import httpx

# 各服务商常见模型（API 拉取失败时的回退）
FALLBACK_MODELS: dict[str, list[str]] = {
    "api.deepseek.com": ["deepseek-chat", "deepseek-reasoner"],
    "api.openai.com": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "dashscope.aliyuncs.com": [
        "qwen-turbo", "qwen-plus", "qwen-max", "qwen-long",
    ],
}


def _fallback_for_base_url(base_url: str) -> list[str]:
    base = base_url.lower().rstrip("/")
    for host, models in FALLBACK_MODELS.items():
        if host in base:
            return models
    return ["deepseek-chat", "gpt-4o-mini"]


def fetch_available_models(api_key: str, base_url: str, timeout: float = 10.0) -> tuple[list[str], str | None]:
    """
    调用 OpenAI 兼容的 GET /v1/models 接口。
    返回 (模型列表, 错误信息)。
    """
    if not api_key or not base_url:
        return _fallback_for_base_url(base_url or ""), "请先填写 API Key 和 Base URL"

    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code == 401:
            return _fallback_for_base_url(base_url), "API Key 无效，已显示默认模型列表"
        if resp.status_code != 200:
            return _fallback_for_base_url(base_url), f"拉取模型失败 ({resp.status_code})，已显示默认列表"

        data = resp.json()
        models = []
        for item in data.get("data", []):
            model_id = item.get("id", "")
            if model_id and not model_id.startswith("ft:"):
                models.append(model_id)

        if not models:
            return _fallback_for_base_url(base_url), "未获取到模型，已显示默认列表"

        # 过滤 embedding 类模型，保留对话模型
        chat_models = [m for m in models if "embed" not in m.lower()]
        return sorted(chat_models or models), None

    except httpx.TimeoutException:
        return _fallback_for_base_url(base_url), "请求超时，已显示默认模型列表"
    except Exception as e:
        return _fallback_for_base_url(base_url), f"网络错误: {e}，已显示默认列表"
