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
    "Explicit": "explicit, nsfw"
}

class PromptPolicy:
    def __init__(self):
        self.writer = PromptWriter()

    def format_artist_tag(self, raw_tag: str) -> str:
        """Formats artist tags to standard Anima-2.9B style: @artist_name."""
        t = raw_tag.strip().rstrip(",")
        if not t:
            return ""
        if t.startswith("artist:"):
            t = "@" + t[7:].strip()
        elif not t.startswith("@"):
            t = "@" + t
        return t

    def determine_character_count_tag(self, facts: SemanticFacts) -> Optional[str]:
        """Calculates count tags like 1girl, 2girls, 1boy, 1boy, 1girl."""
        count = len(facts.entities)
        if count == 0:
            return None
        elif count == 1:
            name = facts.entities[0].name.lower()
            if "boy" in name or "男" in name or "小明" in name:
                return "1boy"
            return "1girl"
        elif count == 2:
            return "2girls"
        else:
            return f"{count}girls"

    def compile_positive_prompt(
        self,
        facts: SemanticFacts,
        safety: SafetyLevel = "Safe",
        positive_prefix: Optional[str] = "",
        artist_tags: List[str] = None,
        lora_items: List[LoraBuildItem] = None
    ) -> str:
        sections: List[str] = []

        # 1. Preset Positive Prefix (if provided by user preset)
        if positive_prefix and positive_prefix.strip():
            sections.append(positive_prefix.strip().rstrip(","))

        # 2. Safety Tag (deterministic)
        safety_tag = SAFETY_TAG_MAP.get(safety, "safe")
        sections.append(safety_tag)

        # 3. Character Count Tag
        count_tag = self.determine_character_count_tag(facts)
        if count_tag:
            sections.append(count_tag)

        # 4. Canonical Character Triggers / Custom Character Descriptions
        char_tags: List[str] = []
        for entity in facts.entities:
            if entity.source == "user_defined":
                if entity.custom_description:
                    char_tags.append(entity.custom_description)
            elif entity.source == "model_character":
                if entity.canonical_tag:
                    char_tags.append(entity.canonical_tag)

        if char_tags:
            sections.append(", ".join(char_tags))

        # 5. Natural Language Scene & Actions
        natural_language_scene = self.writer.write_natural_language_scene(facts)
        if natural_language_scene:
            sections.append(natural_language_scene)

        # 6. Artist Tags (@artist format)
        if artist_tags:
            formatted_artists = [self.format_artist_tag(a) for a in artist_tags if a.strip()]
            if formatted_artists:
                sections.append(", ".join(formatted_artists))

        # 7. LoRA Trigger Words
        if lora_items:
            lora_triggers = []
            for item in lora_items:
                if item.is_enabled and item.trigger_words.strip():
                    lora_triggers.append(item.trigger_words.strip().rstrip(","))
            if lora_triggers:
                sections.append(", ".join(lora_triggers))

        # Clean and join sections
        cleaned_sections = [sec.strip() for sec in sections if sec.strip()]
        final_prompt = ", ".join(cleaned_sections)
        final_prompt = re.sub(r",\s*,", ",", final_prompt)
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
