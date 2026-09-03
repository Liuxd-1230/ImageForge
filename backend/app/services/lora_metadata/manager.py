"""LoRA Civitai metadata orchestration: single refresh + batch refresh (V1 closure).

Local-first ownership (spec §28): remote refresh NEVER overwrites
name / description / trigger_words / category / default_strength / is_favorite /
cover_hidden. Only fills the `remote_*` fields, sha256 cache and cover cache.

Tier layering:
- Tier 1 (stable Site API): by-hash identification + /models/{id} — 主链；
- Tier 2 (Civitai Web public tRPC modelVersion.getById): Usage Tips enrichment
  (settings.strength / clipSkip / steps / epochs)。tRPC 失败 → fail-open：
  metadata 仍 matched，只是 Usage 字段保持旧值/为空。
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
    safe_finite_float,
    safe_int,
    pick_cover_image,
    cover_ext_from_content_type,
)

logger = logging.getLogger(__name__)

_OTHER_HOST = {"red": "com", "com": "red"}
COVER_SEMAPHORE = 4     # cover 下载并发上限（spec §35）
ENRICH_SEMAPHORE = 6    # Tier-2 tRPC enrichment 并发上限（非主链，失败只缺 Usage Tips）


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
        "remote_model_description", "remote_version_description",
        "remote_recommended_strength", "remote_clip_skip",
        "remote_steps", "remote_epochs",
        "remote_creator", "remote_tags", "remote_nsfw_level",
        "cached_cover_path", "metadata_fetched_at", "metadata_json",
    ):
        setattr(lora, attr, None)


def _persist_remote(
    lora: Lora, version: Dict[str, Any], match_file: Dict[str, Any],
    model: Dict[str, Any], host_key: str, sha256: str, cover_path: Optional[str],
    version_detail: Optional[Dict[str, Any]] = None,
) -> None:
    """写远端字段 + hash 缓存 + 封面路径；本地用户字段一律不动。

    version_detail（Tier-2 tRPC enrichment）：
    - 提供时：Usage Tips 字段（strength/clipSkip/steps/epochs）按其权威值写入
      （远端明确 null → 本地 None）；
    - None（enrichment 失败/不可用）：fail-open，绝不清掉已存在的旧 Usage 值，
      trainedWords / version description 回退到 by-hash payload。
    """
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

    # Trigger Words：优先 enrichment trainedWords，fallback by-hash trainedWords（spec §17）
    tw = (version_detail or {}).get("trainedWords") or version.get("trainedWords") or []
    tw = [str(w) for w in tw if isinstance(w, str) and w.strip()] if isinstance(tw, list) else []
    lora.remote_trained_words = json.dumps(tw, ensure_ascii=False) if tw else None

    # 简介拆分（spec §5/§11/§12）：模型简介 ≠ 版本说明，不再混用一个字段
    model_desc = sanitize_description((model or {}).get("description"))
    version_desc = sanitize_description(
        (version_detail or {}).get("description") or version.get("description")
    )
    lora.remote_model_description = model_desc or None
    lora.remote_version_description = version_desc or None
    # legacy 兼容字段（deprecated，新 UI 不依赖）：保留旧 version-first 语义
    lora.remote_description = (version_desc or model_desc) or None

    # Usage Tips（Tier-2）：只有 enrichment 成功才权威写入；失败保留旧值（spec §18）
    if version_detail is not None:
        settings_obj = version_detail.get("settings")
        lora.remote_recommended_strength = (
            safe_finite_float(settings_obj.get("strength"))
            if isinstance(settings_obj, dict) else None
        )
        lora.remote_clip_skip = safe_int(version_detail.get("clipSkip"))
        lora.remote_steps = safe_int(version_detail.get("steps"))
        lora.remote_epochs = safe_int(version_detail.get("epochs"))

    lora.remote_creator = ((model or {}).get("creator") or {}).get("username") or None
    tags = (model or {}).get("tags") or []
    lora.remote_tags = json.dumps(tags, ensure_ascii=False) if tags else None
    lora.remote_nsfw_level = version.get("nsfwLevel") or ((model or {}).get("nsfwLevel")) or None
    lora.cached_cover_path = cover_path
    lora.metadata_fetched_at = datetime.utcnow()

    # metadata_json：normalized payload {version, model, version_detail}；
    # 不含 token / Authorization / 本地绝对路径；限制大小（spec §20/§65）
    safe_version = dict(version)
    safe_version.pop("downloadUrl", None)
    safe_model = {
        k: model.get(k)
        for k in ("id", "name", "type", "description", "creator", "tags", "nsfw", "nsfwLevel")
        if isinstance(model, dict) and model.get(k) is not None
    }
    safe_detail = None
    if isinstance(version_detail, dict):
        safe_detail = {
            k: version_detail.get(k)
            for k in ("id", "name", "description", "baseModel", "baseModelType",
                      "trainedWords", "epochs", "steps", "clipSkip", "settings")
            if version_detail.get(k) is not None
        }
    payload = {"version": safe_version, "model": safe_model, "version_detail": safe_detail}
    lora.metadata_json = json.dumps(payload, ensure_ascii=False)[:100_000]


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


async def _fetch_enrichment(
    client: CivitaiClient, version: Dict[str, Any], host_key: str
) -> Optional[Dict[str, Any]]:
    """Tier-2 tRPC enrichment — fail-open：任何失败返回 None，绝不影响 matched。"""
    vid = version.get("id")
    if not vid:
        return None
    try:
        return await client.get_model_version_enrichment(vid, host_key)
    except Exception as e:  # noqa: BLE001 — enrichment 失败是合法状态（spec §18）
        logger.warning(f"usage enrichment failed for version {vid}@{host_key}: {e}")
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

    # Tier-2 Usage Tips enrichment（fail-open）
    version_detail = await _fetch_enrichment(client, version, used_host)

    cover_path = await _download_cover(client, version, used_host, sha256)

    _persist_remote(lora, version, match_file, model, used_host, sha256, cover_path,
                    version_detail=version_detail)
    session.add(lora)
    session.commit()
    return {
        "status": STATUS_MATCHED,
        "auth_warning": auth_warning,
        "usage_enrichment": "ok" if version_detail is not None else "unavailable",
        "metadata_host": CIVITAI_HOST_NAMES[used_host],
        "remote_model_id": lora.remote_model_id,
        "remote_version_id": lora.remote_version_id,
        "remote_model_name": lora.remote_model_name,
        "remote_version_name": lora.remote_version_name,
        "remote_file_name": lora.remote_file_name,
        "remote_trained_words": lora.remote_trained_words,
        "remote_recommended_strength": lora.remote_recommended_strength,
        "remote_clip_skip": lora.remote_clip_skip,
        "cover_cached": lora.cached_cover_path is not None,
    }


# ────────────────────────── batch refresh ──────────────────────────
#
# Terminal outcome per LoRA（spec §23）：
#   matched | not_found | rate_limited | remote_error |
#   local_file_not_found | local_file_ambiguous
# not_found 只意味着：两个官方 host 都成功查询过且都没有该 SHA —— 绝不代表
# 网络错误 / 429 / 5xx（spec Batch Bug 3）。

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

    for lid in ids:
        lora = session.get(Lora, lid)
        if lora is None:
            errors.append({"id": lid, "name": "", "detail": "记录不存在"})
            continue
        path, loc_status = resolve_local_lora_file(session, lora)
        # Batch Bug 4：本地文件状态必须持久化（只改 status，不动旧 remote metadata）
        if loc_status == STATUS_LOCAL_FILE_NOT_FOUND:
            lora.metadata_status = STATUS_LOCAL_FILE_NOT_FOUND
            session.add(lora)
            local_missing.append({"id": lora.id, "name": lora.name})
            continue
        if loc_status == STATUS_LOCAL_FILE_AMBIGUOUS:
            lora.metadata_status = STATUS_LOCAL_FILE_AMBIGUOUS
            session.add(lora)
            local_ambiguous.append({"id": lora.id, "name": lora.name})
            continue
        sha256 = await _hash_or_reuse(lora, path)
        session.add(lora)
        prep.append((lora, sha256, _target_host_key(lora)))
    session.commit()

    # Batch Bug 2：sha → List[Lora]（同 SHA 多条 DB 记录共享一次远端 lookup）
    loras_by_sha: Dict[str, List[Lora]] = {}
    host_by_sha: Dict[str, str] = {}
    for lora, sha, hk in prep:
        s = sha.lower()
        loras_by_sha.setdefault(s, []).append(lora)
        host_by_sha.setdefault(s, hk)

    # 2) 每 host 分组 bulk；primary 命中的 sha 绝不发给 secondary（Batch Bug 1）
    version_by_sha: Dict[str, Tuple[Dict[str, Any], Dict[str, Any], str]] = {}
    terminal_error: Dict[str, Tuple[str, str]] = {}   # sha -> (status, detail)

    async def bulk_on_host(hk: str, shas: List[str]):
        """返回 (matched: sha->(version,file), missing, unknown, err, warn)。
        missing = host 成功应答但未包含；unknown = chunk 请求失败（未得到答案）。
        bulk 404 视为 host 权威应答「全部未找到」。"""
        matched_out: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
        missing: List[str] = []
        unknown: List[str] = []
        err: Optional[Tuple[str, str]] = None
        warn_any = False
        for start in range(0, len(shas), 100):
            chunk = shas[start:start + 100]
            chunk_set = set(chunk)
            try:
                versions, warn = await client.lookup_by_hashes(chunk, hk)
                warn_any = warn_any or warn
            except CivitaiRequestError as e:
                if e.status == STATUS_NOT_FOUND:
                    missing.extend(chunk)
                    continue
                unknown.extend(chunk)
                if err is None:
                    st = e.status if e.status == STATUS_RATE_LIMITED else STATUS_REMOTE_ERROR
                    err = (st, e.detail or "远端查询失败")
                continue
            got: set = set()
            for v in versions:
                for f in v.get("files") or []:
                    h = ((f.get("hashes") or {}).get("SHA256") or "").lower()
                    if h in chunk_set and h not in matched_out:
                        matched_out[h] = (v, f)
                        got.add(h)
            missing.extend(s for s in chunk if s not in got)
        return matched_out, missing, unknown, err, warn_any

    # host 分组：sha 的首选 host（同 sha 只查一次）
    shas_by_host: Dict[str, List[str]] = {}
    for s, hk in host_by_sha.items():
        shas_by_host.setdefault(hk, []).append(s)

    for hk, shas in shas_by_host.items():
        other = _OTHER_HOST.get(hk, hk)
        m1, miss1, unk1, err1, w1 = await bulk_on_host(hk, shas)
        auth_warning = auth_warning or w1
        for sha, vf in m1.items():
            version_by_sha[sha] = (vf[0], vf[1], hk)

        # primary 未确认的（missing + unknown）才发给 secondary —— 已匹配的绝不重发
        retry_shas = miss1 + unk1
        if not retry_shas:
            continue
        m2, miss2, unk2, err2, w2 = await bulk_on_host(other, retry_shas)
        auth_warning = auth_warning or w2
        for sha, vf in m2.items():
            version_by_sha[sha] = (vf[0], vf[1], other)

        # 终局分类：两 host 都权威应答「没有」→ not_found（保持默认，无 error 记录）；
        # 任一 host 没给出答案 → error（Batch Bug 3：error 绝不落入 not_found）
        answered_missing_both = set(miss1) & set(miss2)
        unresolved = set(retry_shas) - set(m2.keys()) - answered_missing_both
        if unresolved:
            errs = [e for e in (err1, err2) if e]
            st = (STATUS_RATE_LIMITED if any(e[0] == STATUS_RATE_LIMITED for e in errs)
                  else STATUS_REMOTE_ERROR)
            detail = errs[-1][1] if errs else "远端查询失败"
            for sha in unresolved:
                terminal_error[sha] = (st, detail)

    # 3) modelId 去重（spec §14）
    model_cache: Dict[Tuple[str, int], Dict[str, Any]] = {}
    model_ids = {(host, v.get("modelId")) for v, _f, host in version_by_sha.values() if v.get("modelId")}
    sem_model = asyncio.Semaphore(COVER_SEMAPHORE)

    async def fetch_model(hk: str, mid: int) -> None:
        async with sem_model:
            try:
                model_cache[(hk, mid)] = await client.get_model(mid, hk)
            except CivitaiRequestError as e:
                logger.warning(f"batch model lookup failed {mid}: {e}")

    await asyncio.gather(*(fetch_model(hk, mid) for hk, mid in model_ids))

    # 3b) Tier-2 Usage Tips enrichment：version_id 去重 + 有限并发；单条失败只缺 Usage Tips
    detail_cache: Dict[Tuple[str, int], Optional[Dict[str, Any]]] = {}
    version_ids = {(host, v.get("id")) for v, _f, host in version_by_sha.values() if v.get("id")}
    sem_enrich = asyncio.Semaphore(ENRICH_SEMAPHORE)

    async def fetch_detail(hk: str, vid: int) -> None:
        async with sem_enrich:
            version_stub = {"id": vid}
            detail_cache[(hk, vid)] = await _fetch_enrichment(client, version_stub, hk)

    await asyncio.gather(*(fetch_detail(hk, vid) for hk, vid in version_ids))

    # 4) cover 下载（并发 4，同 SHA 只下载一次）+ 持久化（同 SHA 应用到所有 LoRA）
    sem_cover = asyncio.Semaphore(COVER_SEMAPHORE)
    cover_by_sha: Dict[str, Optional[str]] = {}

    async def persist_one(sha: str) -> None:
        version, match_file, host_used = version_by_sha[sha]
        async with sem_cover:
            if sha not in cover_by_sha:
                cover_by_sha[sha] = await _download_cover(client, version, host_used, sha)
            cover_path = cover_by_sha[sha]
        model = model_cache.get((host_used, version.get("modelId"))) or {}
        detail = detail_cache.get((host_used, version.get("id")))
        for lora in loras_by_sha[sha]:
            _persist_remote(lora, version, match_file, model, host_used, sha, cover_path,
                            version_detail=detail)
            session.add(lora)
            matched.append({
                "id": lora.id, "name": lora.name,
                "metadata_host": lora.metadata_host,
                "remote_model_name": lora.remote_model_name,
                "cover_cached": lora.cached_cover_path is not None,
            })

    await asyncio.gather(*(persist_one(sha) for sha in version_by_sha))
    session.commit()

    # 5) 未匹配 hash 的终局状态：not_found（两 host 均权威应答）vs error（有 host 未应答）
    for sha, loras in loras_by_sha.items():
        if sha in version_by_sha:
            continue
        terr = terminal_error.get(sha)
        for lora in loras:
            if terr:
                lora.metadata_status = terr[0]
                session.add(lora)
                errors.append({"id": lora.id, "name": lora.name, "detail": terr[1]})
            else:
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
