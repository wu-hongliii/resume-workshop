from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Literal

import httpx
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import runtime

runtime.configure_packaged_environment()

from . import ai, demo_package, learning, parsers, providers, renderers, storage


WEB_DIR = runtime.RESOURCE_ROOT / "web"
APP_VERSION = "0.3.0-beta"
PUBLIC_REPOSITORY = "wu-hongliii/resume-workshop"
app = FastAPI(title="简历工坊", version=APP_VERSION, docs_url="/api/docs")
LOCAL_PORT = int(os.environ.get("RESUME_WORKSHOP_PORT", "8877"))
ALLOWED_LOCAL_ORIGINS = {f"http://127.0.0.1:{LOCAL_PORT}", f"http://localhost:{LOCAL_PORT}"}
ALLOWED_HOSTS = {f"127.0.0.1:{LOCAL_PORT}", f"localhost:{LOCAL_PORT}", "testserver"}
MAX_REQUEST_BYTES = 50 * 1024 * 1024
_packaged_log_stream = None


@app.middleware("http")
async def protect_local_boundary(request: Request, call_next):
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if host and host not in ALLOWED_HOSTS:
        return JSONResponse(status_code=403, content={"detail": "拒绝非本机来源的请求"})
    if origin and origin not in ALLOWED_LOCAL_ORIGINS:
        return JSONResponse(status_code=403, content={"detail": "拒绝其他网页操作本地简历数据"})
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": "请求内容过大"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "无效的请求长度"})
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
        "frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


class StateRequest(BaseModel):
    payload: dict[str, Any]
    version_label: str | None = Field(default=None, max_length=80)


class SettingsRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=300)
    ai_provider: str | None = Field(default=None, max_length=30)
    ai_base_url: str | None = Field(default=None, max_length=500)
    ai_model: str | None = Field(default=None, max_length=200)
    clear_ai_key: bool = False
    search_provider: Literal["", "brave", "tavily"] | None = None
    search_api_key: str | None = Field(default=None, max_length=500)


class TextRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=100_000)


class ProfileRequest(BaseModel):
    profile: dict[str, Any]
    jd: str = Field(default="", max_length=50_000)


class GenerateRequest(ProfileRequest):
    related_experience: str = Field(default="", max_length=30_000)
    generation_mode: Literal["same_direction", "career_switch"] = "same_direction"
    proficiency_level: Literal["novice", "beginner", "proficient", "expert"] = "beginner"


class QuestionRequest(ProfileRequest):
    history: list[dict[str, str]] = Field(default_factory=list)


class RefineRequest(ProfileRequest):
    question: str = Field(min_length=1, max_length=2_000)
    answer: str = Field(min_length=1, max_length=20_000)
    previous_answer: str = Field(default="", max_length=20_000)
    history: list[dict[str, str]] = Field(default_factory=list)


class SelectionEditRequest(ProfileRequest):
    path: str = Field(min_length=1, max_length=200)
    field_label: str = Field(default="", max_length=100)
    full_text: str = Field(default="", max_length=30_000)
    selected_text: str = Field(default="", max_length=20_000)
    selection_start: int = Field(default=0, ge=0, le=30_000)
    selection_end: int = Field(default=0, ge=0, le=30_000)
    instruction: str = Field(min_length=1, max_length=10_000)


class AddContentRequest(ProfileRequest):
    instruction: str = Field(min_length=1, max_length=20_000)
    mode: Literal["add", "adjust"] = "add"


class TranslationRequest(BaseModel):
    profile: dict[str, Any]
    target: str


class OCRPage(BaseModel):
    index: int = Field(ge=1, le=100)
    filename: str = Field(default="", max_length=255)
    text: str = Field(min_length=1, max_length=50_000)
    confidence: float | None = None


class OCRCorrectionRequest(BaseModel):
    pages: list[OCRPage] = Field(min_length=1, max_length=100)


class ProjectFile(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=20_000)


class ProjectCaseRequest(ProfileRequest):
    folder_name: str = Field(default="项目文件夹", max_length=255)
    files: list[ProjectFile] = Field(min_length=1, max_length=40)
    material_type: Literal[
        "software", "engineering", "finance", "research", "business",
        "content", "management", "education", "general",
    ] | None = None


class LearningPathRequest(ProfileRequest):
    analysis: dict[str, Any] = Field(default_factory=dict)


class LearningFeedbackRequest(BaseModel):
    url: str = Field(min_length=10, max_length=1000)
    verdict: Literal["useful", "irrelevant", "too_hard", "too_easy", "broken"]


@app.on_event("startup")
async def _startup() -> None:
    storage.initialize()


@app.exception_handler(ai.AIError)
async def _ai_error(_: Request, exc: ai.AIError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "name": "简历工坊", "version": APP_VERSION}


