import os
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.database import get_session
from app.models.lora import Lora, LoraCreate, LoraUpdate, LoraRead
from app.models.lora_source import LoraSource, LoraSourceCreate, LoraSourceUpdate, LoraSourceRead
from app.services.comfyui.client import ComfyUIClient
from app.services.pathutils import (
    source_identity,
    path_status,
    resolve_backend_path,
    safe_relative,
    join_within_root,
    match_comfy_lora,
)

router = APIRouter(prefix="/loras", tags=["loras"])

LORA_EXTENSIONS = (".safetensors", ".ckpt", ".pt")


# ─────────────────────────────── 基础 CRUD ───────────────────────────────

@router.get("", response_model=List[LoraRead])
def list_loras(
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    stmt = select(Lora)
    if category:
        stmt = stmt.where(Lora.category == category)
    if is_favorite is not None:
        stmt = stmt.where(Lora.is_favorite == is_favorite)
    return session.exec(stmt).all()


@router.post("", response_model=LoraRead)
def create_lora(lora_in: LoraCreate, session: Session = Depends(get_session)):
    lora = Lora.model_validate(lora_in)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    return lora


@router.put("/{lora_id}", response_model=LoraRead)
def update_lora(
    lora_id: int,
    lora_in: LoraUpdate,
    session: Session = Depends(get_session)
):
    lora = session.get(Lora, lora_id)
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA不存在")
    data = lora_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(lora, key, value)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    return lora


@router.delete("/{lora_id}")
def delete_lora(lora_id: int, session: Session = Depends(get_session)):
    lora = session.get(Lora, lora_id)
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA不存在")
    session.delete(lora)
    session.commit()
    return {"status": "ok"}


# ────────────────── ComfyUI 同步：只校验，不再自动导入 ──────────────────
# ComfyUI `/models/loras` / `object_info/LoraLoader` 是「是否被 ComfyUI 识别」的
# 权威来源，但不再等于「ImageForge 要导入的全部 LoRA」。导入必须走来源扫描两阶段流程。

@router.post("/sync-comfyui")
async def sync_comfyui_loras(session: Session = Depends(get_session)):
    client = ComfyUIClient()
    comfy_loras = await client.get_loras()
    comfy_norm = {n.replace("\\", "/") for n in comfy_loras}
    comfy_basenames = {n.split("/")[-1] for n in comfy_norm}

    existing = session.exec(select(Lora)).all()
    changed = 0
    for rec in existing:
        f = (rec.filename or "").replace("\\", "/")
        valid = f in comfy_norm or f.split("/")[-1] in comfy_basenames
        if rec.is_valid_file != valid:
            rec.is_valid_file = valid
            session.add(rec)
            changed += 1
    session.commit()
    return {
        "status": "ok",
        "comfy_recognized_total": len(comfy_loras),
        "library_total": len(existing),
        "validity_updated": changed,
    }


# ─────────────────────────────── 来源管理 ───────────────────────────────

def _source_status(src: LoraSource) -> dict:
    st = path_status(src.resolved_path)
    return {
        "id": src.id,
        "display_path": src.display_path,
        "resolved_path": src.resolved_path,
        "enabled": src.enabled,
        "recursive": src.recursive,
        "created_at": src.created_at.isoformat() if src.created_at else None,
        **st,
    }


@router.get("/sources")
def list_sources(session: Session = Depends(get_session)):
    sources = session.exec(select(LoraSource).order_by(LoraSource.id)).all()
    return [_source_status(s) for s in sources]


@router.post("/sources", status_code=201)
def add_source(payload: LoraSourceCreate, session: Session = Depends(get_session)):
    display, resolved = source_identity(payload.display_path)
    if not resolved:
        raise HTTPException(status_code=400, detail="路径不能为空")

    st = path_status(resolved)
    if not st["exists"] or not st["is_dir"]:
        raise HTTPException(status_code=400, detail=f"路径无效：{st['error']}（解析后：{resolved}）")
    if not st["readable"]:
        raise HTTPException(status_code=400, detail=f"目录不可读：{resolved}")

    # 去重：按 resolved 路径（已 realpath/normpath 规范化）
    existing = session.exec(select(LoraSource)).all()
    for src in existing:
        if src.resolved_path == resolved:
            raise HTTPException(status_code=409, detail=f"该来源已存在（{src.display_path}）")

    src = LoraSource(
        display_path=display,
        resolved_path=resolved,
        enabled=payload.enabled,
        recursive=payload.recursive,
    )
    session.add(src)
    session.commit()
    session.refresh(src)
    return _source_status(src)


@router.put("/sources/{source_id}")
def update_source(source_id: int, payload: LoraSourceUpdate, session: Session = Depends(get_session)):
    src = session.get(LoraSource, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="来源不存在")
    if payload.enabled is not None:
        src.enabled = payload.enabled
    if payload.recursive is not None:
        src.recursive = payload.recursive
    session.add(src)
    session.commit()
    session.refresh(src)
    return _source_status(src)


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, session: Session = Depends(get_session)):
    """删除来源本身，不删除已经导入整理的 LoRA 库记录（两个独立操作）。"""
    src = session.get(LoraSource, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="来源不存在")
    session.delete(src)
    session.commit()
    return {"status": "ok", "deleted_source": src.display_path}


