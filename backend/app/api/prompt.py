from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from app.database import get_session
from app.config import settings
from app.models.prompt_engine import (
    ParsePromptRequest,
    ResolveTriggerRequest,
    ResolveTriggerResponse,
    PromptBuildRequest,
    PromptBuildResponse,
    SemanticFacts
)
from app.models.trigger_cache import CharacterTriggerCache
from app.services.llm.lm_studio import LMStudioProvider
from app.services.llm.openai_compat import OpenAICompatibleProvider
from app.services.prompt_engine.pipeline import PromptPipeline
from app.services.prompt_engine.resolver import CharacterResolver

router = APIRouter(prefix="/prompt", tags=["prompt"])

def get_llm_provider(provider_type: str = "lm_studio"):
    if provider_type == "cloud":
        return OpenAICompatibleProvider(base_url=settings.CLOUD_API_BASE_URL, api_key=settings.CLOUD_API_KEY)
    else:
        return LMStudioProvider(base_url=settings.LM_STUDIO_BASE_URL, api_key=settings.LM_STUDIO_API_KEY)

@router.post("/parse", response_model=SemanticFacts)
async def parse_prompt(
    req: ParsePromptRequest,
    session: Session = Depends(get_session)
):
    """Extract semantic entities and statements from user input."""
    provider_type = req.provider or settings.ACTIVE_PROVIDER
    llm = get_llm_provider(provider_type)
    pipeline = PromptPipeline(session=session, llm_provider=llm)
    
    # Check auto-load for LM Studio if configured
    if provider_type == "lm_studio" and settings.LM_STUDIO_AUTO_LOAD and req.model:
        try:
            await llm.load_model(req.model)
        except Exception:
            pass

    facts = await pipeline.parse_and_extract(
        raw_text=req.text,
        rule_ids=req.rule_ids,
        model=req.model or (settings.LM_STUDIO_MODEL if provider_type == "lm_studio" else settings.CLOUD_MODEL),
        reasoning_effort=req.reasoning_effort or (settings.LM_STUDIO_REASONING_EFFORT if provider_type == "lm_studio" else settings.CLOUD_REASONING_EFFORT)
    )

    # Check auto-unload for LM Studio if configured
    if provider_type == "lm_studio" and settings.LM_STUDIO_AUTO_UNLOAD and req.model:
        try:
            await llm.unload_model(req.model)
        except Exception:
            pass

    return facts

@router.post("/resolve-trigger", response_model=ResolveTriggerResponse)
def resolve_trigger(
    req: ResolveTriggerRequest,
    session: Session = Depends(get_session)
):
    """Resolve character trigger for a model character and optionally persist user edit."""
    name_clean = req.name.strip()
    
    if req.save_to_cache and req.canonical_tag and req.caption_name:
        # User manually edited and wants to save mapping
        stmt = select(CharacterTriggerCache).where(CharacterTriggerCache.name == name_clean)
        existing = session.exec(stmt).first()
        if existing:
            existing.canonical_tag = req.canonical_tag
            existing.caption_name = req.caption_name
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            new_cache = CharacterTriggerCache(
                name=name_clean,
                canonical_tag=req.canonical_tag,
                caption_name=req.caption_name
            )
            session.add(new_cache)
        session.commit()
        return ResolveTriggerResponse(
            name=name_clean,
            canonical_tag=req.canonical_tag,
            caption_name=req.caption_name,
            from_cache=True
        )

    resolver = CharacterResolver(session=session)
    tag, caption = resolver._resolve_model_trigger(name_clean)
    return ResolveTriggerResponse(
        name=name_clean,
        canonical_tag=tag,
        caption_name=caption,
        from_cache=True
    )

@router.post("/build", response_model=PromptBuildResponse)
def build_prompt(
    req: PromptBuildRequest,
    session: Session = Depends(get_session)
):
    """Compile intermediate semantic facts and deterministic options into final English prompt."""
    pipeline = PromptPipeline(session=session)
    return pipeline.build_prompt(req)
