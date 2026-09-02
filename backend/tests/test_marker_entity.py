"""显式角色标记 <角色名> 的“显式角色”契约（pipeline 级，无网络/无真实 LLM）。

目标 contract：`<猫又>` 是用户对「猫又是角色主体」的确定声明——
即使 extractor 漏抽，系统也不能静默忽略：extractor hint + 确定性 invariant 兜底补回 Entity。

覆盖：
- extractor 故意不返回显式角色 → 系统仍保证该名称为 Entity
- 多个显式名称逐一保证
- hint 确实进入 extractor（system），user 消息无尖括号、为剥离后 clean_text
- 尖括号不得泄漏进 Entity.name / canonical / caption / final prompt
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from sqlmodel import Session, create_engine, SQLModel  # noqa: E402

from app.models.trigger_cache import CharacterTriggerCache  # noqa: E402
from app.models.prompt_engine import PromptBuildRequest  # noqa: E402
from app.services.prompt_engine.pipeline import PromptPipeline  # noqa: E402
from app.services.prompt_engine.markers import parse_explicit_markers  # noqa: E402


class FakeLLM:
    """extraction 返回固定 JSON（可故意漏掉显式角色）；resolver batch 返回空。"""

    def __init__(self, extract_json):
        self.extract_json = extract_json
        self.sys_contents = []
        self.user_contents = []

    async def chat(self, messages, model=None, temperature=0.2,
                   reasoning_effort="instruct", response_format=None):
        for m in messages:
            if m.get("role") == "system":
                self.sys_contents.append(m.get("content", ""))
            elif m.get("role") == "user":
                self.user_contents.append(m.get("content", ""))
        if any("User Input:" in m.get("content", "") for m in messages):
            return self.extract_json
        return '{"characters": []}'


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def make_pipe(session, llm):
    return PromptPipeline(session=session, llm_provider=llm, online_resolver=None)


async def parse_via_markers(pipe, raw: str, model="m"):
    """镜像 API 路径：先 parse_explicit_markers 剥离尖括号，再进 pipeline。"""
    clean_text, explicit_names = parse_explicit_markers(raw)
    return await pipe.parse_and_extract(
        raw_text=clean_text, explicit_names=explicit_names, model=model, reasoning_effort="off",
    )


@pytest.mark.asyncio
async def test_explicit_marker_guarantees_dropped_entity(session):
    """extractor 故意返回空 entities → <花火> 仍必须是 Entity（确定性兜底）。"""
    llm = FakeLLM('{"entities": [], "statements": []}')
    pipe = make_pipe(session, llm)
    facts = await parse_via_markers(pipe, "<花火>站在窗边")
    names = [e.name for e in facts.entities]
    assert "花火" in names, f"显式 <角色名> 不能被静默忽略: {names}"


@pytest.mark.asyncio
async def test_multiple_explicit_markers_guaranteed(session):
    """<小鸟游六花> / <猫又> / <Pikachu> 逐个保证（extractor 全部漏抽）。"""
    llm = FakeLLM('{"entities": [], "statements": []}')
    pipe = make_pipe(session, llm)
    for name, scene in [("小鸟游六花", "坐在椅子上"), ("猫又", "回头看向镜头"), ("Pikachu", "站在肩膀上")]:
        facts = await parse_via_markers(pipe, f"<{name}>{scene}")
        assert any(e.name == name for e in facts.entities), f"<{name}> 未被保证为 Entity"


@pytest.mark.asyncio
async def test_explicit_hint_sent_to_extractor(session):
    """extractor 必须知道这些名称是角色（system hint）；user 消息无尖括号。"""
    llm = FakeLLM('{"entities": [], "statements": []}')
    pipe = make_pipe(session, llm)
    await parse_via_markers(pipe, "<花火>站在窗边")
    sys_joined = " ".join(llm.sys_contents)
    assert "USER-DECLARED CHARACTERS" in sys_joined
    assert "花火" in sys_joined
    user_joined = " ".join(llm.user_contents)
    assert "<" not in user_joined and ">" not in user_joined
    assert "花火站在窗边" in user_joined  # clean_text：剥掉尖括号、名称保留


@pytest.mark.asyncio
async def test_marker_never_leaks_into_prompt(session):
    """尖括号不得进入 Entity.name / canonical / caption / final prompt。"""
    session.add(CharacterTriggerCache(name="花火", canonical_tag="huohuo",
                                      caption_name="Huo Huo", series_tag=None, source="online"))
    session.commit()
    llm = FakeLLM('{"entities": [{"id": "c1", "name": "花火"}], '
                   '"statements": [{"kind": "scene", "text": "standing by the window"}]}')
    pipe = make_pipe(session, llm)
    facts = await parse_via_markers(pipe, "<花火>站在窗边")
    for e in facts.entities:
        assert "<" not in e.name and ">" not in e.name
    res = pipe.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "<" not in res.prompt and ">" not in res.prompt
    assert "huohuo" in res.prompt  # canonical tag 正常进入 tag 区


@pytest.mark.asyncio
async def test_explicit_name_not_duplicated_when_extractor_keeps_it(session):
    """extractor 已返回显式名称 → invariant 不重复添加。"""
    llm = FakeLLM('{"entities": [{"id": "c1", "name": "花火"}], "statements": []}')
    pipe = make_pipe(session, llm)
    facts = await parse_via_markers(pipe, "<花火>站在窗边")
    matches = [e for e in facts.entities if e.name == "花火"]
    assert len(matches) == 1, f"不应重复添加: {len(matches)}"