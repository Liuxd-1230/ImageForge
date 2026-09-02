"""Online character resolver orchestrator (V1).

Responsibilities:
- run the resolution chain against a tag source,
- transliterate CJK names to candidate English names via the local LLM,
- decide resolved / ambiguous / not_found / offline,
- write results into CharacterTriggerCache with source="online",
- honour manual overrides (source="manual" is never overwritten for non-empty
  fields unless `force` is set — online only fills missing fields),
- never raise into the parse path (offline/failure ⇒ existing LLM fallback).
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models.trigger_cache import CharacterTriggerCache
from app.services.character_meta.source import TagSource, CharacterMetadata

logger = logging.getLogger(__name__)

TRANSLIT_PROMPT = (
    "Given this anime/game character name (possibly Chinese/Japanese), list 1-3 likely "
    "English character-tag candidates used on image boorus (lowercase, one per line, no numbering).\n"
    "Name: {name}"
)

PINYIN_PROMPT = "Output the pinyin romanization of this Chinese name (lowercase, no tones, no spaces): {name}"

# resolved 所需的最低证据（帖数）。非 confidence 系统——仅避免「LLM 幻觉一个冷门 tag」被当唯一结论。
MIN_POST_COUNT_FOR_RESOLVED = 10

_AMBIGUOUS_RATIO = 5.0  # top1 count must be >= ratio × top2 to be considered unambiguous


def _normalize_name(name: str) -> str:
    return (name or "").strip()


def _is_ambiguous(cands: List[CharacterMetadata]) -> bool:
    if len(cands) < 2:
        return False
    top1, top2 = cands[0].post_count, cands[1].post_count
    return not (top1 >= _AMBIGUOUS_RATIO * max(top2, 1))


class OnlineCharacterResolver:
    def __init__(
        self,
        session: Session,
        source: Optional[TagSource] = None,
        llm_provider: Any = None,
        write_cache: bool = True,
        model: Optional[str] = None,
    ):
        self.session = session
        self.source = source
        self.llm_provider = llm_provider
        self.write_cache = write_cache
        self.model = model
        self._last_pinyin = ""

    # ── cache IO ────────────────────────────────────────────────────────────
    def get_cache(self, name: str) -> Optional[CharacterTriggerCache]:
        stmt = select(CharacterTriggerCache).where(CharacterTriggerCache.name == _normalize_name(name))
        return self.session.exec(stmt).first()

    def _write(self, name: str, meta: CharacterMetadata, force: bool = False) -> CharacterTriggerCache:
        """Write an online result into the cache.

        manual rows: non-empty fields are preserved; only empty fields are filled
        unless `force=True` (user explicitly chose “重新解析并替换”).
        """
        name = _normalize_name(name)
        existing = self.get_cache(name)
        if existing is None:
            row = CharacterTriggerCache(
                name=name,
                canonical_tag=meta.canonical_tag,
                caption_name=meta.caption_name or name,
                series_tag=meta.series_tag or None,
                aliases=", ".join(meta.aliases),
                source="online",
                resolved_at=datetime.utcnow(),
            )
            self.session.add(row)
            self.session.commit()
            return row

        def put(field: str, value: Optional[str]) -> None:
            if force:
                setattr(existing, field, value)
            else:
                cur = getattr(existing, field)
                if not cur and value:
                    setattr(existing, field, value)

        put("canonical_tag", meta.canonical_tag)
        put("caption_name", meta.caption_name or name)
        put("series_tag", meta.series_tag or None)
        aliases = ", ".join(meta.aliases)
        put("aliases", aliases)
        if existing.source != "manual":
            existing.source = "online"
        existing.resolved_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        self.session.add(existing)
        self.session.commit()
        return existing

    # ── LLM transliteration (CJK → English candidates) ──────────────────────
    async def _chat_line(self, prompt: str) -> Optional[str]:
        if not self.llm_provider:
            return None
        try:
            return await self.llm_provider.chat(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                reasoning_effort="off",
            )
        except Exception as e:
            logger.warning(f"online resolver LLM call failed: {e}")
            return None

    async def _pinyin_of(self, name: str) -> str:
        """汉字名 → 无调号无空格拼音（如 穗穗 → suisui）。失败/无意义返回 ''。"""
        raw = await self._chat_line(PINYIN_PROMPT.format(name=name))
        if not raw:
            return ""
        import unicodedata
        norm = unicodedata.normalize("NFKD", raw)
        norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
        flat = re.sub(r"[^a-z]+", "", norm.lower()).strip()
        return flat[:24] if len(flat) >= 2 else ""

    async def _english_candidates(self, name: str) -> List[str]:
        # 已像英文 tag 的名字直接用；仅 CJK 需要本地 LLM 转写候选
        if re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", name):
            self._last_pinyin = ""
            if not self.llm_provider:
                return []
            out = []
            raw = await self._chat_line(TRANSLIT_PROMPT.format(name=name))
            if raw:
                for line in raw.splitlines():
                    line = line.strip().lstrip("-•0123456789. ").strip()
                    if not line or re.search(r"[\u4e00-\u9fff]", line):
                        continue
                    low = line.lower()
                    if low in ("unknown", "not found", "n/a", "na", "none") or low == name.lower():
                        continue
                    out.append(line)
            # 拼音是额外的可靠候选（真实角色 tag 常＝拼音，如 穗穗→suisui）
            pinyin = await self._pinyin_of(name)
            self._last_pinyin = pinyin
            if pinyin and pinyin not in out:
                out.append(pinyin)
            seen, uniq = set(), []
            for c in out:
                k = c.lower()
                if k not in seen:
                    seen.add(k)
                    uniq.append(c)
            return uniq[:4]
        self._last_pinyin = ""
        return [name]

    # ── main resolve ────────────────────────────────────────────────────────
    async def resolve(self, name: str) -> Dict[str, Any]:
        """Run the online chain. Never raises.

        Returns one of:
          {"status": "resolved",   "result": {canonical_tag, series_tag, caption_name, aliases}}
          {"status": "ambiguous",  "candidates": [...]}
          {"status": "not_found"}
          {"status": "offline",    "reason": ...}
        """
        name = _normalize_name(name)
        if not name or not self.source:
            return {"status": "offline", "reason": "online resolve not available"}
        try:
            cand_names = await self._english_candidates(name)
        except Exception:
            cand_names = []
        if not cand_names:
            return {"status": "offline", "reason": "remote unavailable"}

        merged: Dict[str, CharacterMetadata] = {}
        for cand in cand_names:
            try:
                found = await self.source.search(cand)
            except Exception as e:
                logger.warning(f"source search failed for {cand}: {e}")
                continue
            for m in found:
                key = (m.canonical_tag.lower(), m.series_tag.lower())
                if key in merged:
                    merged[key].post_count = max(merged[key].post_count, m.post_count)
                else:
                    merged[key] = m
        cands = sorted(merged.values(), key=lambda m: -m.post_count)
        if not cands:
            return {"status": "not_found"}

        # 拼音精确命中加权：若某个候选的 canonical 与本次拼音完全一致（如 suisui），
        # 说明它就是名字本身的罗马字，优先级高于同音同名的热门角色（suiseiseki 等）。
        if self._last_pinyin:
            boost = [m for m in cands
                     if m.canonical_tag.replace(" ", "").lower() == self._last_pinyin.lower()]
            if boost:
                top_pin = boost[0]
                top_pin.post_count = max(top_pin.post_count, (cands[0].post_count if cands else 0) * 2)
                cands.sort(key=lambda m: -m.post_count)

        if _is_ambiguous(cands):
            return {"status": "ambiguous", "candidates": [self._encode(m) for m in cands[:5]]}
        top = cands[0]
        if top.post_count < MIN_POST_COUNT_FOR_RESOLVED:
            # 唯一候选但证据过低（LLM 幻觉/冷门泛指 tag）→ 当作未找到，避免把错结论写进缓存
            return {"status": "not_found", "reason": f"evidence too low ({top.post_count} posts)"}
        if self.write_cache:
            self._write(name, top)
        return {"status": "resolved", "result": self._encode(top)}

    async def confirm(self, name: str, candidate: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """User picked one candidate → write cache → return resolved.

        force=False（默认，普通候选选择）：manual 非空字段不覆盖，只补空字段；
        force=True（“重新解析并替换”）才允许覆盖 manual 非空值。"""
        meta = CharacterMetadata(
            canonical_tag=candidate.get("canonical_tag", ""),
            series_tag=candidate.get("series_tag", "") or None,
            caption_name=candidate.get("caption_name", "") or name,
            aliases=candidate.get("aliases") or [],
        )
        if self.write_cache:
            self._write(name, meta, force=force)
        return {"status": "resolved", "result": self._encode(meta)}

    # ── pipeline helpers (backfill) ─────────────────────────────────────────
    async def backfill(self, name: str, existing_canonical: Optional[str] = None) -> bool:
        """Best-effort cache backfill used by the parse pipeline.

        - existing_canonical is set: only need the series tag (patch);
        - otherwise resolve fully and cache.
        Returns True if the cache row is now complete (canonical + series).
        """
        try:
            if existing_canonical:
                cand_names = await self._english_candidates(name) or [existing_canonical]
                for cand in cand_names:
                    found = await self.source.search(cand)
                    for m in found:
                        if m.canonical_tag.lower() == existing_canonical.lower() and m.series_tag:
                            self._write(name, m)
                            return True
                    if found and found[0].series_tag:
                        self._write(name, found[0])
                        return True
                return False
            outcome = await self.resolve(name)
            return outcome.get("status") == "resolved"
        except Exception as e:
            logger.warning(f"online backfill failed for {name}: {e}")
            return False

    @staticmethod
    def _encode(m: CharacterMetadata) -> Dict[str, Any]:
        return {
            "canonical_tag": m.canonical_tag,
            "series_tag": m.series_tag or "",
            "caption_name": m.caption_name,
            "aliases": m.aliases,
        }


async def run_with_timeout(coro, timeout: float = 25.0):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except (asyncio.TimeoutError, Exception):
        return None