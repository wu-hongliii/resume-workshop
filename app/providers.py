from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    name: str
    adapter: str
    base_url: str
    model: str
    key_required: bool = True
    live_tested: bool = False


PROVIDERS: dict[str, ProviderDefinition] = {
    "deepseek": ProviderDefinition(
        "deepseek", "DeepSeek", "openai", "https://api.deepseek.com", "deepseek-v4-flash", live_tested=True
    ),
    "openai": ProviderDefinition(
        "openai", "OpenAI", "openai", "https://api.openai.com/v1", "gpt-5.2"
    ),
    "anthropic": ProviderDefinition(
        "anthropic", "Anthropic Claude", "anthropic", "https://api.anthropic.com", "claude-sonnet-5"
    ),
    "minimax": ProviderDefinition(
        "minimax", "MiniMax", "openai", "https://api.minimaxi.com/v1", "MiniMax-M2.7"
    ),
    "glm": ProviderDefinition(
        "glm", "智谱 GLM", "openai", "https://open.bigmodel.cn/api/paas/v4", "glm-5.2"
    ),
    "kimi": ProviderDefinition(
        "kimi", "Moonshot Kimi", "openai", "https://api.moonshot.cn/v1", "kimi-k2.6"
    ),
    "mimo": ProviderDefinition(
        "mimo", "小米 MiMo", "openai", "https://api.xiaomimimo.com/v1", "mimo-v2.5-pro"
    ),
    "ollama": ProviderDefinition(
        "ollama", "Ollama（本地）", "openai", "http://127.0.0.1:11434/v1", "qwen3:8b", key_required=False
    ),
    "lmstudio": ProviderDefinition(
        "lmstudio", "LM Studio（本地）", "openai", "http://127.0.0.1:1234/v1", "", key_required=False
    ),
    "custom": ProviderDefinition(
        "custom", "自定义 OpenAI 兼容接口", "openai", "", ""
    ),
}


class ProviderError(RuntimeError):
    pass


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def public_provider_options() -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "adapter": item.adapter,
            "default_base_url": item.base_url,
            "default_model": item.model,
            "key_required": item.key_required,
            "live_tested": item.live_tested,
        }
        for item in PROVIDERS.values()
    ]


def normalize_config(config: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(config, str):
        config = {"provider": "deepseek", "api_key": config}
    provider_id = str(config.get("provider") or "deepseek")
    definition = PROVIDERS.get(provider_id)
    if not definition:
        raise ProviderError("不支持的 AI 服务商")
    base_url = str(config.get("base_url") or definition.base_url).strip().rstrip("/")
    model = str(config.get("model") or definition.model).strip()
    api_key = str(config.get("api_key") or "").strip()
    if not base_url:
        raise ProviderError("请填写 API Base URL")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ProviderError("API Base URL 必须是有效的 http/https 地址，且不能包含账号或密码")
    if parsed.scheme != "https" and not _is_loopback_host(parsed.hostname):
        raise ProviderError("非本机 API 地址必须使用 HTTPS，避免密钥和简历内容被明文传输")
    if not model:
        raise ProviderError("请填写模型名称")
    if definition.key_required and not api_key:
        raise ProviderError(f"请先在设置中填写 {definition.name} API Key")
    return {
        "provider": provider_id,
        "name": definition.name,
        "adapter": definition.adapter,
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "key_required": definition.key_required,
    }


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error", payload) if isinstance(payload, dict) else payload
        if isinstance(error, dict):
            return str(error.get("message") or error.get("msg") or response.text)
        return str(error)
    except Exception:
        return response.text


async def request_completion(config: dict[str, Any] | str, request: dict[str, Any]) -> dict[str, Any]:
    resolved = normalize_config(config)
    if resolved["adapter"] == "anthropic":
        return await _request_anthropic(resolved, request)
    return await _request_openai_compatible(resolved, request)


async def _request_openai_compatible(config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    body = dict(request)
    body["model"] = config["model"]
    if config["provider"] != "deepseek":
        body.pop("thinking", None)
    if config["provider"] in {"ollama", "lmstudio", "custom"}:
        body.pop("response_format", None)
    if config["provider"] in {"openai", "mimo"} and "max_tokens" in body:
        body["max_completion_tokens"] = body.pop("max_tokens")
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        if config["provider"] == "mimo":
            headers["api-key"] = config["api_key"]
        else:
            headers["Authorization"] = f"Bearer {config['api_key']}"
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{config['base_url']}/chat/completions", headers=headers, json=body
            )
    except httpx.HTTPError as exc:
        raise ProviderError(f"无法连接 {config['name']}：{exc}") from exc
    if response.status_code >= 400:
        raise ProviderError(
            f"{config['name']} 返回错误（{response.status_code}）：{_error_message(response)[:300]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise ProviderError(f"{config['name']} 返回了无法识别的响应")
    return payload


async def _request_anthropic(config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": config["model"],
        "max_tokens": request.get("max_tokens", 12000),
        "system": next(
            (item.get("content", "") for item in request.get("messages", []) if item.get("role") == "system"),
            "",
        ),
        "messages": [item for item in request.get("messages", []) if item.get("role") != "system"],
    }
    if "temperature" in request:
        body["temperature"] = request["temperature"]
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
    }
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{config['base_url']}/v1/messages", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ProviderError(f"无法连接 {config['name']}：{exc}") from exc
    if response.status_code >= 400:
        raise ProviderError(
            f"{config['name']} 返回错误（{response.status_code}）：{_error_message(response)[:300]}"
        )
    payload = response.json()
    content = "".join(
        str(item.get("text") or "")
        for item in payload.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    )
    return {
        "choices": [{"message": {"content": content}, "finish_reason": payload.get("stop_reason")}],
        "usage": payload.get("usage", {}),
        "model": payload.get("model", config["model"]),
    }


async def test_connection(config: dict[str, Any] | str) -> dict[str, Any]:
    resolved = normalize_config(config)
    response = await request_completion(
        resolved,
        {
            "model": resolved["model"],
            "temperature": 0,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "请只回复 OK"}],
        },
    )
    choices = response.get("choices") or []
    content = str(((choices[0].get("message") or {}).get("content") or "")).strip() if choices else ""
    if not content:
        raise ProviderError(f"{resolved['name']} 已连接，但没有返回文本")
    return {"ok": True, "provider": resolved["provider"], "name": resolved["name"], "model": resolved["model"]}
