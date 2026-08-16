from __future__ import annotations

import base64
import ctypes
import getpass
import json
import os
import sqlite3
import subprocess
import sys
from ctypes import wintypes
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from . import runtime

DATA_DIR = runtime.USER_DATA_DIR
DB_PATH = DATA_DIR / "resume.db"
MAX_VERSIONS = 100
KEYCHAIN_MARKER = "keychain:v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_resource_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_resource_feedback (
                url TEXT PRIMARY KEY,
                verdict TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        existing = db.execute("SELECT id FROM state WHERE id = 1").fetchone()
        if not existing:
            db.execute(
                "INSERT INTO state(id, payload, updated_at) VALUES(1, ?, ?)",
                (json.dumps(default_state(), ensure_ascii=False), _now()),
            )


def default_state() -> dict[str, Any]:
    return {
        "profile": {
            "basics": {
                "name": "",
                "target_role": "",
                "phone": "",
                "email": "",
                "city": "",
                "links": "",
                "summary": "",
                "photo": "",
            },
            "experience": [],
            "projects": [],
            "education": [],
            "skills": [],
            "certificates": [],
            "languages": [],
        },
        "resume": {
            "title": "我的定制简历",
            "language": "zh",
            "template": "ats",
            "custom_template": None,
            "page_mode": "one",
            "section_order": [
                "summary",
                "experience",
                "projects",
                "education",
                "skills",
                "certificates",
                "languages",
            ],
            "jd": "",
            "jd_ocr_original": "",
            "jd_ocr_corrected": "",
            "jd_ocr_corrections": [],
            "jd_ocr_images": [],
            "learning_path": None,
            "analysis": None,
            "tailored_profile": None,
            "tailored_jd": "",
            "related_experience": "",
            "generation_mode": "same_direction",
            "proficiency_level": "beginner",
            "candidate_drafts": [],
            "suggestions": [],
            "questions": [],
        },
        "resume_library": [],
        "active_resume_id": None,
    }


def get_state() -> dict[str, Any]:
    initialize()
    with _connect() as db:
        row = db.execute("SELECT payload FROM state WHERE id = 1").fetchone()
    return json.loads(row["payload"]) if row else default_state()


def save_state(payload: dict[str, Any], version_label: str | None = None) -> None:
    initialize()
    serialized = json.dumps(payload, ensure_ascii=False)
    timestamp = _now()
    with _connect() as db:
        db.execute(
            "UPDATE state SET payload = ?, updated_at = ? WHERE id = 1",
            (serialized, timestamp),
        )
        if version_label:
            _insert_version(db, version_label, serialized, timestamp)
        _prune_versions(db)


def _insert_version(db: sqlite3.Connection, label: str, payload: str, created_at: str) -> None:
    duplicate = db.execute(
        "SELECT 1 FROM versions WHERE label = ? AND payload = ? LIMIT 1",
        (label[:80], payload),
    ).fetchone()
    if not duplicate:
        db.execute(
            "INSERT INTO versions(label, payload, created_at) VALUES(?, ?, ?)",
            (label[:80], payload, created_at),
        )


def _prune_versions(db: sqlite3.Connection) -> None:
    db.execute(
        "DELETE FROM versions WHERE id NOT IN "
        "(SELECT id FROM versions ORDER BY id DESC LIMIT ?)",
        (MAX_VERSIONS,),
    )


