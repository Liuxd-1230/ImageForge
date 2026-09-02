import re
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.models.preset import Preset
from app.models.rule import RuleFile
from app.models.trigger_cache import CharacterTriggerCache
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

# 匿名/描述性主体（Candidate E：不进入角色解析与在线解析）
_GENERIC_ANON_RE = re.compile(r"^(girl|boy|person|woman|man|male|female)\d*$", re.I)
_GENERIC_CN_MARKERS = (
    "女孩", "女生", "男孩", "男人", "女人", "少女", "路人", "猫娘",
    "小狗", "狗", "猫", "犬", "鸟", "车", "汽车", "书", "包", "花", "树", "桌子", "椅子",
)


class PromptPipeline:
    def __init__(self, session: Session, llm_provider: Optional[BaseLLMProvider] = None,
                 online_resolver: Any = None):
        self.session = session
        self.llm_provider = llm_provider
        self.online_resolver = online_resolver
        self.extractor = FactExtractor(llm_provider=llm_provider)
        self.resolver = CharacterResolver(session=session, llm_provider=llm_provider)
        self.validator = SemanticValidator()
        self.policy = PromptPolicy()

    @staticmethod
    def _is_generic_subject(name: str) -> bool:
        n = (name or "").strip()
        if not n:
            return True
        if _GENERIC_ANON_RE.match(n):
            return True
        return any(m in n.lower() for m in _GENERIC_CN_MARKERS)

    async def _online_backfill(self, entities) -> None:
        """Online Resolver 预回填（best-effort，失败静默 → 既有 LLM fallback 兜底）。

        解析链：角色书命中 → 跳过；缓存 canonical+series 完整 → 跳过；
        canonical 在但缺 series → 只补 series；完全未缓存 → 全量解析并写缓存。
        """
        if not self.online_resolver:
            return
        from app.services.character_meta.resolver import run_with_timeout
        from app.models.character import Character
        for e in entities:
            name = (e.name or "").strip()
            if not name or self._is_generic_subject(name):
                continue
            # Character Book 命中（用户自定义角色）→ 不联网
            if self.session.exec(select(Character).where(Character.name == name)).first():
                continue
            try:
                cache_item = self.online_resolver.get_cache(name)
                if cache_item and cache_item.canonical_tag and cache_item.series_tag:
                    continue  # 完整，直接复用
                if cache_item and cache_item.canonical_tag and not cache_item.series_tag:
                    await run_with_timeout(self.online_resolver.backfill(name, cache_item.canonical_tag))
                    continue
                await run_with_timeout(self.online_resolver.backfill(name))
            except Exception as ex:  # noqa: BLE001 — backfill 永不破坏解析
                self.session.rollback()
                import logging
                logging.getLogger(__name__).warning(f"online backfill skip {name}: {ex}")
                continue

    async def parse_and_extract(
        self,
        raw_text: str,
        rule_ids: Optional[List[int]] = None,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = "instruct"
    ) -> SemanticFacts:
        rule_context = ""
        # Only inject rules if specifically selected by user (rule_ids is non-empty list)
        if rule_ids is not None:
            if len(rule_ids) > 0:
                stmt = select(RuleFile).where(RuleFile.id.in_(rule_ids), RuleFile.is_enabled == True)
                rules = self.session.exec(stmt).all()
                rule_context = "\n\n".join([f"[{r.name}]:\n{r.content}" for r in rules])
        
        # 1. Fact Extraction
        raw_facts = await self.extractor.extract(
            user_input=raw_text,
            rules_context=rule_context,
            model=model,
            reasoning_effort=reasoning_effort
        )

        # 2. Online Resolver 预回填（可选；角色书/缓存完整则不联网）
        await self._online_backfill(raw_facts.entities)

        # 3. Batch Character Resolution (Character Book -> Cache -> LLM)
        resolved_entities = await self.resolver.resolve_entities_async(
            entities=raw_facts.entities,
            statements=raw_facts.statements,
            model=model,
            reasoning_effort=reasoning_effort
        )
        facts = SemanticFacts(entities=resolved_entities, statements=raw_facts.statements)

        # 4. Structural Validation
        return self.validator.validate_and_sanitize(facts)

    def build_prompt(self, request: PromptBuildRequest) -> PromptBuildResponse:
        resolved_entities = self.resolver.resolve_entities_sync(request.facts.entities, request.facts.statements)

        # Validate that specific named model characters have a canonical trigger tag
        for e in resolved_entities:
            if e.source == "model_character" and not e.canonical_tag:
                raise ValueError(
                    f"角色【{e.name}】未解析 Trigger 标签。"
                    f"请在上方“识别人物与 Trigger 映射”卡片中手动填写 Canonical Tag 与 Caption Name 并点击保存。"
                )

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

        # series_tag 映射（model_character 的角色 identification tag 区注入，
        # 从 Trigger Cache 读取；不触碰 SemanticFacts / 自然语言策略）
        series_tag_map: Dict[str, str] = {}
        for e in validated_facts.entities:
            if e.source == "model_character" and e.canonical_tag:
                ci = self.session.exec(
                    select(CharacterTriggerCache).where(CharacterTriggerCache.name == e.name.strip())
                ).first()
                if ci and ci.series_tag:
                    series_tag_map[e.canonical_tag] = ci.series_tag

        positive_prompt = self.policy.compile_positive_prompt(
            facts=validated_facts,
            safety=request.safety,
            positive_prefix=prefix or "",
            artist_tags=request.artist_tags,
            lora_items=request.lora_items,
            series_tag_map=series_tag_map
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
