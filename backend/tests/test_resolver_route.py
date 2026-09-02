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
async def test_resolve_online_force_flows(session, monkeypatch):
    """force 必须贯穿唯一 resolved 结果（真实 endpoint，不直接调 confirm）。

    A: force=false → manual 非空 canonical 保持
    B: force=true  → online 唯一结果覆盖 manual canonical
    """
    # 预置 manual 缓存（ASCII 名 → 无需 LLM 转写，直接走唯一 resolved 路径）
    session.add(CharacterTriggerCache(name="Pikachu", canonical_tag="manual_tag",
                                      caption_name="Manual", series_tag=None, source="manual"))
    session.commit()

    monkeypatch.setattr(settings, "ONLINE_RESOLVE_CACHE_WRITE", True)
    fake_src = FakeSource()  # search → 唯一 [pikachu / pokemon, 14177 posts]
    from app.services.character_meta import source as source_mod
    monkeypatch.setattr(source_mod, "BooruTagSource", lambda *a, **k: fake_src)
    monkeypatch.setattr(characters_api, "LMStudioProvider", lambda *a, **k: object())

    from app.api.characters import ResolveOnlineRequest, resolve_online

    # A: force=false → 唯一结果不覆盖 manual 非空字段
    out_a = await resolve_online(ResolveOnlineRequest(name="Pikachu", force=False), session)
    assert out_a["status"] == "resolved"
    row_a = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "Pikachu")).first()
    assert row_a.canonical_tag == "manual_tag"   # manual 非空保持
    assert row_a.caption_name == "Manual"
    assert row_a.series_tag == "pokemon"         # 空字段仍被补全

    # B: force=true → 唯一结果覆盖 manual canonical（row 保持 manual 归属，
    #    代表用户已接管：后续自动联网仍只补空字段，不会静默再覆盖）
    out_b = await resolve_online(ResolveOnlineRequest(name="Pikachu", force=True), session)
    assert out_b["status"] == "resolved"
    row_b = session.exec(__import__("sqlmodel").select(CharacterTriggerCache).where(
        CharacterTriggerCache.name == "Pikachu")).first()
    assert row_b.canonical_tag == "pikachu"      # online 唯一结果覆盖
    assert row_b.source == "manual"              # 归属标记保持 manual（设计语义）