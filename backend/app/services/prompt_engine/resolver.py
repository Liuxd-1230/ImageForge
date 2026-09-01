import json
import re
import logging
from typing import List, Optional, Tuple, Dict
from sqlmodel import Session, select
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.prompt_engine import Entity, Statement
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

RESOLVER_SYSTEM_PROMPT = """You are an anime character tag resolver for the Anima image generation model.
Given a list of anime / manga / game character names (in Chinese or Japanese or English), return the standard Danbooru / Gelbooru canonical character tag (lowercase with underscores) and the English display name for captions.

OUTPUT SCHEMA (JSON ONLY):
{
  "characters": [
    {
      "name": "穗穗",
      "canonical_tag": "suisui",
      "caption_name": "Suisui"
    },
    {
      "name": "希露菲",
      "canonical_tag": "sylphiette",
      "caption_name": "Sylphiette"
    }
  ]
}

If a character has a series tag (e.g. "asuka_langley_(evangelion)"), provide the primary character trigger tag.
Do NOT invent extra appearance tags or clothing. Return ONLY the character tag and caption name in JSON.
"""

class CharacterResolver:
    def __init__(self, session: Session, llm_provider: Optional[BaseLLMProvider] = None):
        self.session = session
        self.llm_provider = llm_provider

    def _build_caption_name(self, char: Character) -> str:
        gender_str = (char.gender or "").strip().lower()
        if "man" in gender_str and "wo" not in gender_str:
            gender_base = "man"
        elif "woman" in gender_str or "girl" in gender_str:
            gender_base = "woman"
        else:
            gender_base = "character"

        age = "young " if "young" in (char.age_group or "") else ""
        distinct = ""
        if char.hair_color:
            distinct = f" with {char.hair_color} hair"
        elif char.hair_style:
            distinct = f" with {char.hair_style} hair"
        return f"the {age}{gender_base}{distinct}".strip()

    async def resolve_entities_async(
        self,
        entities: List[Entity],
        statements: List[Statement],
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = "instruct"
    ) -> List[Entity]:
        """Resolves entities: Character Book lookup -> Cache lookup -> Batch LLM Trigger resolution."""
        resolved: List[Entity] = []
        unresolved_model_chars: List[Entity] = []

        for entity in entities:
            # 1. Check Character Book
            char = self._find_in_character_book(entity.name)
            if char:
                entity.source = "user_defined"
                entity.canonical_tag = None
                entity.caption_name = self._build_caption_name(char)

                replaced_facets = set()
                for s in statements:
                    if s.subject == entity.id:
                        # ONLY suppress default attribute if effect is explicitly 'replace'
                        if s.effect and s.effect.lower() == "replace":
                            if s.facet:
                                replaced_facets.add(s.facet.lower())
                            if any(w in s.text.lower() for w in ["wearing", "swimsuit", "uniform", "raincoat"]):
                                replaced_facets.add("outfit")
                            if any(w in s.text.lower() for w in ["hair", "ponytail", "twintails"]):
                                replaced_facets.add("hairstyle")

                entity.custom_description = self._build_character_description(char, replaced_facets)
                resolved.append(entity)
            else:
                # 2. Model Character - check trigger cache first
                entity.source = "model_character"
                cache_tag, cache_caption = self._lookup_trigger_cache(entity.name)
                if cache_tag and cache_caption:
                    entity.canonical_tag = cache_tag
                    entity.caption_name = cache_caption
                    entity.custom_description = None
                    resolved.append(entity)
                else:
                    entity.custom_description = None
                    unresolved_model_chars.append(entity)
                    resolved.append(entity)

        # 3. Batch resolve any unknown model characters via LLM
        if unresolved_model_chars and self.llm_provider:
            names_to_resolve = [e.name for e in unresolved_model_chars]
            try:
                llm_mappings = await self._batch_llm_resolve(names_to_resolve, model=model, reasoning_effort=reasoning_effort)
                for e in unresolved_model_chars:
                    if e.name in llm_mappings:
                        tag, caption = llm_mappings[e.name]
                        e.canonical_tag = tag
                        e.caption_name = caption
            except Exception as ex:
                logger.error(f"Batch LLM trigger resolution failed: {ex}")
                raise RuntimeError(f"未能解析角色 Trigger: {ex}")

            # Check if any model character remains unresolved
            missing_chars = [e.name for e in unresolved_model_chars if not e.canonical_tag]
            if missing_chars:
                raise RuntimeError(
                    f"未能解析角色【{', '.join(missing_chars)}】的 Danbooru/Gelbooru Trigger 标签。"
                    f"请在创作台的识别人物卡片中手动填写 Canonical Tag 与 Caption Name，或检查 LLM 模型连接。"
                )

        return resolved

    def resolve_entities_sync(self, entities: List[Entity], statements: List[Statement]) -> List[Entity]:
        """Synchronous version for build phase (relies on Character Book and Cache)."""
        resolved: List[Entity] = []
        for entity in entities:
            char = self._find_in_character_book(entity.name)
            if char:
                entity.source = "user_defined"
                entity.canonical_tag = None
                entity.caption_name = self._build_caption_name(char)

                replaced_facets = set()
                for s in statements:
                    if s.subject == entity.id:
                        if s.effect and s.effect.lower() == "replace":
                            if s.facet:
                                replaced_facets.add(s.facet.lower())
                            if any(w in s.text.lower() for w in ["wearing", "swimsuit", "uniform", "raincoat"]):
                                replaced_facets.add("outfit")
                            if any(w in s.text.lower() for w in ["hair", "ponytail", "twintails"]):
                                replaced_facets.add("hairstyle")

                entity.custom_description = self._build_character_description(char, replaced_facets)
            else:
                entity.source = "model_character"
                cache_tag, cache_caption = self._lookup_trigger_cache(entity.name)
                if cache_tag and cache_caption:
                    entity.canonical_tag = cache_tag
                    entity.caption_name = cache_caption
                entity.custom_description = None

            resolved.append(entity)
        return resolved

    def _find_in_character_book(self, name: str) -> Optional[Character]:
        name_clean = name.strip()
        stmt = select(Character).where(Character.name == name_clean)
        res = self.session.exec(stmt).first()
        if res:
            return res

        all_chars = self.session.exec(select(Character)).all()
        for char in all_chars:
            if char.aliases:
                aliases = [a.strip() for a in char.aliases.replace("，", ",").split(",") if a.strip()]
                if name_clean in aliases:
                    return char
        return None

    def _lookup_trigger_cache(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        name_clean = name.strip()
        stmt = select(CharacterTriggerCache).where(CharacterTriggerCache.name == name_clean)
        cache_item = self.session.exec(stmt).first()
        if cache_item:
            return cache_item.canonical_tag, cache_item.caption_name
        return None, None

    def _build_character_description(self, char: Character, replaced_facets: set) -> str:
        parts = []
        if char.age_group:
            parts.append(char.age_group)
        if char.gender:
            parts.append(char.gender)
        hair_tokens = []
        if char.hair_length and "hairstyle" not in replaced_facets:
            hair_tokens.append(char.hair_length)
        if char.hair_style and "hairstyle" not in replaced_facets:
            hair_tokens.append(char.hair_style)
        if char.hair_color and "hair_color" not in replaced_facets and "hairstyle" not in replaced_facets:
            hair_tokens.append(char.hair_color)
        if hair_tokens:
            parts.append(f"{' '.join(hair_tokens)} hair")
        if char.eye_color and "eye_color" not in replaced_facets:
            parts.append(f"{char.eye_color} eyes")
        if char.top and "outfit" not in replaced_facets and "top" not in replaced_facets:
            parts.append(f"wearing {char.top}")
        if char.bottom and "outfit" not in replaced_facets and "bottom" not in replaced_facets:
            parts.append(char.bottom)
        if char.outer and "outfit" not in replaced_facets and "outer" not in replaced_facets:
            parts.append(f"wearing {char.outer}")
        if char.accessories and "accessories" not in replaced_facets:
            parts.append(char.accessories)

        # De-duplicate
        seen = set()
        clean_parts = []
        for p in parts:
            if p and p.lower() not in seen:
                clean_parts.append(p)
                seen.add(p.lower())

        return ", ".join(clean_parts)

    async def _batch_llm_resolve(self, names: List[str], model: Optional[str] = None, reasoning_effort: Optional[str] = "instruct") -> Dict[str, Tuple[str, str]]:
        if not self.llm_provider:
            return {}

        messages = [
            {"role": "system", "content": RESOLVER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Resolve character tags for these characters: {json.dumps(names, ensure_ascii=False)}"}
        ]

        response_text = await self.llm_provider.chat(
            messages=messages,
            model=model,
            temperature=0.1,
            reasoning_effort=reasoning_effort,
            response_format={"type": "json_object"}
        )

        clean_json = response_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_json)
        result = {}
        for item in data.get("characters", []):
            name = item.get("name")
            tag = item.get("canonical_tag")
            caption = item.get("caption_name")
            if name and tag:
                result[name] = (tag, caption or name)

                # Persist to trigger cache
                cache_stmt = select(CharacterTriggerCache).where(CharacterTriggerCache.name == name)
                existing = self.session.exec(cache_stmt).first()
                if not existing:
                    new_cache = CharacterTriggerCache(
                        name=name,
                        canonical_tag=tag,
                        caption_name=caption or name
                    )
                    self.session.add(new_cache)
        self.session.commit()
        return result
