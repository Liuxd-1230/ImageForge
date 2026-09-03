"""LoRA Civitai metadata orchestration: single refresh + batch refresh (V1).

Local-first ownership (spec §28): remote refresh NEVER overwrites
name / description / trigger_words / category / default_strength / is_favorite /
cover_hidden. Only fills the `remote_*` fields, sha256 cache and cover cache.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session

from app.config import settings, CIVITAI_HOSTS, CIVITAI_HOST_NAMES
from app.models.lora import Lora
from app.services.lora_metadata.civitai import (
    CivitaiClient,
    CivitaiRequestError,
    STATUS_MATCHED,
    STATUS_NOT_FOUND,
    STATUS_REMOTE_ERROR,
    STATUS_RATE_LIMITED,
    STATUS_LOCAL_FILE_NOT_FOUND,
    STATUS_LOCAL_FILE_AMBIGUOUS,
    STATUS_HASH_FILE_MISMATCH,
    resolve_local_lora_file,
    hash_local_file,
    sanitize_description,
    pick_cover_image,
    cover_ext_from_content_type,
)

logger = logging.getLogger(__name__)

_OTHER_HOST = {"red": "com", "com": "red"}
COVER_SEMAPHORE = 4     # cover 下载并发上限（spec §35）


def _cover_dir(sha256: str) -> str:
    return os.path.join(settings.LORA_METADATA_DIR, sha256)


def _target_host_key(lora: Lora) -> str:
    """刷新优先此前成功 metadata_host（裸 host）；否则 Settings host（默认 red，spec §8）。"""
    if lora.metadata_host:
        for key, name in CIVITAI_HOST_NAMES.items():
            if name == lora.metadata_host:
                return key
    return (settings.CIVITAI_API_HOST or "red")


def _matching_file(version: Dict[str, Any], local_sha: str) -> Optional[Dict[str, Any]]:
    """files[].hashes.SHA256 case-insensitive exact match（spec §11）。绝不假定 files[0]。"""
    local_l = (local_sha or "").lower()
    for f in version.get("files") or []:
        h = ((f.get("hashes") or {}).get("SHA256") or "").lower()
        if h and h == local_l:
            return f
    return None


def _clear_remote_metadata(lora: Lora) -> None:
    """文件被替换（hash 变化）→ 旧远端 metadata 与封面不可信（spec §24）。
    本地字段 name/description/trigger_words/category/favorite/default_strength 绝不触碰。"""
    for attr in (
        "metadata_provider", "metadata_host", "metadata_status",
        "remote_model_id", "remote_version_id", "remote_file_id",
        "remote_model_name", "remote_version_name", "remote_file_name",
        "remote_base_model", "remote_trained_words", "remote_description",
        "remote_creator", "remote_tags", "remote_nsfw_level",
        "cached_cover_path", "metadata_fetched_at", "metadata_json",
    ):
        setattr(lora, attr, None)


def _persist_remote(
    lora: Lora, version: Dict[str, Any], match_file: Dict[str, Any],
    model: Dict[str, Any], host_key: str, sha256: str, cover_path: Optional[str],
) -> None:
    """写远端字段 + hash 缓存 + 封面路径；本地用户字段一律不动。"""
    lora.metadata_provider = "civitai"
    lora.metadata_host = CIVITAI_HOST_NAMES[host_key]  # 裸 host（spec §60）
    lora.metadata_status = STATUS_MATCHED
    lora.remote_model_id = version.get("modelId")
    lora.remote_version_id = version.get("id")
    lora.remote_file_id = match_file.get("id")
    lora.remote_model_name = (
        (model or {}).get("name") or (version.get("model") or {}).get("name")
    ) or None
    lora.remote_version_name = version.get("name") or None
    lora.remote_file_name = match_file.get("name") or None   # 仅 metadata，绝不覆盖 Lora.filename
    lora.remote_base_model = version.get("baseModel") or None
    tw = version.get("trainedWords") or []
    lora.remote_trained_words = json.dumps(tw, ensure_ascii=False) if tw else None
    desc = (version.get("description") or "") or ((model or {}).get("description") or "")
    lora.remote_description = sanitize_description(desc) or None
    lora.remote_creator = ((model or {}).get("creator") or {}).get("username") or None
    tags = (model or {}).get("tags") or []
    lora.remote_tags = json.dumps(tags, ensure_ascii=False) if tags else None
    lora.remote_nsfw_level = version.get("nsfwLevel") or ((model or {}).get("nsfwLevel")) or None
    lora.cached_cover_path = cover_path
    lora.metadata_fetched_at = datetime.utcnow()
    # metadata_json：远端 normalized payload；不含 token / 本地绝对路径（spec §65）
    safe = dict(version)
    safe.pop("downloadUrl", None)
    lora.metadata_json = json.dumps(safe, ensure_ascii=False)[:100_000]


async def _hash_or_reuse(lora: Lora, path: str) -> str:
    """SHA256 持久缓存：size+mtime 未变 → 复用，不重新 hash（spec §22/§24）。"""
    st = os.stat(path)
    size, mtime = st.st_size, st.st_mtime_ns
    if lora.sha256 and lora.sha256_file_size == size and lora.sha256_mtime_ns == mtime:
        return lora.sha256
    new_sha = hash_local_file(path)
    if lora.sha256 and lora.sha256.lower() != new_sha.lower():
        _clear_remote_metadata(lora)  # 同路径文件被替换 → 旧 metadata 不可信
    lora.sha256 = new_sha
    lora.sha256_file_size = size
    lora.sha256_mtime_ns = mtime
    return new_sha


async def _download_cover(client: CivitaiClient, version: Dict[str, Any], host_key: str, sha256: str) -> Optional[str]:
    """V1 每 LoRA 只缓存 1 张 cover（spec §16）。version.images 优先，
    空 → GET /api/v1/images fallback。失败绝不导致 metadata 失败（spec §17/§61）。"""
    try:
        url = pick_cover_image(version, [])
        if not url:
            imgs = await client.get_version_images(version.get("id"), host_key)
            url = pick_cover_image(version, imgs)
        if not url:
            return None
        data, ctype = await client.download_cover(url)
        ext = cover_ext_from_content_type(ctype)
        d = _cover_dir(sha256)
        os.makedirs(d, exist_ok=True)
        cover_path = os.path.join(d, f"cover.{ext}")
        with open(cover_path, "wb") as f:
            f.write(data)
        return cover_path
    except Exception as e:  # noqa: BLE001 — cover 失败是合法状态
        logger.warning(f"cover download failed for {sha256}: {e}")
        return None


# ────────────────────────── single refresh ──────────────────────────

async def refresh_lora_metadata(
    session: Session, lora: Lora, client: Optional[CivitaiClient] = None
) -> Dict[str, Any]:
    path, loc_status = resolve_local_lora_file(session, lora)
    if loc_status != "ok":
        lora.metadata_status = loc_status
        session.add(lora)
        session.commit()
        detail = ("本地文件不存在或已移动" if loc_status == STATUS_LOCAL_FILE_NOT_FOUND
                  else "多个同名文件，无法确定目标")
        return {"status": loc_status, "detail": detail}

    sha256 = await _hash_or_reuse(lora, path)

    client = client or CivitaiClient()
    host_key = _target_host_key(lora)
    auth_warning = False
    version: Optional[Dict[str, Any]] = None
    used_host = host_key
    last_error: Optional[CivitaiRequestError] = None

    # 优先目标 host；仅当 404/网络错误 才 cross-host fallback 一次（spec §8/§9/§10）
    for idx, hk in enumerate([host_key, _OTHER_HOST.get(host_key, host_key)]):
        try:
            data, auth_warning = await client.lookup_by_hash(sha256, hk)
            if data:
                version, used_host = data, hk
                break
            break  # 200 空对象 → not_found，不跨站
        except CivitaiRequestError as e:
            last_error = e
            if e.status in (STATUS_NOT_FOUND, STATUS_REMOTE_ERROR) and idx == 0:
                continue
            break

    if version is None:
        if last_error and last_error.status == STATUS_RATE_LIMITED:
            status = STATUS_RATE_LIMITED
        elif last_error and last_error.status == STATUS_REMOTE_ERROR:
            status = STATUS_REMOTE_ERROR
        else:
            status = STATUS_NOT_FOUND
        lora.metadata_status = status
        session.add(lora)
        session.commit()
        return {"status": status, "auth_warning": auth_warning,
                "detail": last_error.detail if last_error else "两个官方 host 均未找到"}

    match_file = _matching_file(version, sha256)
    if match_file is None:
        lora.metadata_status = STATUS_HASH_FILE_MISMATCH
        session.add(lora)
        session.commit()
        return {"status": STATUS_HASH_FILE_MISMATCH, "auth_warning": auth_warning,
                "detail": "远端响应的 files 中没有与本地 SHA256 对应的文件"}

    model: Dict[str, Any] = {}
    try:
        if version.get("modelId"):
            model = await client.get_model(version["modelId"], used_host)
    except CivitaiRequestError as e:
        logger.warning(f"model lookup failed {version.get('modelId')}: {e}")

    cover_path = await _download_cover(client, version, used_host, sha256)

    _persist_remote(lora, version, match_file, model, used_host, sha256, cover_path)
    session.add(lora)
    session.commit()
    return {
        "status": STATUS_MATCHED,
        "auth_warning": auth_warning,
        "metadata_host": CIVITAI_HOST_NAMES[used_host],
        "remote_model_id": lora.remote_model_id,
        "remote_version_id": lora.remote_version_id,
        "remote_model_name": lora.remote_model_name,
        "remote_version_name": lora.remote_version_name,
        "remote_file_name": lora.remote_file_name,
        "remote_trained_words": lora.remote_trained_words,
        "cover_cached": lora.cached_cover_path is not None,
    }


# ────────────────────────── batch refresh ──────────────────────────

async def refresh_lora_metadata_batch(
    session: Session, ids: List[int], client: Optional[CivitaiClient] = None
) -> Dict[str, Any]:
    client = client or CivitaiClient()
    total = len(ids)
    matched: List[Dict[str, Any]] = []
    not_found: List[Dict[str, Any]] = []
    local_missing: List[Dict[str, Any]] = []
    local_ambiguous: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    auth_warning = False

    # 1) resolve + hash（顺序执行——单请求 session 最安全，也满足“不把 SSD 打满”）
    prep: List[Tuple[Lora, str, str]] = []   # (lora, sha, host_key)

    async def prep_one(lora: Lora) -> None:
        path, loc_status = resolve_local_lora_file(session, lora)
        if loc_status == STATUS_LOCAL_FILE_NOT_FOUND:
            local_missing.append({"id": lora.id, "name": lora.name})
            return
        if loc_status == STATUS_LOCAL_FILE_AMBIGUOUS:
            local_ambiguous.append({"id": lora.id, "name": lora.name})
            return
        sha256 = await _hash_or_reuse(lora, path)
        prep.append((lora, sha256, _target_host_key(lora)))

    for lid in ids:
        lora = session.get(Lora, lid)
        if lora is None:
            errors.append({"id": lid, "name": "", "detail": "记录不存在"})
            continue
        await prep_one(lora)

    # 2) 按 host 分组 → 每 100 个一批 bulk 查询（spec §12/§13）
    by_host: Dict[str, Dict[str, Lora]] = {}
    for lora, sha, hk in prep:
        by_host.setdefault(hk, {})[sha.lower()] = lora

    version_by_lora: Dict[int, Tuple[Dict[str, Any], Dict[str, Any], str]] = {}  # lora_id -> (version, file, host)
    for hk, sha_map in by_host.items():
        shas = list(sha_map.keys())
        for start in range(0, len(shas), 100):
            chunk = shas[start:start + 100]
            try:
                versions, warn = await client.lookup_by_hashes(chunk, hk)
                auth_warning = auth_warning or warn
            except CivitaiRequestError as e:
                # 网络/404 → 换另一个官方 host 一次；429 → 记 error
                if e.status == STATUS_RATE_LIMITED:
                    for s in chunk:
                        errors.append({"id": sha_map[s].id, "name": sha_map[s].name, "detail": "rate limited"})
                    continue
                other = _OTHER_HOST.get(hk, hk)
                try:
                    versions, warn = await client.lookup_by_hashes(chunk, other)
                    auth_warning = auth_warning or warn
                    for v in versions:
                        v["_host"] = other
                except CivitaiRequestError as e2:
                    for s in chunk:
                        errors.append({"id": sha_map[s].id, "name": sha_map[s].name,
                                       "detail": e2.detail or e.detail})
                    continue
                hk_used = other
            else:
                for v in versions:
                    v["_host"] = hk
                hk_used = hk

            for v in versions:
                host_used = v.pop("_host", hk_used)
                for f in v.get("files") or []:
                    h = ((f.get("hashes") or {}).get("SHA256") or "").lower()
                    if h in sha_map:
                        lora = sha_map[h]
                        version_by_lora[lora.id] = (v, f, host_used)

    # 3) modelId 去重（spec §14）
    model_cache: Dict[Tuple[str, int], Dict[str, Any]] = {}
    model_ids = {(host, v.get("modelId")) for v, _f, host in version_by_lora.values() if v.get("modelId")}
    sem_model = asyncio.Semaphore(COVER_SEMAPHORE)

    async def fetch_model(hk: str, mid: int) -> None:
        async with sem_model:
            try:
                model_cache[(hk, mid)] = await client.get_model(mid, hk)
            except CivitaiRequestError as e:
                logger.warning(f"batch model lookup failed {mid}: {e}")

    await asyncio.gather(*(fetch_model(hk, mid) for hk, mid in model_ids))

    # 4) cover 下载（并发 4）+ 持久化
    sem_cover = asyncio.Semaphore(COVER_SEMAPHORE)

    async def persist_one(lora_id: int) -> None:
        nonlocal auth_warning
        version, match_file, host_used = version_by_lora[lora_id]
        lora = session.get(Lora, lora_id)
        sha256 = lora.sha256 or ""
        async with sem_cover:
            cover_path = await _download_cover(client, version, host_used, sha256)
        model = model_cache.get((host_used, version.get("modelId"))) or {}
        _persist_remote(lora, version, match_file, model, host_used, sha256, cover_path)
        session.add(lora)
        matched.append({
            "id": lora.id, "name": lora.name,
            "metadata_host": lora.metadata_host,
            "remote_model_name": lora.remote_model_name,
            "cover_cached": lora.cached_cover_path is not None,
        })

    await asyncio.gather(*(persist_one(lid) for lid in version_by_lora))
    session.commit()

    # 5) 未匹配的 hash → not_found
    resolved_ids = set(version_by_lora.keys())
    for lora, sha, hk in prep:
        if lora.id not in resolved_ids:
            lora.metadata_status = STATUS_NOT_FOUND
            session.add(lora)
            not_found.append({"id": lora.id, "name": lora.name})
    session.commit()

    return {
        "total": total,
        "matched": matched,
        "not_found": not_found,
        "local_file_missing": local_missing,
        "local_file_ambiguous": local_ambiguous,
        "errors": errors,
        "auth_warning": auth_warning,
    }
