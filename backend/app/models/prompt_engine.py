from typing import Literal, Optional, List
from pydantic import BaseModel, Field

SafetyLevel = Literal["Safe", "Sensitive", "NSFW", "Explicit"]

class Entity(BaseModel):
    id: str = Field(description="Unique entity ID, e.g. c1, c2")
    name: str = Field(description="Character name as entered by user, e.g. 林澄")
    source: Optional[Literal["user_defined", "model_character"]] = Field(
        default=None, 
        description="Assigned by character book lookup, not by fact extractor"
    )
    canonical_tag: Optional[str] = Field(default=None, description="Trigger tag for tag area, e.g. lincheng")
    caption_name: Optional[str] = Field(default=None, description="English name for natural language caption, e.g. Lin Cheng")
    custom_description: Optional[str] = Field(default=None, description="Expanded appearance text if user_defined")

class Statement(BaseModel):
    kind: Literal["attribute", "relation", "scene", "general"] = Field(
        description="Kind of statement: attribute, relation, scene, or general"
    )
    subject: Optional[str] = Field(default=None, description="Entity ID of the subject")
    target: Optional[str] = Field(default=None, description="Entity ID of the target (for relations)")
    text: str = Field(description="English semantic content, e.g. 'wearing a swimsuit', 'chasing'")
    facet: Optional[str] = Field(
        default=None, 
        description="Optional facet string: outfit, hairstyle, expression, accessory, pose, etc."
    )
    effect: Optional[Literal["replace", "add", "modify"]] = Field(
        default=None,
        description="Optional effect: replace, add, modify"
    )

class SemanticFacts(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    statements: List[Statement] = Field(default_factory=list)

class ParsePromptRequest(BaseModel):
    text: str
    rule_ids: Optional[List[int]] = None
    provider: Optional[str] = "lm_studio"
    model: Optional[str] = None
    reasoning_effort: Optional[str] = "instruct"

class ResolveTriggerRequest(BaseModel):
    name: str
    canonical_tag: Optional[str] = None
    caption_name: Optional[str] = None
    save_to_cache: bool = False

class ResolveTriggerResponse(BaseModel):
    name: str
    canonical_tag: str
    caption_name: str
    from_cache: bool

class LoraBuildItem(BaseModel):
    id: Optional[int] = None
    filename: Optional[str] = None
    trigger_words: str
    strength: float = 0.8
    is_enabled: bool = True

class PromptBuildRequest(BaseModel):
    facts: SemanticFacts
    safety: SafetyLevel = "Safe"
    preset_id: Optional[int] = None
    positive_prefix: Optional[str] = None
    default_negative: Optional[str] = None
    artist_tags: List[str] = Field(default_factory=list)
    lora_items: List[LoraBuildItem] = Field(default_factory=list)
    extra_negative: str = ""

class PromptBuildResponse(BaseModel):
    prompt: str
    negative_prompt: str
    facts: SemanticFacts
    safety_tag: str
    character_count_tag: Optional[str] = None