@app.get("/api/update-check")
async def update_check() -> dict[str, Any]:
    """Check the public release only after an explicit user action."""
    url = f"https://api.github.com/repos/{PUBLIC_REPOSITORY}/releases/latest"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"resume-workshop/{APP_VERSION}"}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="暂时无法连接 GitHub，请稍后重试") from exc
    if response.status_code == 404:
        return {"current": APP_VERSION, "latest": None, "update_available": False, "release_url": None}
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GitHub 返回异常状态：{response.status_code}")
    payload = response.json()
    latest = str(payload.get("tag_name", "")).lstrip("v") or None
    return {
        "current": APP_VERSION,
        "latest": latest,
        "update_available": bool(latest and latest != APP_VERSION),
        "release_url": f"https://github.com/{PUBLIC_REPOSITORY}/releases/tag/{urllib.parse.quote(str(payload.get('tag_name', '')))}",
    }


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    return storage.get_state()


@app.put("/api/state")
async def put_state(request: StateRequest) -> dict[str, bool]:
    if not isinstance(request.payload.get("profile"), dict) or not isinstance(request.payload.get("resume"), dict):
        raise HTTPException(status_code=422, detail="状态数据缺少 profile 或 resume")
    library = request.payload.get("resume_library", [])
    if not isinstance(library, list) or len(library) > 100:
        raise HTTPException(status_code=422, detail="岗位简历库数据无效或数量超过 100")
    storage.save_state(request.payload, request.version_label)
    return {"ok": True}


@app.get("/api/versions")
async def versions() -> list[dict[str, Any]]:
    return storage.list_versions()


@app.get("/api/edit-history")
async def edit_history() -> dict[str, Any]:
    return storage.get_edit_history()


@app.post("/api/versions/{version_id}/restore")
async def restore_version(version_id: int) -> dict[str, Any]:
    try:
        return storage.restore_version(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return storage.api_key_status()


@app.put("/api/settings")
async def put_settings(request: SettingsRequest) -> dict[str, Any]:
    if any(value is not None for value in (request.api_key, request.ai_provider, request.ai_base_url, request.ai_model)) or request.clear_ai_key:
        current = storage.get_ai_settings(request.ai_provider)
        try:
            storage.set_ai_settings(
                request.ai_provider or current["provider"],
                request.ai_base_url if request.ai_base_url is not None else current["base_url"],
                request.ai_model if request.ai_model is not None else current["model"],
                request.api_key if request.api_key and request.api_key.strip() else None,
                clear_api_key=request.clear_ai_key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if request.search_provider is not None or request.search_api_key is not None:
        current = storage.get_search_settings()
        storage.set_search_settings(
            request.search_provider if request.search_provider is not None else current["provider"],
            request.search_api_key if request.search_api_key is not None else current["api_key"],
        )
    return storage.api_key_status()


@app.post("/api/settings/test-ai")
async def test_ai_connection(request: SettingsRequest) -> dict[str, Any]:
    current = storage.get_ai_settings(request.ai_provider)
    config = {
        "provider": request.ai_provider or current["provider"],
        "base_url": request.ai_base_url if request.ai_base_url is not None else current["base_url"],
        "model": request.ai_model if request.ai_model is not None else current["model"],
        "api_key": request.api_key.strip() if request.api_key and request.api_key.strip() else current["api_key"],
    }
    try:
        return await providers.test_connection(config)
    except providers.ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/import")
async def import_file(request: Request, filename: str = Query(..., min_length=1, max_length=255)) -> dict[str, Any]:
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        return await asyncio.to_thread(parsers.parse_file, urllib.parse.unquote(filename), data)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/template/analyze")
async def analyze_template(request: Request, filename: str = Query(..., min_length=1, max_length=255)) -> dict[str, Any]:
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="上传模板为空")
    try:
        return await asyncio.to_thread(parsers.analyze_template, urllib.parse.unquote(filename), data)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/ai/correct-ocr")
async def correct_ocr(request: OCRCorrectionRequest) -> dict[str, Any]:
    return await ai.correct_ocr_text(storage.get_ai_settings(), [page.model_dump() for page in request.pages])


@app.post("/api/ai/project-case")
async def project_case(request: ProjectCaseRequest) -> dict[str, Any]:
    return await ai.draft_project_case(
        storage.get_ai_settings(), request.profile, request.jd, request.folder_name,
        [item.model_dump() for item in request.files], request.material_type,
    )


@app.post("/api/ai/learning-path")
async def learning_path(request: LearningPathRequest) -> dict[str, Any]:
    if not request.jd.strip():
        raise HTTPException(status_code=400, detail="请先粘贴岗位 JD")
    ai_settings = storage.get_ai_settings()
    result = await ai.generate_learning_path(ai_settings, request.profile, request.jd, request.analysis)
    search = storage.get_search_settings()
    result = await learning.attach_direct_resources(result, search["provider"], search["api_key"])
    try:
        result = await ai.rank_learning_resources(ai_settings, result)
    except ai.AIError:
        for stage in result.get("stages", []):
            stage.pop("resource_candidates", None)
        result["resource_note"] += " 候选课程语义复核失败，本次按检索相关度展示。"
    return learning.finalize_resource_pools(result)


@app.post("/api/learning-feedback")
async def learning_feedback(request: LearningFeedbackRequest) -> dict[str, bool]:
    if not learning.is_supported_direct_url(request.url):
        raise HTTPException(status_code=400, detail="只接受当前支持的具体课程链接")
    storage.set_learning_resource_feedback(request.url, request.verdict)
    return {"ok": True}


@app.post("/api/ai/structure")
async def structure(request: TextRequest) -> dict[str, Any]:
    return await ai.structure_profile(storage.get_ai_settings(), request.raw_text)


@app.post("/api/ai/analyze")
async def analyze(request: ProfileRequest) -> dict[str, Any]:
    if not request.jd.strip():
        raise HTTPException(status_code=400, detail="请先粘贴岗位 JD")
    return await ai.analyze_jd(storage.get_ai_settings(), request.profile, request.jd)


@app.post("/api/ai/rewrite")
async def rewrite(request: ProfileRequest) -> dict[str, Any]:
    if not request.jd.strip():
        raise HTTPException(status_code=400, detail="请先粘贴岗位 JD")
    return await ai.rewrite_profile(storage.get_ai_settings(), request.profile, request.jd)


@app.post("/api/ai/generate")
async def generate_targeted(request: GenerateRequest) -> dict[str, Any]:
    if not request.jd.strip():
        raise HTTPException(status_code=400, detail="请先粘贴岗位 JD")
    return await ai.generate_targeted_profile(
        storage.get_ai_settings(),
        request.profile,
        request.jd,
        request.related_experience,
        request.generation_mode,
        request.proficiency_level,
    )


@app.post("/api/ai/question")
async def question(request: QuestionRequest) -> dict[str, Any]:
    return await ai.next_question(storage.get_ai_settings(), request.profile, request.jd, request.history)


@app.post("/api/ai/refine")
async def refine(request: RefineRequest) -> dict[str, Any]:
    return await ai.refine_with_answer(
        storage.get_ai_settings(), request.profile, request.jd, request.question, request.answer, request.history, request.previous_answer
    )


@app.post("/api/ai/edit-selection")
async def edit_selection(request: SelectionEditRequest) -> dict[str, str]:
    return await ai.edit_selected_text(
        storage.get_ai_settings(), request.profile, request.jd, request.path,
        request.field_label, request.full_text, request.selected_text,
        request.selection_start, request.selection_end, request.instruction,
    )


@app.post("/api/ai/add-content")
async def add_content(request: AddContentRequest) -> dict[str, Any]:
    return await ai.add_resume_content(
        storage.get_ai_settings(), request.profile, request.jd, request.instruction, request.mode
    )


@app.post("/api/ai/translate")
async def translate(request: TranslationRequest) -> dict[str, Any]:
    return await ai.translate_profile(storage.get_ai_settings(), request.profile, request.target)


@app.post("/api/preview", response_class=HTMLResponse)
async def preview(payload: dict[str, Any] = Body(...)) -> str:
    return renderers.render_resume_html(payload)


@app.post("/api/export/pdf")
async def export_pdf(payload: dict[str, Any] = Body(...)) -> Response:
    try:
        content = await renderers.render_pdf(payload)
    except renderers.ResumeLayoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF 生成失败。可先使用 Ctrl+P，或运行 python -m playwright install chromium 后重试。",
        ) from exc
    filename = renderers.safe_filename(payload.get("resume", {}).get("title", "简历"), "pdf")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"},
    )


