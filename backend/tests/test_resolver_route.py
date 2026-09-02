"""Character Resolver route-level closure tests (no real network / LLM).

Covers:
- 2.1 target_model order bug: ONLINE_RESOLVE_ENABLED=true 时 /api/prompt/parse 必须真实接入 online resolver
- <角色名> marker：剥离开关后 clean_text 无尖括号，explicit 名进入解析链
- cache hit → 第二次 parse 不再联网
- force/manual：普通候选选择不覆盖 manual 非空；force=true 才覆盖
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from sqlmodel import Session, create_engine, SQLModel  # noqa: E402

import app.api.prompt as prompt_api  # noqa: E402
import app.api.characters as characters_api  # noqa: E402
from app.config import settings  # noqa: E402
from app.models.prompt_engine import ParsePromptRequest  # noqa: E402
from app.models.trigger_cache import CharacterTriggerCache  # noqa: E402
from app.services.character_meta.source import CharacterMetadata  # noqa: E402

EXTRACT_JSON = (
    '{"entities": [{"id": "c1", "name": "Pikachu"}], "statements": []}'
)


class FakeLLM:
    """代替 LMStudioProvider：提取返回固定 JSON，转写返回空。"""
    def __init__(self, base_url="", api_key="", **kw):
        self.calls = []

    async def chat(self, messages, model=None, temperature=0.2,
                   reasoning_effort="instruct", response_format=None):
        self.calls.append((messages, model))
        return EXTRACT_JSON

    async def load_model(self, *a, **k):
        return {"instance_id": "test"}

    async def unload_model(self, *a, **k):
        return None


class FakeSource:
    def __init__(self, base_url="", timeout=15.0, max_candidates=5):
        self.calls = []

    async def search(self, name):
        self.calls.append(name)
        return [CharacterMetadata(canonical_tag="pikachu", series_tag="pokemon",
                                  caption_name="Pikachu", post_count=14177)]


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def wired(monkeypatch, session):
    """ONLINE_RESOLVE_ENABLED=true + fake LLM + fake source；返回 fake 引用供断言。"""
    monkeypatch.setattr(settings, "ONLINE_RESOLVE_ENABLED", True)
    monkeypatch.setattr(settings, "ONLINE_RESOLVE_CACHE_WRITE", True)
    fake_llm = FakeLLM()
    monkeypatch.setattr(prompt_api, "LMStudioProvider", lambda *a, **k: fake_llm)
    fake_src = FakeSource()
    # BooruTagSource 在 parse_prompt 内部 import → patch 源模块属性
    from app.services.character_meta import source as source_mod
    monkeypatch.setattr(source_mod, "BooruTagSource", lambda *a, **k: fake_src)
    return {"llm": fake_llm, "src": fake_src}


async def _parse(text, session):
    req = ParsePromptRequest(text=text, provider="lm_studio", model="m")
    facts = await prompt_api.parse_prompt(req, session)
    return facts


@pytest.mark.asyncio
async def test_parse_wires_online_resolver_and_strips_markers(wired, session):
    facts = await _parse("<Pikachu> standing alone on a beach", session)
    assert wired["src"].calls == ["Pikachu"]  # online resolver 真实接入（2.1 修复）
    names = [e.name for e in facts.entities]
    assert "Pikachu" in names
    # marker 已剥离：user 输入里不得含尖括号，且是剥离后的 clean_text
    user_joined = " | ".join(m.get("content", "") for msgs, _m in wired["llm"].calls for m in msgs if m.get("role") == "user")
    assert "<Pikachu>" not in user_joined
    assert "Pikachu standing alone on a beach" in user_joined


@pytest.mark.asyncio
async def test_parse_respects_online_disabled(wired, session, monkeypatch):
    monkeypatch.setattr(settings, "ONLINE_RESOLVE_ENABLED", False)
    await _parse("<Pikachu> standing alone", session)
    assert wired["src"].calls == []  # 未开启 → 不联网


@pytest.mark.asyncio
async def test_cache_hit_no_second_online_call(wired, session):
    await _parse("<Pikachu> standing alone", session)
    first_calls = list(wired["src"].calls)
    await _parse("<Pikachu> sitting down", session)
    assert wired["src"].calls == first_calls  # 第二次命中缓存，不再联网


@pytest.mark.asyncio
async def test_resolve_online_force_flows(session):
    # 预置 manual 缓存
    session.add(CharacterTriggerCache(name="穗穗", canonical_tag="my precious",
                                      caption_name="Mine", series_tag=None, source="manual"))
    session.commit()
    fake_src = FakeSource()
    monkeypatch = None
    orig_llm = characters_api.LMStudioProvider

    class FLLM:
        def __init__(self, *a, **k): pass

    characters_api.LMStudioProvider = FLLM
    characters_api.BooruTagSource = lambda *a, **k: fake_src
    try:
        from app.api.characters import ResolveOnlineRequest, resolve_online
        # 普通候选选择 force=false：manual 非空不覆盖，只补空 series
        req = ResolveOnlineRequest(name="穗穗", candidate_index=0, force=False)
        # resolve() 对 CJK 需要 LLM 转写 → FLLM 返回空 → cand_names [] → offline
        # 因此直接测 confirm 路径（绕过 resolve 的转写）：
        from app.services.character_meta.resolver import OnlineCharacterResolver
        from app.services.character_meta.source import BooruTagSource
        res = OnlineCharacterResolver(session=session, source=BooruTagSource(), llm_provider=None, write_cache=True)
        await res.confirm("穗穗", {"canonical_tag": "suisui", "series_tag": "wuthering waves",
                                   "caption_name": "Suisui", "aliases": []}, force=False)
        row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
            CharacterTriggerCache.name == "穗穗")).first()
        assert row.canonical_tag == "my precious"      # manual 非空不覆盖
        assert row.caption_name == "Mine"
        assert row.series_tag == "wuthering waves"     # 空字段补全
        # force=true → 覆盖
        await res.confirm("穗穗", {"canonical_tag": "suisui", "series_tag": "ww2",
                                   "caption_name": "Suisui", "aliases": []}, force=True)
        row = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
            CharacterTriggerCache.name == "穗穗")).first()
        assert row.canonical_tag == "suisui"
        assert row.series_tag == "ww2"
    finally:
        characters_api.LMStudioProvider = orig_llm