def list_versions() -> list[dict[str, Any]]:
    initialize()
    with _connect() as db:
        rows = db.execute(
            "SELECT id, label, created_at FROM versions ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(row) for row in rows]


def get_edit_history() -> dict[str, Any]:
    initialize()
    with _connect() as db:
        state_row = db.execute("SELECT payload FROM state WHERE id = 1").fetchone()
        rows = db.execute(
            "SELECT label, payload FROM versions ORDER BY id DESC LIMIT 2"
        ).fetchall()
    empty = {"undo": None, "redo": None}
    if not state_row or len(rows) < 2:
        return empty
    current = json.loads(state_row["payload"])
    latest = json.loads(rows[0]["payload"])
    if current != latest:
        return empty
    label = str(rows[0]["label"])
    edit_prefixes = ("AI 局部修改", "AI 智能新增", "AI 调整", "手动新增", "手动删除", "手动编辑岗位字段", "恢复操作")
    undo_prefixes = ("撤销操作", "撤销 AI", "撤销上次")
    previous = json.loads(rows[1]["payload"])
    profile = (previous.get("resume") or {}).get("tailored_profile")
    if not isinstance(profile, dict):
        return empty
    entry = {"kind": "profile", "profile": profile, "label": label}
    if label.startswith(undo_prefixes):
        return {"undo": None, "redo": entry}
    if label.startswith(edit_prefixes):
        return {"undo": entry, "redo": None}
    return empty


def restore_version(version_id: int) -> dict[str, Any]:
    initialize()
    with _connect() as db:
        row = db.execute(
            "SELECT payload FROM versions WHERE id = ?", (version_id,)
        ).fetchone()
        if not row:
            raise ValueError("找不到该历史版本")
        current_row = db.execute("SELECT payload FROM state WHERE id = 1").fetchone()
        timestamp = _now()
        if current_row:
            _insert_version(db, "恢复历史版本前的自动快照", current_row["payload"], timestamp)
        db.execute(
            "UPDATE state SET payload = ?, updated_at = ? WHERE id = 1",
            (row["payload"], timestamp),
        )
        _prune_versions(db)
    return json.loads(row["payload"])


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _dpapi_protect(value: str) -> str:
    if os.name != "nt":
        return "plain:" + base64.b64encode(value.encode()).decode()
    source, source_buffer = _blob(value.encode("utf-8"))
    target = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "ResumeWorkshop", None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(target.pbData, target.cbData)
        return "dpapi:" + base64.b64encode(encrypted).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)
        del source_buffer


def _dpapi_unprotect(value: str) -> str:
    prefix, encoded = value.split(":", 1)
    raw = base64.b64decode(encoded)
    if prefix == "plain":
        return raw.decode("utf-8")
    source, source_buffer = _blob(raw)
    target = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)
        del source_buffer


def _keychain_service(key: str) -> str:
    return f"com.resumeworkshop.{key}"


