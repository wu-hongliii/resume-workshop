from __future__ import annotations

import asyncio
import hashlib
import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx

from . import storage


DIRECT_COURSES = (
    {"title": "Python语言程序设计", "platform": "中国大学 MOOC", "url": "https://www.icourse163.org/course/detail.htm?cid=268001", "tags": ("python", "编程基础", "程序设计", "零基础", "脚本")},
    {"title": "用Python学人工智能", "platform": "国家高等教育智慧教育平台", "url": "https://higher.smartedu.cn/course/68c0987da9f4619f8f00c004", "tags": ("python", "人工智能", "机器学习", "agent", "智能体")},
    {"title": "桥梁工程 I", "platform": "国家高等教育智慧教育平台", "url": "https://higher.smartedu.cn/course/69a20dea95df98bb276c9fe6", "tags": ("桥梁工程", "桥梁设计", "市政桥涵", "土木工程", "结构设计")},
    {"title": "Python 零基础系统入门教程", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1QUCCBDEAC/", "tags": ("python", "编程基础", "数据处理", "脚本")},
    {"title": "Python 数据分析：NumPy、Pandas、Matplotlib", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1hx411d7jb/", "tags": ("python", "数据分析", "pandas", "numpy", "matplotlib", "csv")},
    {"title": "LangChain、RAG 与 Agent 实战教程", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1rv7A6oEeP/", "tags": ("langchain", "rag", "agent", "智能体", "知识库", "大模型应用")},
    {"title": "AI Agent 从基础到项目实战", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1k4w4ziEyu/", "tags": ("agent", "智能体", "ai 工具链", "大模型应用", "自动化流程")},
    {"title": "FastAPI 从入门到实战", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1zV2QBtE39/", "tags": ("fastapi", "python web", "后端", "api", "系统开发", "接口")},
    {"title": "Git 与 GitHub 基础全套教程", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1pW411A7a5/", "tags": ("git", "github", "版本控制", "代码管理", "项目交付")},
    {"title": "Docker 从零开始系统教程", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1ba411j7u1/", "tags": ("docker", "容器", "部署", "devops", "系统交付")},
    {"title": "零基础学 SQL", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1cJ41167iG/", "tags": ("sql", "数据库", "数据查询", "mysql", "数据分析")},
    {"title": "如何讲清楚简历中的项目与项目亮点", "platform": "哔哩哔哩", "url": "https://www.bilibili.com/video/BV1EE411T7HF/", "tags": ("项目打磨", "项目介绍", "项目亮点", "面试准备", "项目经验", "简历项目")},
)

SEARCH_DOMAINS = ["bilibili.com", "icourse163.org", "xuetangx.com", "imooc.com", "higher.smartedu.cn"]
NON_BILIBILI_DOMAINS = [domain for domain in SEARCH_DOMAINS if domain != "bilibili.com"]


def _clean_title(value: str) -> str:
    title = re.sub(r"<[^>]+>", "", value).strip()
    return re.sub(r"\s+", " ", title)[:180]


def _normalize_direct_url(url: str) -> tuple[str, str] | None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    path = parsed.path
    if host in {"www.bilibili.com", "bilibili.com"}:
        match = re.fullmatch(r"/video/(BV[0-9A-Za-z]+|av[0-9]+)/?", path)
        return (f"https://www.bilibili.com/video/{match.group(1)}/", "哔哩哔哩") if match else None
    if host in {"www.icourse163.org", "icourse163.org"} and "/course/" in path:
        return (urllib.parse.urlunparse(("https", host, path, "", "", "")), "中国大学 MOOC")
    if host in {"www.xuetangx.com", "xuetangx.com"} and "/course/" in path:
        return (urllib.parse.urlunparse(("https", host, path, "", "", "")), "学堂在线")
    if host in {"www.imooc.com", "imooc.com"} and re.match(r"^/(learn|course)/", path):
        return (urllib.parse.urlunparse(("https", host, path, "", "", "")), "慕课网")
    if host == "higher.smartedu.cn" and re.fullmatch(r"/course/[0-9A-Za-z]+/?", path):
        return (urllib.parse.urlunparse(("https", host, path.rstrip("/"), "", "", "")), "国家高等教育智慧教育平台")
    return None


def is_supported_direct_url(url: str) -> bool:
    return _normalize_direct_url(url) is not None


def _direct_resource(title: str, url: str, description: str = "") -> dict[str, str] | None:
    normalized = _normalize_direct_url(url)
    if not normalized:
        return None
    direct_url, platform = normalized
    clean_title = _clean_title(title)
    if not clean_title:
        return None
    return {
        "title": clean_title,
        "platform": platform,
        "url": direct_url,
        "kind": "具体课程或视频",
        "description": re.sub(r"\s+", " ", description).strip()[:500],
        "verified_at": datetime.now(timezone.utc).date().isoformat(),
    }


def _stage_text(stage: dict[str, Any]) -> str:
    keywords = stage.get("keywords") if isinstance(stage.get("keywords"), list) else []
    fields = [stage.get("title", ""), stage.get("goal", ""), stage.get("deliverable", ""), *keywords]
    return " ".join(str(value).strip().lower() for value in fields if str(value).strip())


def find_direct_resources(stage: dict[str, Any], limit: int = 3) -> list[dict[str, str]]:
    text = _stage_text(stage)
    ranked: list[tuple[int, int, dict[str, str]]] = []
    for index, course in enumerate(DIRECT_COURSES):
        score = sum(1 for tag in course["tags"] if tag.lower() in text)
        if score:
            resource = _direct_resource(course["title"], course["url"])
            if resource:
                resource["source"] = "内置已核验目录"
                ranked.append((score, -index, resource))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


def diversify_resources(resources: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    """Round-robin platforms while preserving relevance order within each platform."""
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for resource in resources:
        platform = str(resource.get("platform") or "其他平台")
        if platform not in groups:
            groups[platform] = []
            order.append(platform)
        groups[platform].append(resource)
    diversified: list[dict[str, Any]] = []
    while any(groups.values()):
        for platform in order:
            if groups[platform]:
                diversified.append(groups[platform].pop(0))
                if limit is not None and len(diversified) >= limit:
                    return diversified
    return diversified


def finalize_resource_pools(result: dict[str, Any]) -> dict[str, Any]:
    for stage in result.get("stages", []):
        pool = stage.get("resource_pool") if isinstance(stage.get("resource_pool"), list) else stage.get("resources", [])
        diversified = diversify_resources(pool)
        stage["resource_pool"] = diversified
        stage["resources"] = diversified[:3]
        stage["resource_offset"] = 0
    return result


def _search_query(stage: dict[str, Any]) -> str:
    keywords = stage.get("keywords") if isinstance(stage.get("keywords"), list) else []
    terms = [str(value).strip() for value in keywords[:3] if str(value).strip()]
    if not terms:
        terms = [str(stage.get("title", "")).strip()]
    return " ".join(terms) + " 中文 系统教程 入门 实战"


async def _search_tavily(client: httpx.AsyncClient, api_key: str, query: str, domains: list[str] | None = None) -> list[dict[str, Any]]:
    response = await client.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "search_depth": "basic", "max_results": 10, "include_domains": domains or SEARCH_DOMAINS, "include_answer": False},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("results", []) if isinstance(data.get("results"), list) else []


async def _search_brave(client: httpx.AsyncClient, api_key: str, query: str, domains: list[str] | None = None) -> list[dict[str, Any]]:
    sites = " OR ".join(f"site:{domain}" for domain in (domains or SEARCH_DOMAINS))
    response = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        params={"q": f"{query} ({sites})", "count": 10, "search_lang": "zh-hans", "country": "CN", "safesearch": "strict"},
    )
    response.raise_for_status()
    data = response.json().get("web", {})
    return data.get("results", []) if isinstance(data.get("results"), list) else []


def _cache_key(provider: str, stage: dict[str, Any]) -> str:
    value = "diverse-v2\n" + provider + "\n" + _stage_text(stage)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _find_remote_resources(client: httpx.AsyncClient, provider: str, api_key: str, stage: dict[str, Any]) -> list[dict[str, Any]]:
    key = _cache_key(provider, stage)
    cached = storage.get_learning_resource_cache(key)
    if cached is not None:
        return cached
    query = _search_query(stage)
    search = _search_tavily if provider == "tavily" else _search_brave
    broad, non_bilibili = await asyncio.gather(
        search(client, api_key, query, SEARCH_DOMAINS),
        search(client, api_key, query, NON_BILIBILI_DOMAINS),
    )
    raw = [*broad, *non_bilibili]
    resources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        resource = _direct_resource(
            str(item.get("title", "")), str(item.get("url", "")), str(item.get("content") or item.get("description") or ""),
        )
        if resource and resource["url"] not in seen:
            resource["source"] = "实时公开检索"
            resources.append(resource)
            seen.add(resource["url"])
    resources = diversify_resources(resources, 12)
    storage.set_learning_resource_cache(key, resources)
    return resources


async def attach_direct_resources(
    result: dict[str, Any], provider: str = "", api_key: str = ""
) -> dict[str, Any]:
    stages = result.get("stages") if isinstance(result.get("stages"), list) else []
    remote_batches: list[Any] = [[] for _ in stages]
    search_error = ""
    if provider in {"brave", "tavily"} and api_key:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                remote_batches = await asyncio.gather(
                    *(_find_remote_resources(client, provider, api_key, stage) for stage in stages)
                )
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            search_error = str(exc)[:180]
            remote_batches = [[] for _ in stages]
    for stage_index, (stage, remote) in enumerate(zip(stages, remote_batches)):
        combined = diversify_resources([*remote, *find_direct_resources(stage, limit=6)])
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in combined:
            if item["url"] in seen:
                continue
            feedback = storage.get_learning_resource_feedback(item["url"])
            if feedback in {"irrelevant", "broken"}:
                continue
            candidate = dict(item)
            if feedback:
                candidate["feedback"] = feedback
            candidate["candidate_id"] = f"S{stage_index + 1}R{len(unique) + 1}"
            unique.append(candidate)
            seen.add(item["url"])
        stage["resource_candidates"] = unique[:12]
        stage["resource_pool"] = [{key: value for key, value in item.items() if key != "candidate_id"} for item in unique[:9]]
        stage["resources"] = stage["resource_pool"][:3]
        stage["resource_status"] = "found" if unique else "not_found"
    if provider and api_key and not search_error:
        result["resource_note"] = "已实时检索具体课程页面，并结合当前学习阶段进行相关性审核；链接、免费状态和课程内容仍以平台当前页面为准。"
        result["resource_mode"] = "realtime"
    elif search_error:
        result["resource_note"] = "实时课程搜索暂时失败，已使用本地核验目录兜底。可检查搜索服务 Key 后重试。"
        result["resource_mode"] = "fallback"
        result["resource_error"] = search_error
    else:
        result["resource_note"] = "当前未配置课程搜索服务，仅使用本地核验目录；要覆盖任意职业，请在设置中配置 Brave Search 或 Tavily。"
        result["resource_mode"] = "curated"
    return result
