"""Civitai metadata client (LoRA Metadata V1) — Red/Green dual host.

Tier 1 — Stable identification (official Site API, 主链):
- lookup_by_hash / lookup_by_hashes (bulk, chunks of 100) via /api/v1/model-versions/by-hash
- get_model (caller dedupes by modelId)
- get_version_images (fallback cover search when version.images is empty)
- download_cover (secure: https + allowlisted hosts + image/* content-type + size cap)
- hash_local_file (streaming SHA256, 4 MiB chunks — never read the whole file into RAM)
- resolve_local_lora_file (source_path → enabled LoraSource exact/basename search)

Tier 2 — Optional UI metadata enrichment (Civitai Web public tRPC, 可失败):
- get_model_version_enrichment → public procedure modelVersion.getById
  (settings.strength / clipSkip / steps / epochs / trainedWords / description)。
  这不是官方 Site REST API：transport 集中在这一个函数里，Civitai 改 tRPC
  时 Tier 1 identification 不受影响；调用方必须 fail-open（enrichment 失败
  不影响 matched 状态）。

Token safety:
- token only sent to civitai.red / civitai.com via Authorization: Bearer
- never in query string / logs / metadata_json / error detail
- 401/403 on public metadata → anonymous retry once, auth_warning=True

Error model (status strings, per spec §63):
matched | not_found | remote_error | rate_limited | local_file_not_found |
local_file_ambiguous | hash_file_mismatch
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

import httpx
from sqlmodel import Session, select

from app.config import settings, CIVITAI_HOSTS

logger = logging.getLogger(__name__)

HASH_CHUNK_BYTES = 4 * 1024 * 1024          # streaming SHA256 chunk (spec §23)
MAX_COVER_BYTES = 15 * 1024 * 1024          # cover download cap (spec §21)
COVER_TIMEOUT = 15.0
API_TIMEOUT = 20.0
BULK_CHUNK = 100                            # Civitai bulk by-hash max (spec §12)
COVER_EXTS = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}

STATUS_MATCHED = "matched"
STATUS_NOT_FOUND = "not_found"
STATUS_REMOTE_ERROR = "remote_error"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_LOCAL_FILE_NOT_FOUND = "local_file_not_found"
STATUS_LOCAL_FILE_AMBIGUOUS = "local_file_ambiguous"
STATUS_HASH_FILE_MISMATCH = "hash_file_mismatch"


class CivitaiRequestError(Exception):
    """Civitai HTTP-level failure with classification fields."""

    def __init__(self, status: str, detail: str = "",
                 retry_after: Optional[float] = None, http_status: Optional[int] = None):
        super().__init__(detail or status)
        self.status = status
        self.detail = detail
        self.retry_after = retry_after
        self.http_status = http_status


class CivitaiClient:
    def __init__(self, transport: Any = None):
        """transport: httpx.AsyncBaseTransport for tests (httpx.MockTransport)."""
        self.transport = transport

    # ── hosts / auth ──────────────────────────────────────────────────────
    def host_base(self, host: str) -> str:
        if host not in CIVITAI_HOSTS:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"不支持的 Civitai host: {host}")
        return CIVITAI_HOSTS[host]

    def _auth_headers(self) -> Dict[str, str]:
        token = (settings.CIVITAI_API_TOKEN or "").strip()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def _request(
        self, method: str, url: str, *, host: str,
        retry_5xx: int = 2, json_body: Any = None,
        allow_anonymous_retry: bool = True
    ) -> Tuple[httpx.Response, bool]:
        """Request with Bearer token + retry policy.

        Returns (response, auth_warning). Raises CivitaiRequestError for
        network errors / 5xx-after-retry / 429-after-retry.
        401/403 with token → one anonymous retry (auth_warning=True).
        """
        token = (settings.CIVITAI_API_TOKEN or "").strip()

        async def attempt(use_token: bool) -> httpx.Response:
            headers = {"Authorization": f"Bearer {token}"} if (use_token and token) else {}
            kwargs: Dict[str, Any] = {"headers": headers}
            if json_body is not None:
                kwargs["json"] = json_body
            async with httpx.AsyncClient(transport=self.transport, timeout=API_TIMEOUT) as client:
                resp = await client.request(method, url, **kwargs)
                return resp

        try:
            resp = await attempt(use_token=True)
        except httpx.HTTPError as e:
            resp = None
            last_err: Exception = e
        else:
            last_err = None

        # 401/403 with token → anonymous retry once (spec §6)
        if resp is not None and resp.status_code in (401, 403) and token and allow_anonymous_retry:
            try:
                resp2 = await attempt(use_token=False)
                if resp2.status_code in (401, 403):
                    raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                              f"Civitai 公开接口拒绝访问 (HTTP {resp2.status_code})",
                                              http_status=resp2.status_code)
                return resp2, True
            except CivitaiRequestError:
                raise
            except httpx.HTTPError as e:
                resp = None
                last_err = e

        # network error / 5xx → lightweight exponential backoff retry (spec §64)
        for i in range(retry_5xx + 1):
            if i > 0:
                await asyncio.sleep(0.5 * (2 ** (i - 1)))
            if resp is None:
                try:
                    resp = await attempt(use_token=True)
                except httpx.HTTPError as e:
                    last_err = e
                    continue
            if resp.status_code not in (502, 503, 504):
                return resp, False
            resp = None  # 5xx → retry
        raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                  f"Civitai 网络错误: {last_err}" if last_err else "Civitai 网络错误")

    async def _get_json(self, url: str, host: str) -> Tuple[Any, bool]:
        resp, auth_warning = await self._request("GET", url, host=host)
        if resp.status_code == 404:
            raise CivitaiRequestError(STATUS_NOT_FOUND, "not found", http_status=404)
        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
            if retry_after is not None:
                await asyncio.sleep(min(retry_after, 5.0))
                resp, auth_warning = await self._request("GET", url, host=host, retry_5xx=1)
                if resp.status_code == 429:
                    raise CivitaiRequestError(STATUS_RATE_LIMITED, "Civitai rate limited", http_status=429)
            else:
                raise CivitaiRequestError(STATUS_RATE_LIMITED, "Civitai rate limited", http_status=429)
        if resp.status_code != 200:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                      f"Civitai HTTP {resp.status_code}", http_status=resp.status_code)
        try:
            return resp.json(), auth_warning
        except ValueError as e:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"Civitai 响应解析失败: {e}")

    # ── lookup ────────────────────────────────────────────────────────────
    async def lookup_by_hash(self, sha256: str, host: str) -> Tuple[Dict[str, Any], bool]:
        """GET /api/v1/model-versions/by-hash/{sha256} → version dict."""
        url = f"{self.host_base(host)}/api/v1/model-versions/by-hash/{sha256.lower()}"
        data, auth_warning = await self._get_json(url, host)
        return data or {}, auth_warning

    async def lookup_by_hashes(self, sha256s: List[str], host: str) -> Tuple[List[Dict[str, Any]], bool]:
        """POST /api/v1/model-versions/by-hash with a list of hashes.

        Chunks internally (100 per request, spec §12). Response array is NOT
        positional — callers must remap by files[].hashes.SHA256 (spec §13).
        """
        out: List[Dict[str, Any]] = []
        auth_warning = False
        for i in range(0, len(sha256s), BULK_CHUNK):
            chunk = [h.lower() for h in sha256s[i:i + BULK_CHUNK]]
            url = f"{self.host_base(host)}/api/v1/model-versions/by-hash"
            resp, warn = await self._request("POST", url, host=host, json_body=chunk)
            if resp.status_code == 404:
                raise CivitaiRequestError(STATUS_NOT_FOUND, "not found", http_status=404)
            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                if retry_after is not None:
                    await asyncio.sleep(min(retry_after, 5.0))
                    resp, warn = await self._request("POST", url, host=host,
                                                     json_body=chunk, retry_5xx=1)
                    if resp.status_code == 429:
                        raise CivitaiRequestError(STATUS_RATE_LIMITED, "Civitai rate limited", http_status=429)
                else:
                    raise CivitaiRequestError(STATUS_RATE_LIMITED, "Civitai rate limited", http_status=429)
            if resp.status_code != 200:
                raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                          f"Civitai HTTP {resp.status_code}", http_status=resp.status_code)
            try:
                chunk_data = resp.json()
            except ValueError as e:
                raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"Civitai 响应解析失败: {e}")
            if isinstance(chunk_data, list):
                out.extend(chunk_data)
            auth_warning = auth_warning or warn
        return out, auth_warning

    async def get_model(self, model_id: int, host: str) -> Dict[str, Any]:
        url = f"{self.host_base(host)}/api/v1/models/{model_id}"
        data, _ = await self._get_json(url, host)
        return data or {}

    # ── Tier 2: Civitai Web public tRPC enrichment（非官方 Site REST API） ──
    # 仅此函数了解 tRPC transport。Civitai 对无浏览器 Referer/Origin 的 tRPC
    # 请求返回 401 "Please use the public API instead"（2026-09 实测），因此
    # 必须带 Referer。失败一律抛 CivitaiRequestError，由调用方 fail-open。
    async def get_model_version_enrichment(self, version_id: int, host: str) -> Dict[str, Any]:
        """public tRPC modelVersion.getById → version detail dict.

        返回 result.data.json（含 settings / clipSkip / steps / epochs /
        trainedWords / description）。withFiles=false：by-hash 已完成 file
        identification，这里不再拉 files。
        """
        base = self.host_base(host)
        payload = {"json": {"id": int(version_id), "withFiles": False}}
        url = f"{base}/api/trpc/modelVersion.getById?input={quote(json.dumps(payload, separators=(',', ':')))}"
        headers = {
            "Referer": f"{base}/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ImageForge-metadata-enrichment",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=API_TIMEOUT) as client:
                resp = await client.get(url, headers=headers)
        except httpx.HTTPError as e:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"tRPC enrichment 网络错误: {e}")
        if resp.status_code == 429:
            raise CivitaiRequestError(STATUS_RATE_LIMITED, "Civitai rate limited", http_status=429)
        if resp.status_code != 200:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                      f"tRPC enrichment HTTP {resp.status_code}",
                                      http_status=resp.status_code)
        try:
            body = resp.json()
        except ValueError as e:
            raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"tRPC enrichment 响应解析失败: {e}")
        data = ((body or {}).get("result") or {}).get("data") or {}
        detail = data.get("json")
        if not isinstance(detail, dict):
            err = ((body or {}).get("error") or {}).get("json") or {}
            raise CivitaiRequestError(STATUS_REMOTE_ERROR,
                                      f"tRPC enrichment 无数据: {err.get('message') or 'unknown'}")
        return detail

    async def get_version_images(self, version_id: int, host: str) -> List[Dict[str, Any]]:
        """Fallback cover search when version.images is empty (spec §16)."""
        url = (f"{self.host_base(host)}/api/v1/images"
               f"?modelVersionId={version_id}&limit=8&sort=Most%20Reactions")
        data, _ = await self._get_json(url, host)
        return data if isinstance(data, list) else (data.get("items") or [] if isinstance(data, dict) else [])

    @staticmethod
    def _is_allowed_cover_host(host: str) -> bool:
        """仅允许 Civitai 官方域（含其图片 CDN 子域，如 image.civitai.com / image-b2.civitai.com）。
        禁止任意第三方 host（SSRF 防护，spec §21）。"""
        h = (host or "").strip().lower().rstrip(".")
        if h in ("civitai.com", "civitai.red", "www.civitai.com"):
            return True
        return h.endswith(".civitai.com") or h.endswith(".civitai.red")

    async def download_cover(self, url: str) -> Tuple[bytes, str]:
        """Download a cover. Returns (bytes, content_type). Raises on unsafe/size/type.

        Only https + Civitai 官方域（含图片 CDN 子域）; follows redirects but
        re-validates the final host; image/* content-type; ≤15 MB.
        """
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise CivitaiRequestError(STATUS_REMOTE_ERROR, "封面 URL 必须是 HTTPS")
        async with httpx.AsyncClient(transport=self.transport, timeout=COVER_TIMEOUT,
                                     follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            final = urlparse(str(resp.url))
            if final.scheme != "https" or not self._is_allowed_cover_host(final.hostname or ""):
                raise CivitaiRequestError(STATUS_REMOTE_ERROR, "封面重定向到非 Civitai host，已拒绝")
            ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            if not ctype.startswith("image/"):
                raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"封面 Content-Type 非图片: {ctype}")
            data = resp.content
            if len(data) > MAX_COVER_BYTES:
                raise CivitaiRequestError(STATUS_REMOTE_ERROR, "封面超过大小限制，已拒绝")
            return data, ctype


# ─────────────────────────── pure helpers ───────────────────────────

def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def hash_local_file(path: str) -> str:
    """Streaming SHA256 (4 MiB chunks). Never loads the whole file into RAM."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def sanitize_description(raw: Optional[str]) -> str:
    """Strip HTML from Civitai description → readable plain text（禁止执行远端 HTML）。

    - <p>/<br>/<li> 等块级标记转换为换行，保留基本段落结构；
    - 其余 tag 去除，HTML entity unescape；
    - 行内空白合并，>2 连续空行压缩为 1 个空行。
    """
    if not raw:
        return ""
    text = str(raw)
    # 块级/换行标记 → 换行（在通用 tag strip 之前）
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*(p|div|li|ul|ol|h[1-6]|blockquote|tr)\s*>", "\n", text)
    text = re.sub(r"(?i)<\s*li[^>]*>", "\n· ", text)
    text = re.sub(r"(?i)<\s*(p|div|ul|ol|h[1-6]|blockquote|tr)[^>]*>", "\n", text)
    # 其余所有 tag → 去掉（不执行）
    text = re.sub(r"<[^>]*>", "", text)
    text = html.unescape(text)
    # 行内空白合并；保留换行
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_finite_float(value: Any) -> Optional[float]:
    """Civitai settings.strength 防御解析：只接受可安全解析的 finite number。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def safe_int(value: Any) -> Optional[int]:
    """Civitai clipSkip/steps/epochs 防御解析：只接受有限整数。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _walk_lora_files(root: str, recursive: bool) -> List[str]:
    exts = (".safetensors", ".ckpt", ".pt")
    found: List[str] = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames.sort()
            for fn in filenames:
                if fn.lower().endswith(exts):
                    found.append(os.path.join(dirpath, fn))
    else:
        try:
            for fn in os.listdir(root):
                full = os.path.join(root, fn)
                if os.path.isfile(full) and fn.lower().endswith(exts):
                    found.append(full)
        except Exception:
            pass
    return sorted(found)


def resolve_local_lora_file(session: Session, lora: Any) -> Tuple[Optional[str], str]:
    """Locate the local weight file for a Lora row.

    Priority (spec §25):
      1. Lora.source_path if it still exists;
      2. enabled LoraSource: exact relative match (normalized), then unique
         basename search. 0 hits → local_file_not_found; >1 → local_file_ambiguous.
    Returns (path_or_None, status).
    """
    from app.models.lora_source import LoraSource

    sp = (lora.source_path or "").strip()
    if sp and os.path.isfile(sp):
        return sp, "ok"

    filename = (lora.filename or "").replace("\\", "/")
    if not filename:
        return None, STATUS_LOCAL_FILE_NOT_FOUND
    basename = filename.split("/")[-1].lower()

    sources = session.exec(select(LoraSource).where(LoraSource.enabled == True)).all()  # noqa: E712
    exact_hits: List[str] = []
    base_hits: List[str] = []
    for s in sources:
        root = (s.resolved_path or "").strip()
        if not root or not os.path.isdir(root):
            continue
        for full in _walk_lora_files(root, bool(s.recursive)):
            rel = os.path.relpath(full, root).replace("\\", "/")
            if rel == filename or rel.endswith("/" + filename):
                exact_hits.append(full)
            elif rel.split("/")[-1].lower() == basename:
                base_hits.append(full)

    if len(exact_hits) == 1:
        return exact_hits[0], "ok"
    if len(exact_hits) > 1:
        return None, STATUS_LOCAL_FILE_AMBIGUOUS
    if len(base_hits) == 1:
        return base_hits[0], "ok"
    if len(base_hits) > 1:
        return None, STATUS_LOCAL_FILE_AMBIGUOUS
    return None, STATUS_LOCAL_FILE_NOT_FOUND


def pick_cover_image(version: Dict[str, Any], images_fallback: List[Dict[str, Any]]) -> Optional[str]:
    """First usable https image URL (spec §16: 1 cover per LoRA, prefer version.images)."""
    for img in (version.get("images") or []):
        url = (img or {}).get("url") or ""
        if url.startswith("https://"):
            return url
    for img in (images_fallback or []):
        url = (img or {}).get("url") or ""
        if url.startswith("https://"):
            return url
    return None


def cover_ext_from_content_type(ctype: str) -> str:
    ctype = (ctype or "").split(";")[0].strip().lower()
    ext = COVER_EXTS.get(ctype)
    if not ext:
        raise CivitaiRequestError(STATUS_REMOTE_ERROR, f"不支持的封面格式: {ctype}")
    return ext