def _keychain_set(key: str, value: str) -> None:
    subprocess.run(
        [
            "security", "add-generic-password", "-U",
            "-a", getpass.getuser(), "-s", _keychain_service(key), "-w", value,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _keychain_get(key: str) -> str:
    result = subprocess.run(
        [
            "security", "find-generic-password",
            "-a", getpass.getuser(), "-s", _keychain_service(key), "-w",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _keychain_delete(key: str) -> None:
    subprocess.run(
        [
            "security", "delete-generic-password",
            "-a", getpass.getuser(), "-s", _keychain_service(key),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _set_setting(key: str, value: str, *, protected: bool = False) -> None:
    initialize()
    with _connect() as db:
        if value.strip():
            if protected and sys.platform == "darwin":
                _keychain_set(key, value.strip())
                stored_value = KEYCHAIN_MARKER
            else:
                stored_value = _dpapi_protect(value.strip()) if protected else value.strip()
            db.execute(
                "INSERT INTO settings(key, value, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, stored_value, _now()),
            )
        else:
            if protected and sys.platform == "darwin":
                _keychain_delete(key)
            db.execute("DELETE FROM settings WHERE key = ?", (key,))


def _get_setting(key: str, *, protected: bool = False) -> str:
    initialize()
    with _connect() as db:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return ""
    if not protected:
        return str(row["value"])
    try:
        if sys.platform == "darwin" and row["value"] == KEYCHAIN_MARKER:
            return _keychain_get(key)
        return _dpapi_unprotect(row["value"])
    except (OSError, ValueError, subprocess.SubprocessError):
        # A key protected under another operating-system account or security
        # context cannot be decrypted here. Treat it as unconfigured instead of
        # breaking the entire local app.
        return ""


def set_ai_settings(
    provider: str,
    base_url: str,
    model: str,
    api_key: str | None = None,
    *,
    clear_api_key: bool = False,
) -> None:
    from .providers import PROVIDERS, normalize_config

    if provider not in PROVIDERS:
        raise ValueError("不支持的 AI 服务商")
    definition = PROVIDERS[provider]
    preview_key = "" if clear_api_key else (
        api_key if api_key is not None and api_key.strip() else _get_setting(f"ai_api_key:{provider}", protected=True)
    )
    if provider == "deepseek" and not preview_key:
        preview_key = _get_setting("deepseek_api_key", protected=True)
    try:
        normalize_config({
            "provider": provider,
            "base_url": base_url or definition.base_url,
            "model": model or definition.model,
            "api_key": preview_key or ("preview-key" if definition.key_required else ""),
        })
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc
    _set_setting("ai_provider", provider)
    _set_setting(f"ai_base_url:{provider}", (base_url or definition.base_url).strip())
    _set_setting(f"ai_model:{provider}", (model or definition.model).strip())
    if clear_api_key:
        _set_setting(f"ai_api_key:{provider}", "", protected=True)
        if provider == "deepseek":
            _set_setting("deepseek_api_key", "", protected=True)
    elif api_key is not None and api_key.strip():
        _set_setting(f"ai_api_key:{provider}", api_key, protected=True)
        if provider == "deepseek":
            _set_setting("deepseek_api_key", api_key, protected=True)


def get_ai_settings(provider: str | None = None) -> dict[str, Any]:
    from .providers import PROVIDERS

    provider_id = provider or _get_setting("ai_provider") or "deepseek"
    if provider_id not in PROVIDERS:
        provider_id = "deepseek"
    definition = PROVIDERS[provider_id]
    key = _get_setting(f"ai_api_key:{provider_id}", protected=True)
    if provider_id == "deepseek" and not key:
        key = _get_setting("deepseek_api_key", protected=True)
    return {
        "provider": provider_id,
        "base_url": _get_setting(f"ai_base_url:{provider_id}") or definition.base_url,
        "model": _get_setting(f"ai_model:{provider_id}") or definition.model,
        "api_key": key,
    }


def set_api_key(api_key: str) -> None:
    current = get_ai_settings("deepseek")
    set_ai_settings("deepseek", current["base_url"], current["model"], api_key, clear_api_key=not api_key.strip())


def get_api_key() -> str:
    return get_ai_settings()["api_key"]


def set_search_settings(provider: str, api_key: str) -> None:
    if provider not in {"", "brave", "tavily"}:
        raise ValueError("不支持的课程搜索服务")
    _set_setting("learning_search_provider", provider)
    _set_setting("learning_search_api_key", api_key, protected=True)


def get_search_settings() -> dict[str, Any]:
    provider = _get_setting("learning_search_provider")
    api_key = _get_setting("learning_search_api_key", protected=True)
    if provider not in {"brave", "tavily"}:
        provider = ""
    return {
        "provider": provider,
        "configured": bool(provider and api_key),
        "masked": ("•" * 8 + api_key[-4:]) if api_key else "",
        "api_key": api_key,
    }


def api_key_status() -> dict[str, Any]:
    from .providers import PROVIDERS, public_provider_options

    ai = get_ai_settings()
    key = ai["api_key"]
    definition = PROVIDERS[ai["provider"]]
    search = get_search_settings()
    return {
        "configured": bool(key),
        "masked": ("•" * 8 + key[-4:]) if key else "",
        "ai_provider": ai["provider"],
        "ai_provider_name": definition.name,
        "ai_base_url": ai["base_url"],
        "ai_model": ai["model"],
        "ai_key_required": definition.key_required,
        "ai_ready": bool(ai["model"] and ai["base_url"] and (key or not definition.key_required)),
        "ai_providers": public_provider_options(),
        "search_provider": search["provider"],
        "search_configured": search["configured"],
        "search_masked": search["masked"],
    }


def get_learning_resource_cache(cache_key: str, max_age_days: int = 30) -> list[dict[str, Any]] | None:
    initialize()
    with _connect() as db:
        row = db.execute(
            "SELECT payload, updated_at FROM learning_resource_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if not row:
        return None
    try:
        updated_at = datetime.fromisoformat(row["updated_at"])
        if datetime.now(timezone.utc) - updated_at > timedelta(days=max_age_days):
            return None
        payload = json.loads(row["payload"])
        return payload if isinstance(payload, list) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def set_learning_resource_cache(cache_key: str, resources: list[dict[str, Any]]) -> None:
    initialize()
    serialized = json.dumps(resources, ensure_ascii=False)
    with _connect() as db:
        db.execute(
            "INSERT INTO learning_resource_cache(cache_key, payload, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (cache_key, serialized, _now()),
        )


def set_learning_resource_feedback(url: str, verdict: str) -> None:
    if verdict not in {"useful", "irrelevant", "too_hard", "too_easy", "broken"}:
        raise ValueError("不支持的课程反馈")
    initialize()
    with _connect() as db:
        db.execute(
            "INSERT INTO learning_resource_feedback(url, verdict, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(url) DO UPDATE SET verdict=excluded.verdict, updated_at=excluded.updated_at",
            (url[:1000], verdict, _now()),
        )


def get_learning_resource_feedback(url: str) -> str:
    initialize()
    with _connect() as db:
        row = db.execute(
            "SELECT verdict FROM learning_resource_feedback WHERE url = ?", (url[:1000],)
        ).fetchone()
    return str(row["verdict"]) if row else ""


def _all_learning_feedback() -> list[dict[str, str]]:
    initialize()
    with _connect() as db:
        rows = db.execute(
            "SELECT url, verdict, updated_at FROM learning_resource_feedback ORDER BY updated_at"
        ).fetchall()
    return [dict(row) for row in rows]


def export_backup() -> dict[str, Any]:
    return {
        "format": "resume-workshop-backup",
        "version": 1,
        "exported_at": _now(),
        "state": get_state(),
        "versions": _all_versions(),
        "learning_feedback": _all_learning_feedback(),
        "notes": "出于安全考虑，备份不包含任何模型或课程搜索服务 API Key。",
    }


def _all_versions() -> list[dict[str, Any]]:
    initialize()
    with _connect() as db:
        rows = db.execute(
            "SELECT label, payload, created_at FROM versions ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def import_backup(payload: dict[str, Any]) -> None:
    if payload.get("format") != "resume-workshop-backup" or payload.get("version") != 1:
        raise ValueError("不是受支持的简历工坊备份文件")
    state = payload.get("state")
    if not isinstance(state, dict) or "profile" not in state or "resume" not in state:
        raise ValueError("备份文件缺少必要数据")
    initialize()
    with _connect() as db:
        current_row = db.execute("SELECT payload FROM state WHERE id = 1").fetchone()
        if current_row:
            _insert_version(db, "恢复备份前的自动快照", current_row["payload"], _now())
        db.execute(
            "UPDATE state SET payload = ?, updated_at = ? WHERE id = 1",
            (json.dumps(state, ensure_ascii=False), _now()),
        )
        for item in payload.get("versions", []):
            if all(key in item for key in ("label", "payload", "created_at")):
                _insert_version(db, str(item["label"]), str(item["payload"]), str(item["created_at"]))
        for item in payload.get("learning_feedback", []):
            if not isinstance(item, dict) or item.get("verdict") not in {"useful", "irrelevant", "too_hard", "too_easy", "broken"}:
                continue
            db.execute(
                "INSERT INTO learning_resource_feedback(url, verdict, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(url) DO UPDATE SET verdict=excluded.verdict, updated_at=excluded.updated_at",
                (str(item.get("url", ""))[:1000], item["verdict"], str(item.get("updated_at") or _now())),
            )
        _prune_versions(db)
