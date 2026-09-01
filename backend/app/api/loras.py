import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.database import get_session
from app.models.lora import Lora, LoraCreate, LoraUpdate, LoraRead
from app.models.lora_source import LoraSource, LoraSourceCreate, LoraSourceUpdate, LoraSourceRead
from app.services.comfyui.client import ComfyUIClient
from app.services.pathutils import source_identity, path_status, resolve_backend_path

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

    # ComfyUI 识别名单（扫描权威，失败则全部标未识别）
    comfy_loras: List[str] = []
    comfy_available = True
    try:
        client = ComfyUIClient()
        comfy_loras = await client.get_loras()
    except Exception:
        comfy_available = False
    comfy_norm = [n.replace("\\", "/") for n in comfy_loras]
    comfy_basenames = {n.split("/")[-1] for n in comfy_norm}

    def match_comfy(rel: str, basename: str) -> Optional[str]:
        for n in comfy_norm:
            if n == rel or n.endswith("/" + rel):
                return n
        if basename in comfy_basenames:
            return basename
        return None

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
    candidates = []
    for full in files:
        rel = os.path.relpath(full, src.resolved_path).replace("\\", "/")
        basename = rel.split("/")[-1]
        comfy_name = match_comfy(rel, basename)
        candidates.append({
            "relative_path": rel,
            "basename": basename,
            "full_path": full,
            "name_hint": _human_name_from_file(rel),
            "exists_in_db": exists_in_db(rel, basename, full),
            "comfy_recognized": comfy_name is not None,
            "comfy_name": comfy_name or rel,
            "basename_conflict": False,
        })

    # 重名冲突：同一 basename 在本轮候选里出现多次（多来源同名）
    by_basename: Dict[str, int] = {}
    for c in candidates:
        by_basename[c["basename"]] = by_basename.get(c["basename"], 0) + 1
    for c in candidates:
        if by_basename[c["basename"]] > 1:
            c["basename_conflict"] = True

    summary = {
        "total": len(candidates),
        "already_imported": sum(1 for c in candidates if c["exists_in_db"]),
        "new": sum(1 for c in candidates if not c["exists_in_db"]),
        "comfy_unrecognized": sum(1 for c in candidates if not c["comfy_recognized"]),
        "basename_conflicts": sum(1 for c in candidates if c["basename_conflict"]),
        "comfy_available": comfy_available,
    }
    return {"source": _source_status(src), "candidates": candidates, "summary": summary}


# ─────────────────────────── 导入所选（显式勾选） ───────────────────────────

class ImportItem(BaseModel):
    relative_path: str
    full_path: str
    comfy_name: str
    comfy_recognized: bool = False
    name_hint: Optional[str] = None


class ImportRequest(BaseModel):
    items: List[ImportItem]


@router.post("/import")
def import_selected(payload: ImportRequest, session: Session = Depends(get_session)):
    imported = []
    skipped = []
    errors = []

    db_records = session.exec(select(Lora)).all()
    db_filenames = {(r.filename or "").replace("\\", "/") for r in db_records}
    db_with_source = [
        ((r.filename or "").replace("\\", "/"), (r.source_path or ""))
        for r in db_records if r.source_path
    ]
    db_legacy = [(r.filename or "").replace("\\", "/") for r in db_records if not r.source_path]

    for item in payload.items:
        rel = item.relative_path.replace("\\", "/")
        basename = rel.split("/")[-1]
        filename = (item.comfy_name or rel).replace("\\", "/")

        exists = (
            filename in db_filenames
            or any(sp == item.full_path for _, sp in db_with_source)
            or any(fn == rel or fn.split("/")[-1] == basename for fn in db_legacy)
        )
        if exists:
            skipped.append({"relative_path": rel, "reason": "已存在"})
            continue

        if not os.path.isfile(item.full_path):
            errors.append({"relative_path": rel, "reason": "文件不存在"})
            continue

        lora = Lora(
            name=item.name_hint or _human_name_from_file(rel),
            filename=filename,
            trigger_words="",
            default_strength=0.8,
            is_favorite=False,
            category="通用",
            is_valid_file=item.comfy_recognized,
            source_path=item.full_path,
        )
        session.add(lora)
        imported.append({"relative_path": rel, "filename": filename})

    session.commit()
    return {"status": "ok", "imported": imported, "skipped": skipped, "errors": errors}
