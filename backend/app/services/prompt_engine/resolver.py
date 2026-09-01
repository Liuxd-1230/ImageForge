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
                if char.gender and "man" in char.gender.lower() and "wo" not in char.gender.lower():
                    entity.caption_name = "the young man" if "young" in (char.age_group or "") else "the boy"
                else:
                    entity.caption_name = "the young woman" if "young" in (char.age_group or "") else "the girl"

                replaced_facets = set()
                for s in statements:
                    if s.subject == entity.id:
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
                logger.warning(f"Batch LLM trigger resolution failed: {ex}")

        return resolved

    def resolve_entities_sync(self, entities: List[Entity], statements: List[Statement]) -> List[Entity]:
        """Synchronous version for build phase (relies on Character Book and Cache)."""
        resolved: List[Entity] = []
        for entity in entities:
            char = self._find_in_character_book(entity.name)
            if char:
                entity.source = "user_defined"
                entity.canonical_tag = None
                if char.gender and "man" in char.gender.lower() and "wo" not in char.gender.lower():
                    entity.caption_name = "the young man" if "young" in (char.age_group or "") else "the boy"
                else:
                    entity.caption_name = "the young woman" if "young" in (char.age_group or "") else "the girl"

                replaced_facets = set()
                for s in statements:
                    if s.subject == entity.id:
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

    async def _batch_llm_resolve(
        self,
        names: List[str],
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = "instruct"
    ) -> Dict[str, Tuple[str, str]]:
        """Invokes LLM in batch to resolve standard Anima trigger tags."""
        if not self.llm_provider or not names:
            return {}

        prompt_text = f"Resolve character tags for these characters: {json.dumps(names, ensure_ascii=False)}\nRespond with JSON only:"
        messages = [
            {"role": "system", "content": RESOLVER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ]

        raw_output = await self.llm_provider.chat(
            messages=messages,
            model=model,
            temperature=0.1,
            reasoning_effort=reasoning_effort
        )

        text = re.sub(r"<think>[\s\S]*?</think>", "", raw_output, flags=re.IGNORECASE).strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if m:
                text = m.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

        data = json.loads(text)
        result = {}
        for item in data.get("characters", []):
            c_name = item.get("name")
            c_tag = item.get("canonical_tag")
            c_caption = item.get("caption_name")
            if c_name and c_tag:
                result[c_name] = (c_tag.strip().lower(), c_caption or c_name)
        return result

    def _build_character_description(self, char: Character, replaced_facets: set) -> str:
        parts = []
        traits = [char.age_group, char.body, char.gender]
        trait_str = " ".join([t.strip() for t in traits if t and t.strip()])
        if trait_str:
            parts.append(f"a {trait_str}")

        hair_parts = []
        if "hairstyle" not in replaced_facets:
            for f in [char.hair_length, char.hair_style, char.hair_color]:
                if f and f.strip():
                    hair_parts.append(f.strip())

        eye_part = f"{char.eye_color.strip()} eyes" if char.eye_color and char.eye_color.strip() else ""

        hair_eye = []
        if hair_parts:
            hair_eye.append(f"{' '.join(hair_parts)} hair")
        if eye_part:
            hair_eye.append(eye_part)

        if hair_eye:
            if parts:
                parts.append(f"with {', '.join(hair_eye)}")
            else:
                parts.append(f"{', '.join(hair_eye)}")

        if char.facial_features and char.facial_features.strip():
            parts.append(char.facial_features.strip())
        if char.headwear and char.headwear.strip() and "headwear" not in replaced_facets:
            parts.append(char.headwear.strip())

        if "outfit" not in replaced_facets:
            outfit_pieces = [
                char.top, char.outer, char.bottom, char.socks, char.shoes, char.accessories
            ]
            valid_outfit = [p.strip() for p in outfit_pieces if p and p.strip()]
            if valid_outfit:
                parts.append(f"wearing {', '.join(valid_outfit)}")

        if "expression" not in replaced_facets and char.default_expression and char.default_expression.strip():
            parts.append(char.default_expression.strip())
        if "pose" not in replaced_facets and char.default_pose and char.default_pose.strip():
            parts.append(char.default_pose.strip())

        if char.extra_description and char.extra_description.strip():
            parts.append(char.extra_description.strip())

        return ", ".join(parts)