@app.post("/api/export/docx")
async def export_docx(payload: dict[str, Any] = Body(...)) -> Response:
    content = await asyncio.to_thread(renderers.render_docx, payload)
    filename = renderers.safe_filename(payload.get("resume", {}).get("title", "简历"), "docx")
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"},
    )


@app.get("/api/backup")
async def backup() -> Response:
    content = json.dumps(storage.export_backup(), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=resume-workshop-backup.json"},
    )


@app.get("/api/demo-package")
async def download_demo_package() -> Response:
    content = await asyncio.to_thread(demo_package.build_demo_package)
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(demo_package.PACKAGE_FILENAME)}"},
    )


@app.post("/api/restore")
async def restore(request: Request) -> dict[str, bool]:
    try:
        payload = json.loads((await request.body()).decode("utf-8-sig"))
        storage.import_backup(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def _existing_instance(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=0.6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("ok") is True and payload.get("version") == app.version
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _configure_packaged_output() -> None:
    global _packaged_log_stream
    if not getattr(sys, "frozen", False):
        return
    runtime.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _packaged_log_stream = (runtime.USER_DATA_DIR / "app.log").open("a", encoding="utf-8", buffering=1)
    sys.stdout = _packaged_log_stream
    sys.stderr = _packaged_log_stream


def run() -> None:
    url = f"http://127.0.0.1:{LOCAL_PORT}"
    if _existing_instance(url):
        if os.environ.get("RESUME_WORKSHOP_NO_BROWSER") != "1":
            webbrowser.open(url)
        return
    _configure_packaged_output()
    if os.environ.get("RESUME_WORKSHOP_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=LOCAL_PORT, log_level="info")


if __name__ == "__main__":
    run()
