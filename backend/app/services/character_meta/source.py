"""Character metadata tag sources (V1).

Source contract: given a (mostly-English) character name query, return candidate
character metadata (canonical_tag + series_tag + caption_name + aliases) derived
from model-relevant tag corpora.

V1 source: Safebooru (gelbooru-family SFW booru, public API, reachable, no key).
  - tag search:  page=dapi&s=tag&q=index&name_pattern=<substring>  (XML)
  - post search: page=dapi&s=post&q=index&json=1&tags=<exact tag>   (JSON)
Algorithm (validated by experiment): find type-4 (character) tags matching the
name pattern → rank by post count → for the top candidates query posts and read
co-occurring copyright/series tags → canonical = base tag (strip “_(series)”
suffix, underscores→spaces), series = best co-occurring copyright tag
(disambiguator preferred, junk filtered), caption = per-word capitalized base.
Ambiguity: multiple strong candidates (top1 ≤ 5×top2) → return them all for the
user to choose (never silently pick).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Protocol
from xml.etree import ElementTree as ET

import httpx

# Tags that are copyright-ish but appear generically; plus known heavy franchises
# (the `_(` / `:` heuristics already catch most; this list is a light safety net).
_SERIES_HINTS = {
    "pokemon", "honkai: star rail", "honkai (series)", "wuthering waves",
    "genshin impact", "blue archive", "fate/grand order", "arknights",
    "nijisanji", "hololive", "vocaloid", "touhou", "puzzle and dragons",
    "girls frontline", "project sekai",
}
_GENERIC_TAGS = {"original", "western", "parody", "crossover", "solo", "multiple girls", "character name"}
_EMOTE_RE = re.compile(r"^:\S{0,4}$")      # :o / :d / :3 / :< / :-)
_DIGIT_START_RE = re.compile(r"^\d")      # 0.3::location etc.


@dataclass
class CharacterMetadata:
    canonical_tag: str = ""
    series_tag: str = ""
    caption_name: str = ""
    aliases: List[str] = field(default_factory=list)
    raw_tag: str = ""
    post_count: int = 0


class TagSource(Protocol):
    async def search(self, name: str) -> List[CharacterMetadata]: ...


def _normalize_query(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.lower().strip().replace(" ", "_"))


def _canonicalize(base: str) -> str:
    return base.strip().replace("_", " ")


def _caption_of(base: str) -> str:
    return " ".join((w[:1].upper() + w[1:]) for w in base.replace("_", " ").split() if w)


def _is_seriesish(tag: str, exclude: str) -> bool:
    if not tag or tag == exclude:
        return False
    if tag in _GENERIC_TAGS:
        return False
    if _EMOTE_RE.match(tag) or _DIGIT_START_RE.match(tag):
        return False
    if "_(" in tag or ":" in tag or tag in _SERIES_HINTS:
        return True
    return False


def _best_series(character_raw: str, all_co: Counter, series_co: Counter) -> str:
    """Pick the copyright/series tag. Preference order:
    1. exact normalized match against the character's “_(...)” disambiguator
       (searches ALL co-occurring tags so bare copyright like kantai_collection
       / wuthering_waves / pokemon are found even without “_(” or “:”)
    2. a tag containing ':' (specific franchise, e.g. honkai:_star_rail)
    3. highest-count series-ish tag (not an “x (series)” parent if a better one exists)
    """
    m = re.search(r"_\((.+?)\)$", character_raw)
    disamb = m.group(1).replace("_", " ").strip() if m else ""
    if disamb:
        for tag, _n in all_co.items():
            norm = tag.replace("_", " ").strip()
            if norm == disamb or norm.startswith(disamb):
                return norm
    # 裸 copyright（hints 已知系列）优先于“x: y”变体（pikachu → pokemon 而非
    # “pokemon the series: sun & moon”）
    hints_hits = [(n, t) for t, n in series_co.items()
                  if t.replace("_", " ").strip().lower() in {h.lower() for h in _SERIES_HINTS}]
    if hints_hits:
        hints_hits.sort(reverse=True)
        return hints_hits[0][1].replace("_", " ")
    specific = [(n, t) for t, n in all_co.items()
                if ":" in t and not _EMOTE_RE.match(t) and not _DIGIT_START_RE.match(t)]
    if specific:
        specific.sort(reverse=True)
        return specific[0][1].replace("_", " ")
    parents = [(n, t) for t, n in series_co.items() if t.endswith("(series)")]
    others = [(n, t) for t, n in series_co.items() if n > 0 and not t.endswith("(series)")]
    if others:
        others.sort(reverse=True)
        return others[0][1].replace("_", " ")
    if parents:
        parents.sort(reverse=True)
        return parents[0][1].replace("_", " ")
    return ""


class BooruTagSource:
    """Safebooru-based character metadata source."""

    def __init__(self, base_url: str = "https://safebooru.org/", timeout: float = 15.0, max_candidates: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_candidates = max_candidates

    async def _get_text(self, client: httpx.AsyncClient, params: dict) -> str:
        r = await client.get(f"{self.base_url}/index.php", params=params)
        r.raise_for_status()
        return r.text

    async def _tag_search(self, client: httpx.AsyncClient, pattern: str) -> List[dict]:
        try:
            text = await self._get_text(client, {"page": "dapi", "s": "tag", "q": "index", "name_pattern": pattern})
            root = ET.fromstring(text)
        except Exception:
            return []
        out = []
        for t in root.findall("tag"):
            if t.get("type") == "4":  # character
                try:
                    cnt = int(t.get("count") or 0)
                except ValueError:
                    cnt = 0
                out.append({"name": t.get("name"), "count": cnt})
        return out

    async def _posts_for(self, client: httpx.AsyncClient, tag: str, limit: int = 50) -> List[dict]:
        try:
            text = await self._get_text(client, {"page": "dapi", "s": "post", "q": "index", "json": "1", "tags": tag, "limit": str(limit)})
            return __import__("json").loads(text)
        except Exception:
            return []

    async def search(self, name: str) -> List[CharacterMetadata]:
        query = _normalize_query(name)
        if not query:
            return []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            char_tags = await self._tag_search(client, query)
            char_tags = [t for t in char_tags if t["count"] > 0]
            char_tags.sort(key=lambda t: -t["count"])
            candidates: List[CharacterMetadata] = []
            for ct in char_tags[: self.max_candidates]:
                posts = await self._posts_for(client, ct["name"])
                if not posts:
                    continue
                all_co = Counter()
                series_co = Counter()
                for p in posts:
                    for t in (p.get("tags") or "").split():
                        all_co[t] += 1
                        if _is_seriesish(t, ct["name"]):
                            series_co[t] += 1
                base = re.sub(r"_\(.+?\)$", "", ct["name"]).replace("_", " ")
                aliases = [re.sub(r"_\(.+?\)$", "", t["name"]).replace("_", " ")
                           for t in char_tags if t["name"] != ct["name"]][:5]
                candidates.append(CharacterMetadata(
                    canonical_tag=_canonicalize(base),
                    series_tag=_best_series(ct["name"], all_co, series_co),
                    caption_name=_caption_of(base),
                    aliases=[a for a in aliases if a and a != _canonicalize(base)],
                    raw_tag=ct["name"],
                    post_count=ct["count"],
                ))
            return candidates