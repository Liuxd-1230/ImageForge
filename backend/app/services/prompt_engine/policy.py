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
            name = e.name.lower()
            caption = (e.caption_name or "").lower()
            
            # Check gender explicitly from character description, caption, or explicit gender statements
            if "woman" in desc or "girl" in desc or "girl" in name or "woman" in name or "girl" in caption or "woman" in caption or "female" in desc:
                girls += 1
            elif "man" in desc or "boy" in desc or "boy" in name or "man" in name or "boy" in caption or "man" in caption or "male" in desc:
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
        sections: List[str] = []

        # 1. Preset Positive Prefix (if provided)
        if positive_prefix and positive_prefix.strip():
            sections.append(positive_prefix.strip().rstrip(","))

        # 2. Safety Tag (deterministic 1-to-1 mapping)
        safety_tag = SAFETY_TAG_MAP.get(safety, "safe")
        sections.append(safety_tag)

        # 3. Character Count Tag (only if verified from data/input)
        count_tag = self.determine_character_count_tag(facts)
        if count_tag:
            sections.append(count_tag)

        # 4. Canonical Character Triggers (with underscores to spaces) / Custom Character Descriptions
        char_tags: List[str] = []
        for entity in facts.entities:
            if entity.source == "user_defined":
                if entity.custom_description:
                    char_tags.append(entity.custom_description)
            elif entity.source == "model_character":
                if entity.canonical_tag:
                    char_tags.append(self.format_character_tag(entity.canonical_tag))

        if char_tags:
            sections.append(", ".join(char_tags))

        # 5. Natural Language Scene & Actions
        natural_language_scene = self.writer.write_natural_language_scene(facts)
        if natural_language_scene:
            sections.append(natural_language_scene)

        # 6. Artist Tags (@artist with underscores to spaces)
        if artist_tags:
            formatted_artists = [self.format_artist_tag(a) for a in artist_tags if a.strip()]
            if formatted_artists:
                sections.append(", ".join(formatted_artists))

        # 7. LoRA Trigger Words (preserve original triggers as trained)
        if lora_items:
            lora_triggers = []
            for item in lora_items:
                if item.is_enabled and item.trigger_words.strip():
                    lora_triggers.append(item.trigger_words.strip().rstrip(","))
            if lora_triggers:
                sections.append(", ".join(lora_triggers))

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
