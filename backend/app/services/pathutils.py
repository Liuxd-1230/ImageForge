"""Filesystem path helpers for ImageForge.

Handles Windows → WSL path translation so users can enter `D:\\Models\\LoRA`
or `D:/Models/LoRA` while the backend (running inside WSL) resolves it to
`/mnt/d/Models/LoRA`. Native Linux paths are left untouched.
"""
import os
import re

_WINDOWS_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")


def is_wsl() -> bool:
    """Detect whether the backend runs inside WSL/WSL2."""
    try:
        with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


_WSL = is_wsl()


def normalize_separators(path: str) -> str:
    """Normalize backslashes to forward slashes (POSIX side)."""
    return (path or "").replace("\\", "/")


def windows_to_wsl(display: str) -> str | None:
    """Convert `D:\\...` / `D:/...` to `/mnt/d/...`; returns None if not a drive path."""
    m = _WINDOWS_DRIVE_RE.match((display or "").strip())
    if not m:
        return None
    drive, rest = m.group(1).lower(), m.group(2)
    return f"/mnt/{drive}/{rest.replace('\\', '/')}"


def resolve_backend_path(display: str) -> str:
    """Return the canonical backend filesystem path for a user-entered path.

    - Translates Windows drive paths to WSL mount paths when running inside WSL.
    - Leaves native Linux paths untouched.
    - Resolves symlinks when the path exists (for dedup), else normalizes/absolutes.
    """
    p = (display or "").strip()
    if not p:
        return ""
    if _WSL:
        converted = windows_to_wsl(p)
        if converted:
            p = converted
    p = normalize_separators(p)
    if os.path.isdir(p):
        return os.path.realpath(p)
    return os.path.abspath(os.path.normpath(p))


def source_identity(display: str) -> tuple[str, str]:
    """Return (display_path, resolved_path) with display kept verbatim."""
    display = (display or "").strip()
    return display, resolve_backend_path(display)


def path_status(path: str) -> dict:
    """Validate a resolved path: exists / is dir / readable."""
    if not path:
        return {"exists": False, "is_dir": False, "readable": False, "error": "路径为空"}
    if not os.path.exists(path):
        return {"exists": False, "is_dir": False, "readable": False, "error": "路径不存在"}
    if not os.path.isdir(path):
        return {"exists": True, "is_dir": False, "readable": False, "error": "不是目录"}
    readable = os.access(path, os.R_OK)
    return {
        "exists": True,
        "is_dir": True,
        "readable": readable,
        "error": None if readable else "目录不可读",
    }
