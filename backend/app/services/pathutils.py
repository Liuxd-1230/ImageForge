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


def safe_relative(relative: str) -> str | None:
    """Validate a user-supplied relative path for scan-import.

    Returns the POSIX-normalized relative path, or None if it is unsafe:
    absolute paths (incl. Windows drive), `..` traversal, empty, or leading slash.
    """
    if not relative:
        return None
    p = normalize_separators(relative.strip())
    if p.startswith("/") or _WINDOWS_DRIVE_RE.match(p):
        return None
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if ".." in parts:
        return None
    return "/".join(parts)


def join_within_root(root: str, relative: str) -> str | None:
    """Join `root` with a safe relative path; returns the realpath only if it
    stays inside `root` (lexical containment), else None."""
    safe = safe_relative(relative)
    if safe is None:
        return None
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, *safe.split("/")))
    try:
        common = os.path.commonpath([root_real, candidate])
    except ValueError:
        return None
    if common != root_real:
        return None
    return candidate


def match_comfy_lora(rel: str, basename: str, comfy_norm: list[str]) -> str | None:
    """Match a candidate (relative to its source root) against ComfyUI's lora list.

    Rules (avoid the 'same basename from two dirs both marked recognized' trap):
    - exact relative-path match wins;
    - a comfy entry that *ends with* `/rel` (candidate sits in a deeper folder
      inside the comfy lora root) also matches;
    - basename fallback ONLY when exactly one comfy entry has that basename AND
      no other candidate conflicts — callers decide ambiguity via `comfy_basenames`
      multiplicity. Here we return the comfy name only for the unambiguous case.
    """
    for n in comfy_norm:
        if n == rel or n.endswith("/" + rel):
            return n
    return None