# ─────────────────────────── 扫描（预览，不改库） ───────────────────────────

def _human_name_from_file(relative_path: str) -> str:
    import os as _os
    stem = _os.path.splitext(_os.path.basename(relative_path.replace("/", _os.sep)))[0]
    return stem.replace("_", " ").replace("-", " ").replace(".", " ").title()


def _walk_lora_files(root: str, recursive: bool) -> List[str]:
    """Collect lora-weight files. os.walk(followlinks=False) => no symlink loops."""
    found: List[str] = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames.sort()
            for fn in filenames:
                if fn.lower().endswith(LORA_EXTENSIONS):
                    found.append(os.path.join(dirpath, fn))
    else:
        try:
            for fn in os.listdir(root):
                full = os.path.join(root, fn)
                if os.path.isfile(full) and fn.lower().endswith(LORA_EXTENSIONS):
                    found.append(full)
        except Exception:
            pass
    return sorted(found)


def _comfy_basenames(comfy_norm: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for n in comfy_norm:
        b = n.split("/")[-1]
        counts[b] = counts.get(b, 0) + 1
    return counts


def _match_comfy(rel: str, basename: str, comfy_norm: List[str], comfy_basenames: Dict[str, int], ambiguous: bool = False) -> Optional[str]:
    """Server-authoritative ComfyUI recognition for a candidate.

    - exact / relative-subfolder match wins;
    - basename fallback ONLY when unambiguous: exactly one ComfyUI entry has
      that basename AND the candidate basename isn't shared by another file in
      the same batch (`ambiguous=True` from caller). This prevents two
      same-named files in different dirs from both being marked recognized.
    """
    m = match_comfy_lora(rel, basename, comfy_norm)
    if m:
        return m
    if not ambiguous and comfy_basenames.get(basename, 0) == 1:
        for n in comfy_norm:
            if n.split("/")[-1] == basename:
                return n
    return None


async def _fetch_comfy_loras(client: Optional[ComfyUIClient] = None) -> tuple[bool, List[str]]:
    """Return (comfy_available, lora_names). Offline detection uses an explicit
    health check — get_loras() swallows connection errors and returns []."""
    client = client or ComfyUIClient()
    try:
        health = await client.check_health()
        if health.get("status") != "connected":
            return False, []
        loras = await client.get_loras()
        return True, loras
    except Exception:
        return False, []


def _other_sources_basenames(session: Session, exclude_id: int) -> set:
    """Collect basenames of lora files from all OTHER enabled sources, for
    cross-source same-basename conflict detection."""
    others = session.exec(
        select(LoraSource).where(LoraSource.enabled == True, LoraSource.id != exclude_id)  # noqa: E712
    ).all()
    result = set()
    for s in others:
        st = path_status(s.resolved_path)
        if not st["exists"] or not st["is_dir"] or not st["readable"]:
            continue
        for full in _walk_lora_files(s.resolved_path, s.recursive):
            result.add(os.path.basename(full).lower())
    return result


@router.post("/sources/{source_id}/scan")
async def scan_source(source_id: int, session: Session = Depends(get_session)):
    src = session.get(LoraSource, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="来源不存在")
    if not src.enabled:
        raise HTTPException(status_code=400, detail="该来源已停用，请先启用")

    st = path_status(src.resolved_path)
    if not st["exists"] or not st["is_dir"]:
        raise HTTPException(status_code=400, detail=f"来源路径不可访问：{src.resolved_path}")

    comfy_available, comfy_loras = await _fetch_comfy_loras()
    comfy_norm = [n.replace("\\", "/") for n in comfy_loras]
    comfy_basenames = _comfy_basenames(comfy_norm)

    db_records = session.exec(select(Lora)).all()
    db_filenames = {(r.filename or "").replace("\\", "/") for r in db_records}
    db_with_source = [
        ((r.filename or "").replace("\\", "/"), (r.source_path or ""))
        for r in db_records if r.source_path
    ]
    db_legacy = [(r.filename or "").replace("\\", "/") for r in db_records if not r.source_path]

    def exists_in_db(rel: str, basename: str, full_path: str) -> bool:
        """存在判定：文件标识精确匹配；有 source_path 的记录按真实路径匹配；
        仅对无 source_path 的旧记录回退 basename 匹配（不把「同名不同文件」误判为已存在）。"""
        if rel in db_filenames:
            return True
        for fn, sp in db_with_source:
            if sp == full_path:
                return True
        for fn in db_legacy:
            if fn == rel or fn.split("/")[-1] == basename:
                return True
        return False

    files = _walk_lora_files(src.resolved_path, src.recursive)
    rels = [os.path.relpath(full, src.resolved_path).replace("\\", "/") for full in files]
    basename_counts = Counter(r.split("/")[-1].lower() for r in rels)
    foreign_basenames = _other_sources_basenames(session, src.id)

    candidates = []
    for full, rel in zip(files, rels):
        basename = rel.split("/")[-1]
        basename_l = basename.lower()
        ambiguous = basename_counts[basename_l] > 1 or basename_l in foreign_basenames
        comfy_name = _match_comfy(rel, basename, comfy_norm, comfy_basenames, ambiguous=ambiguous)
        candidates.append({
            "relative_path": rel,
            "basename": basename,
            "full_path": full,
            "name_hint": _human_name_from_file(rel),
            "exists_in_db": exists_in_db(rel, basename, full),
            "comfy_recognized": comfy_name is not None,
            "comfy_name": comfy_name or rel,
            "basename_conflict": ambiguous,
        })

    summary = {
        "total": len(candidates),
        "already_imported": sum(1 for c in candidates if c["exists_in_db"]),
        "new": sum(1 for c in candidates if not c["exists_in_db"]),
        "comfy_unrecognized": sum(1 for c in candidates if not c["comfy_recognized"]),
        "basename_conflicts": sum(1 for c in candidates if c["basename_conflict"]),
        "comfy_available": comfy_available,
    }
    return {"source": _source_status(src), "candidates": candidates, "summary": summary}


# ─────────────────── 导入所选：服务端权威重验（source_id + relative_paths） ───────────────────
# 前端只提交 source_id 与相对路径；路径归属/存在/扩展名/ComfyUI 识别/重复/冲突
# 全部在服务端重新判定，扫描结果只是 UI 预览。

class ImportRequest(BaseModel):
    source_id: int
    relative_paths: List[str]


@router.post("/import")
async def import_selected(payload: ImportRequest, session: Session = Depends(get_session)):
    src = session.get(LoraSource, payload.source_id)
    if not src:
        raise HTTPException(status_code=400, detail="来源不存在")
    if not src.enabled:
        raise HTTPException(status_code=400, detail="来源已停用，请先启用")
    st = path_status(src.resolved_path)
    if not st["exists"] or not st["is_dir"]:
        raise HTTPException(status_code=400, detail="来源路径不可访问，请重新扫描")

    # 服务端重新查询 ComfyUI 识别名单（权威，不信任前端）
    comfy_available, comfy_loras = await _fetch_comfy_loras()
    comfy_norm = [n.replace("\\", "/") for n in comfy_loras]
    comfy_basenames = _comfy_basenames(comfy_norm)

    # 服务端重新建立重复集合（循环内即时更新，绝不允许同 filename 一次请求重复写入）
    db_records = session.exec(select(Lora)).all()
    db_filenames = {(r.filename or "").replace("\\", "/") for r in db_records}
    db_src_paths = {(r.source_path or "") for r in db_records if r.source_path}
    db_legacy_basenames = {
        (r.filename or "").replace("\\", "/").split("/")[-1]
        for r in db_records if not r.source_path
    }
    seen_filenames: set = set()
    seen_src_paths: set = set()
    request_basenames = Counter(
        ((safe_relative(r) or "").split("/")[-1] or "").lower() for r in payload.relative_paths
    )
    foreign_basenames = _other_sources_basenames(session, payload.source_id)

    imported = []
    skipped = []
    errors = []

    for raw_rel in payload.relative_paths:
        rel = safe_relative(raw_rel)
        if rel is None:
            errors.append({"relative_path": raw_rel, "reason": "路径不合法或越界"})
            continue

        # 1) 归属校验：realpath(root/rel) 必须仍在 source root 内
        full = join_within_root(src.resolved_path, rel)
        if full is None:
            errors.append({"relative_path": rel, "reason": "路径越界，已拒绝"})
            continue
        # 2) 文件必须仍然存在（目录变化 / stale 前端）
        if not os.path.isfile(full):
            errors.append({"relative_path": rel, "reason": "文件不存在或已移动，请重新扫描"})
            continue
        # 3) 扩展名
        if not full.lower().endswith(LORA_EXTENSIONS):
            errors.append({"relative_path": rel, "reason": "不是支持的 LoRA 权重文件"})
            continue

        basename = rel.split("/")[-1]
        ambiguous = request_basenames[basename.lower()] > 1 or basename.lower() in foreign_basenames
        comfy_name = _match_comfy(rel, basename, comfy_norm, comfy_basenames, ambiguous=ambiguous)
        filename = (comfy_name or rel).replace("\\", "/")

        # 4) 重复判定（DB + 本请求内已导入项）
        if filename in db_filenames or filename in seen_filenames:
            skipped.append({"relative_path": rel, "reason": "已存在"})
            continue
        if full in db_src_paths or full in seen_src_paths:
            skipped.append({"relative_path": rel, "reason": "已存在"})
            continue
        if basename in db_legacy_basenames:
            skipped.append({"relative_path": rel, "reason": "已存在（同名旧记录）"})
            continue

        lora = Lora(
            name=_human_name_from_file(rel),
            filename=filename,
            trigger_words="",
            default_strength=0.8,
            is_favorite=False,
            category="通用",
            is_valid_file=comfy_name is not None,
            source_path=full,
        )
        session.add(lora)
        # 即时更新去重集合
        db_filenames.add(filename)
        seen_filenames.add(filename)
        db_src_paths.add(full)
        seen_src_paths.add(full)
        imported.append({"relative_path": rel, "filename": filename, "comfy_recognized": comfy_name is not None})

    session.commit()
    return {
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "comfy_available": comfy_available,
    }


# ─────────────────── 路径解析预览（WSL 判定以后端为准） ───────────────────

class ResolvePathRequest(BaseModel):
    display_path: str


@router.post("/resolve-path")
def resolve_path_preview(payload: ResolvePathRequest):
    display, resolved = source_identity(payload.display_path)
    st = path_status(resolved)
    count = 0
    if st["exists"] and st["is_dir"] and st["readable"]:
        count = len(_walk_lora_files(resolved, recursive=True))
    return {
        "display_path": display,
        "resolved_path": resolved,
        "lora_file_count": count,
        **st,
    }
