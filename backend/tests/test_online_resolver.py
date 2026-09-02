"""Character Online Resolver V1 — deterministic tests (no network).

Fake tag source; covers the 10 required scenarios:
 1. cache complete  → no online call
 2. cache lacks series → online patches series only
 3. unknown → online result cached
 4. source=manual → auto online never overwrites non-empty fields
 5. online failure → never breaks parse/fallback
 6. ambiguous → not silently picked (needs user confirm)
 7. series present → prompt identification tag = canonical + series
 8. series empty → canonical-only
 9. Character Book user char → not forced online
10. generic puppy/cat/car/book (Candidate E) → never enters online resolver
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from sqlmodel import Session, create_engine, SQLModel  # noqa: E402

from app.models.character import Character  # noqa: E402
from app.models.trigger_cache import CharacterTriggerCache  # noqa: E402
from app.models.prompt_engine import (  # noqa: E402
    Entity, SemanticFacts, PromptBuildRequest,
)
from app.services.character_meta.source import CharacterMetadata  # noqa: E402
from app.services.character_meta.resolver import OnlineCharacterResolver  # noqa: E402
from app.services.prompt_engine.pipeline import PromptPipeline  # noqa: E402


def meta(canonical, series="", caption=None, aliases=None, count=100):
    return CharacterMetadata(canonical_tag=canonical, series_tag=series,
                             caption_name=caption or canonical.title(),
                             aliases=aliases or [], post_count=count)


class FakeSource:
    """Scripted source: results[name] -> list[CharacterMetadata]; option to fail."""
    def __init__(self, results=None, fail=False):
        self.results = results or {}
        self.fail = fail
        self.calls = []

    async def search(self, name):
        self.calls.append(name)
        if self.fail:
            raise RuntimeError("network down")
        return self.results.get(name, [])


class FakeLLM:
    """Mimics BaseLLMProvider.chat for CJK transliteration in tests."""
    def __init__(self, mapping):
        self.mapping = mapping

    async def chat(self, messages, model=None, temperature=0.2,
                   reasoning_effort="instruct", response_format=None):
        import re
        prompt = (messages or [{}])[-1].get("content", "")
        m = re.search(r"Name: (.+)", prompt)
        key = m.group(1).strip() if m else ""
        return self.mapping.get(key, "")


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def make_online(session, source=None, write_cache=True, llm=None):
    return OnlineCharacterResolver(session=session, source=source or FakeSource(),
                                   llm_provider=llm, write_cache=write_cache)


@pytest.mark.asyncio
async def test_1_cache_complete_no_online_call(session):
    session.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui",
                                      caption_name="Suisui", series_tag="wuthering waves",
                                      source="online"))
    session.commit()
    src = FakeSource()
    online = make_online(session, src)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="穗穗")])
    assert src.calls == []


@pytest.mark.asyncio
async def test_2_missing_series_patched_only(session):
    session.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui",
                                      caption_name="Suisui", series_tag=None, source="online"))
    session.commit()
    src = FakeSource(results={"suisui": [meta("suisui", "wuthering waves")]})
    online = make_online(session, src)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="穗穗")])
    row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "穗穗")).first()
    assert row.canonical_tag == "suisui"            # 不覆盖已存在值
    assert row.series_tag == "wuthering waves"      # 空字段被补全
    assert src.calls != []


@pytest.mark.asyncio
async def test_3_unknown_written_to_cache(session):
    src = FakeSource(results={"march 7th": [meta("march 7th", "honkai: star rail", "March 7th")]})
    llm = FakeLLM({"三月七": "march 7th"})
    online = make_online(session, src, llm=llm)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="三月七")])
    row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "三月七")).first()
    assert row is not None
    assert row.canonical_tag == "march 7th"
    assert row.series_tag == "honkai: star rail"
    assert row.source == "online"
    assert row.resolved_at is not None


@pytest.mark.asyncio
async def test_4_manual_never_overwritten(session):
    session.add(CharacterTriggerCache(name="穗穗", canonical_tag="my precious",
                                      caption_name="Mine", series_tag=None, source="manual"))
    session.commit()
    src = FakeSource(results={"suisui": [meta("suisui", "wuthering waves", "Suisui")]})
    llm = FakeLLM({"穗穗": "suisui"})
    online = make_online(session, src, llm=llm)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="穗穗")])
    row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "穗穗")).first()
    assert row.canonical_tag == "my precious"       # manual 非空值不被覆盖
    assert row.caption_name == "Mine"
    assert row.series_tag == "wuthering waves"      # 空字段可补
    # 用户显式“重新解析并替换”（force=True）才允许覆盖
    src2 = FakeSource(results={"suisui": [meta("suisui", "wuthering waves", "Suisui")]})
    online2 = make_online(session, src2, llm=llm)
    await online2.confirm("穗穗", {"canonical_tag": "suisui", "series_tag": "ww2",
                                   "caption_name": "Suisui", "aliases": []}, force=True)
    row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "穗穗")).first()
    assert row.canonical_tag == "suisui"            # force 覆盖


@pytest.mark.asyncio
async def test_5_online_failure_does_not_break(session):
    src = FakeSource(fail=True)
    online = make_online(session, src)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="三月七")])
    assert session.exec(__import__("sqlmodel").select(CharacterTriggerCache)).all() == []
    # backfill silently returns False, parse continues (no exception)


@pytest.mark.asyncio
async def test_6_ambiguous_not_auto_picked(session):
    src = FakeSource(results={"kasumi": [
        meta("kasumi", "kantai collection", "Kasumi", count=1000),
        meta("kasumi", "pokemon", "Kasumi", count=900),
    ]})
    online = make_online(session, src)
    outcome = await online.resolve("kasumi")  # ASCII 名字无需 LLM
    assert outcome["status"] == "ambiguous"
    assert len(outcome["candidates"]) == 2
    # 未确认前不写缓存
    assert session.exec(__import__("sqlmodel").select(CharacterTriggerCache)).all() == []
    # 用户确认第 2 个 → 写缓存
    out2 = await online.confirm("kasumi", outcome["candidates"][1])
    assert out2["status"] == "resolved"
    row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "kasumi")).first()
    assert row.series_tag == "pokemon"


def _build_prompt(session, series: bool):
    # 缓存行：始终有 canonical；series 仅当 series=True 时写入
    session.add(CharacterTriggerCache(name="三月七", canonical_tag="march 7th",
                                      caption_name="March 7th",
                                      series_tag="honkai: star rail" if series else None,
                                      source="online"))
    session.commit()
    pipe = PromptPipeline(session=session)
    res = pipe.build_prompt(PromptBuildRequest(
        facts=SemanticFacts(entities=[Entity(id="c1", name="三月七")], statements=[]),
        safety="Safe"
    ))
    return res.prompt


def test_7_series_tag_in_identification(session):
    prompt = _build_prompt(session, series=True)
    assert "march 7th, honkai: star rail" in prompt, prompt
    assert "honkai" not in _nl_part(prompt)  # series 不进自然语言句子


def test_8_no_series_canonical_only(session):
    prompt = _build_prompt(session, series=False)
    assert "march 7th" in prompt, prompt
    assert "honkai" not in prompt, prompt  # 无 series 时保持 canonical-only


def _nl_part(prompt: str) -> str:
    parts = prompt.split(". ", 1)
    return parts[1] if len(parts) > 1 else ""


@pytest.mark.asyncio
async def test_9_character_book_not_forced_online(session):
    session.add(Character(name="小雨", gender="girl", hair_color="brown"))
    session.commit()
    src = FakeSource()
    online = make_online(session, src)
    pipe = PromptPipeline(session=session, online_resolver=online)
    await pipe._online_backfill([Entity(id="c1", name="小雨")])
    assert src.calls == []


@pytest.mark.asyncio
async def test_10_generic_subjects_never_enter_online(session):
    src = FakeSource()
    online = make_online(session, src)
    pipe = PromptPipeline(session=session, online_resolver=online)
    # 联网层只保留非常确定的 anonymous placeholder（girl1/boy1/person1…）
    await pipe._online_backfill([
        Entity(id="c1", name="girl1"),
        Entity(id="c2", name="boy1"),
        Entity(id="c3", name="person2"),
    ])
    assert src.calls == []
    # 中文 substring 判断已删除：<猫又> 这类名字绝不能被 generic 误拦
    assert PromptPipeline._is_generic_subject("猫又") is False
    assert PromptPipeline._is_generic_subject("花火") is False
    assert PromptPipeline._is_generic_subject("小鸟游六花") is False
    assert PromptPipeline._is_generic_subject("金发女孩") is False  # 交给 Candidate E 上游
    # 普通小狗不成为 Entity 由 extractor 负责（markers/E 契约），匿名占位符仍被拦截
    assert PromptPipeline._is_generic_subject("girl2") is True