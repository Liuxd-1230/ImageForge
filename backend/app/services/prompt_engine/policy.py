import re
from typing import List, Optional
from app.models.prompt_engine import (
    SemanticFacts,
    SafetyLevel,
    PromptBuildRequest,
    PromptBuildResponse,
    LoraBuildItem
)
from app.services.prompt_engine.writer import PromptWriter

SAFETY_TAG_MAP = {
    "Safe": "safe",
    "Sensitive": "sensitive",
    "NSFW": "nsfw",
    "Explicit": "explicit"
}

class PromptPolicy:
    def __init__(self):
        self.writer = PromptWriter()

    def format_artist_tag(self, raw_tag: str) -> str:
        """
        Formats artist tags to standard Anima-2.9B style: @artist name
        (underscores converted to spaces, prepended with @).
        """
        t = raw_tag.strip().rstrip(",")
        if not t:
            return ""
        if t.startswith("artist:"):
            t = "@" + t[7:].strip()
        elif not t.startswith("@"):
            t = "@" + t
        # In Anima official prompting, replace underscores in artist tags with spaces
        prefix = "@" if t.startswith("@") else ""
        body = t[1:] if t.startswith("@") else t
        return f"{prefix}{body.replace('_', ' ')}".strip()

    def format_character_tag(self, raw_tag: str) -> str:
        """
        Formats character canonical tags to standard Anima-2.9B style
        (underscores converted to spaces, lowercase).
        """
        if not raw_tag:
            return ""
        return raw_tag.strip().replace("_", " ").lower()

    def determine_character_count_tag(self, facts: SemanticFacts) -> Optional[str]:
        """
        Calculates count tags ONLY when gender is explicitly specified or proven in character book / statements.
        Avoids hardcoding character names and avoids assuming all characters are female.
        """
        count = len(facts.entities)
        if count == 0:
            return None

        girls = 0
        boys = 0

        for e in facts.entities:
            desc = (e.custom_description or "").lower()
            desc_tokens = [t.strip() for t in desc.replace(",", " ").split() if t.strip()]

            # Check gender explicitly from character description (character book or explicit gender statement)
            # Never guess gender from proper character name strings!
            if any(w in desc_tokens for w in ["woman", "girl", "female"]):
                girls += 1
            elif any(w in desc_tokens for w in ["man", "boy", "male"]):
                boys += 1

        if girls > 0 and boys == 0 and girls == count:
            return "1girl" if count == 1 else f"{count}girls"
        elif boys > 0 and girls == 0 and boys == count:
            return "1boy" if count == 1 else f"{count}boys"
        elif girls > 0 and boys > 0 and (girls + boys) == count:
            parts = []
            if boys > 0:
                parts.append("1boy" if boys == 1 else f"{boys}boys")
            if girls > 0:
                parts.append("1girl" if girls == 1 else f"{girls}girls")
            return ", ".join(parts)

        return None

    def compile_positive_prompt(
        self,
        facts: SemanticFacts,
        safety: SafetyLevel = "Safe",
        positive_prefix: Optional[str] = "",
        artist_tags: List[str] = None,
        lora_items: List[LoraBuildItem] = None
    ) -> str:
        # 1. Structured Tag Area (Prefix, Safety, Count, Canonical Characters, Artists, LoRA triggers)
        tag_parts: List[str] = []

        if positive_prefix and positive_prefix.strip():
            tag_parts.append(positive_prefix.strip().rstrip(","))

        safety_tag = SAFETY_TAG_MAP.get(safety, "safe")
        tag_parts.append(safety_tag)

        count_tag = self.determine_character_count_tag(facts)
        if count_tag:
            tag_parts.append(count_tag)

        char_tags: List[str] = []
        for entity in facts.entities:
            if entity.source == "user_defined":
                if entity.custom_description:
                    char_tags.append(entity.custom_description)
            elif entity.source == "model_character":
                if entity.canonical_tag:
                    char_tags.append(self.format_character_tag(entity.canonical_tag))

        if char_tags:
            tag_parts.append(", ".join(char_tags))

        if artist_tags:
            formatted_artists = [self.format_artist_tag(a) for a in artist_tags if a.strip()]
            if formatted_artists:
                tag_parts.append(", ".join(formatted_artists))

        if lora_items:
            lora_triggers = []
            for item in lora_items:
                if item.is_enabled and item.trigger_words.strip():
                    lora_triggers.append(item.trigger_words.strip().rstrip(","))
            if lora_triggers:
                tag_parts.append(", ".join(lora_triggers))

        tags_str = ", ".join([t.strip().rstrip(" ,.") for t in tag_parts if t and t.strip()])

        # 2. Natural Language Sentence Area (Scene, Actions, Relations)
        natural_language_scene = self.writer.write_natural_language_scene(facts)
        nl_str = ""
        if natural_language_scene and natural_language_scene.strip():
            nl_str = natural_language_scene.strip()
            if not nl_str.endswith("."):
                nl_str += "."

        # Combine Tag Section and Natural Language Section cleanly
        if tags_str and nl_str:
            final_prompt = f"{tags_str}. {nl_str}"
        elif tags_str:
            final_prompt = tags_str
        else:
            final_prompt = nl_str

        # Clean redundant spaces and punctuation
        final_prompt = re.sub(r",\s*,", ", ", final_prompt)
        final_prompt = re.sub(r"\.\s*,", ". ", final_prompt)
        final_prompt = re.sub(r",\s*\.", ". ", final_prompt)
        final_prompt = re.sub(r"\s+", " ", final_prompt).strip(" ,")
        return final_prompt

    def compile_negative_prompt(
        self,
        default_negative: Optional[str] = "",
        extra_negative: Optional[str] = ""
    ) -> str:
        parts = []
        if default_negative and default_negative.strip():
            parts.append(default_negative.strip().rstrip(","))
        if extra_negative and extra_negative.strip():
            parts.append(extra_negative.strip().rstrip(","))
        return ", ".join(parts).strip(" ,")
