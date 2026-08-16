from __future__ import annotations

import os
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT))


def _installed_data_dir() -> Path:
    override = os.environ.get("RESUME_WORKSHOP_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if not getattr(sys, "frozen", False):
        return SOURCE_ROOT / "data"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ResumeWorkshop"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ResumeWorkshop"
    return Path.home() / ".local" / "share" / "ResumeWorkshop"


USER_DATA_DIR = _installed_data_dir()


def configure_packaged_environment() -> None:
    if not getattr(sys, "frozen", False):
        return
    browsers = RESOURCE_ROOT / "playwright-browsers"
    if browsers.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
