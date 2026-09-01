import re
from typing import List, Optional, Tuple, Dict
from sqlmodel import Session, select
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.prompt_engine import Entity, Statement

DEFAULT_KNOWN_TRIGGERS = {
    "穗穗": ("suisui", "Suisui"),
    "秧秧": ("yangyang", "Yangyang"),
    "爱丽丝": ("alice", "Alice"),
    "明日香": ("souryuu_asuka_langley", "Asuka Langley"),
    "绫波丽": ("ayanami_rei", "Rei Ayanami"),
    "初音未来": ("hatsune_miku", "Hatsune Miku"),
    "芙莉莲": ("frieren", "Frieren"),
    "费伦": ("fern", "Fern"),
}

class CharacterResolver:
    def __init__(self, session: Session):
        self.session = session

    def resolve_entities(self, entities: List[Entity], statements: List[Statement]) -> List[Entity]:
        """Resolves each entity against the character book (user_defined) or model triggers (model_character)."""
        resolved: List[Entity] = []
        for entity in entities:
            # 1. Check Character Book
            char = self._find_in_character_book(entity.name)
            if char:
                # User-defined character: name is internal only, NEVER emitted as Anima tag or prompt token
                entity.source = "user_defined"
                entity.canonical_tag = None
                
                # Determine clean English reference for natural language caption
                if char.gender and "man" in char.gender.lower() and "wo" not in char.gender.lower():
                    entity.caption_name = "the young man" if "young" in (char.age_group or "") else "the boy"
                else:
                    entity.caption_name = "the young woman" if "young" in (char.age_group or "") else "the girl"
                
                # Check for statement facet replacements for this entity
                replaced_facets = set()
                for s in statements:
                    if s.subject == entity.id:
                        if s.facet:
                            replaced_facets.add(s.facet.lower())
                        if "wearing" in s.text.lower() or "swimsuit" in s.text.lower() or "uniform" in s.text.lower() or "raincoat" in s.text.lower():
                            replaced_facets.add("outfit")
                        if "hair" in s.text.lower() or "ponytail" in s.text.lower() or "twintails" in s.text.lower():
                            replaced_facets.add("hairstyle")
                
                entity.custom_description = self._build_character_description(char, replaced_facets)
            else:
                # 2. Model character
                entity.source = "model_character"
                canonical_tag, caption_name = self._resolve_model_trigger(entity.name)
                entity.canonical_tag = canonical_tag
                entity.caption_name = caption_name
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

    def _resolve_model_trigger(self, name: str) -> Tuple[str, str]:
        name_clean = name.strip()
        
        stmt = select(CharacterTriggerCache).where(CharacterTriggerCache.name == name_clean)
        cache_item = self.session.exec(stmt).first()
        if cache_item:
            return cache_item.canonical_tag, cache_item.caption_name
            
        if name_clean in DEFAULT_KNOWN_TRIGGERS:
            tag, caption = DEFAULT_KNOWN_TRIGGERS[name_clean]
            cache_entry = CharacterTriggerCache(name=name_clean, canonical_tag=tag, caption_name=caption)
            self.session.add(cache_entry)
            self.session.commit()
            return tag, caption

        slug = re.sub(r"[^\w\s-]", "", name_clean).strip().lower().replace(" ", "_")
        if not slug:
            slug = "character"
        caption = name_clean.capitalize()
        return slug, caption

    def _build_character_description(self, char: Character, replaced_facets: set) -> str:
        """Expands custom character visual attributes, omitting facets replaced by the current prompt."""
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
