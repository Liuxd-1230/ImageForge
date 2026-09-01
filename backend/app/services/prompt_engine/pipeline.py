from typing import Optional, List
from sqlmodel import Session, select
from app.models.preset import Preset
from app.models.rule import RuleFile
from app.models.prompt_engine import (
    SemanticFacts,
    PromptBuildRequest,
    PromptBuildResponse,
    SafetyLevel
)
from app.services.prompt_engine.extractor import FactExtractor
from app.services.prompt_engine.resolver import CharacterResolver
from app.services.prompt_engine.validator import SemanticValidator
from app.services.prompt_engine.policy import PromptPolicy, SAFETY_TAG_MAP
from app.services.llm.base import BaseLLMProvider

class PromptPipeline:
    def __init__(self, session: Session, llm_provider: Optional[BaseLLMProvider] = None):
        self.session = session
        self.llm_provider = llm_provider
        self.extractor = FactExtractor(llm_provider=llm_provider)
        self.resolver = CharacterResolver(session=session, llm_provider=llm_provider)
        self.validator = SemanticValidator()
        self.policy = PromptPolicy()

    async def parse_and_extract(
        self,
        raw_text: str,
        rule_ids: Optional[List[int]] = None,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = "instruct"
    ) -> SemanticFacts:
        rule_context = ""
        if rule_ids:
            stmt = select(RuleFile).where(RuleFile.id.in_(rule_ids), RuleFile.is_enabled == True)
            rules = self.session.exec(stmt).all()
            rule_context = "\n\n".join([f"[{r.name}]:\n{r.content}" for r in rules])
        else:
            stmt = select(RuleFile).where(RuleFile.is_enabled == True).order_by(RuleFile.sort_order)
            rules = self.session.exec(stmt).all()
            if rules:
                rule_context = "\n\n".join([f"[{r.name}]:\n{r.content}" for r in rules])

        # 1. Fact Extraction
        raw_facts = await self.extractor.extract(
            user_input=raw_text,
            rules_context=rule_context,
            model=model,
            reasoning_effort=reasoning_effort
        )

        # 2. Batch Character Resolution (Character Book -> Cache -> LLM)
        resolved_entities = await self.resolver.resolve_entities_async(
            entities=raw_facts.entities,
            statements=raw_facts.statements,
            model=model,
            reasoning_effort=reasoning_effort
        )
        facts = SemanticFacts(entities=resolved_entities, statements=raw_facts.statements)

        # 3. Structural Validation
        return self.validator.validate_and_sanitize(facts)

    def build_prompt(self, request: PromptBuildRequest) -> PromptBuildResponse:
        resolved_entities = self.resolver.resolve_entities_sync(request.facts.entities, request.facts.statements)
        validated_facts = self.validator.validate_and_sanitize(
            SemanticFacts(entities=resolved_entities, statements=request.facts.statements)
        )

        prefix = request.positive_prefix
        negative = request.default_negative

        if request.preset_id:
            preset = self.session.get(Preset, request.preset_id)
            if preset:
                if prefix is None:
                    prefix = preset.positive_prefix
                if negative is None:
                    negative = preset.default_negative
        elif prefix is None or negative is None:
            stmt = select(Preset).where(Preset.is_default == True)
            default_p = self.session.exec(stmt).first()
            if default_p:
                if prefix is None:
                    prefix = default_p.positive_prefix
                if negative is None:
                    negative = default_p.default_negative

        positive_prompt = self.policy.compile_positive_prompt(
            facts=validated_facts,
            safety=request.safety,
            positive_prefix=prefix or "",
            artist_tags=request.artist_tags,
            lora_items=request.lora_items
        )

        negative_prompt = self.policy.compile_negative_prompt(
            default_negative=negative or "",
            extra_negative=request.extra_negative
        )

        safety_tag = SAFETY_TAG_MAP.get(request.safety, "safe")
        count_tag = self.policy.determine_character_count_tag(validated_facts)

        return PromptBuildResponse(
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            facts=validated_facts,
            safety_tag=safety_tag,
            character_count_tag=count_tag
        )
