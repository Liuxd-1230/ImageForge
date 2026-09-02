"""PromptWriter 静态视觉态渲染单元测试（无 LLM）— Candidate C。

转移瞬态抑制只在结构组合下生效：
A taking off X + A→B putting X on + B wearing/holding X（同物体）→ 抑制 A 的瞬态。
单独 removal / 无最终态 transfer / 异物体 / 自身换装 均不抑制。
facts 保持原样（只影响渲染）。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.models.prompt_engine import SemanticFacts, Entity, Statement  # noqa: E402
from app.services.prompt_engine.writer import PromptWriter  # noqa: E402


def ent(eid, name, caption=None, tag=None):
    return Entity(id=eid, name=name, source="model_character", canonical_tag=tag, caption_name=caption)


def stmt(kind, subject, target, text):
    return Statement(kind=kind, subject=subject, target=target, text=text)


def A():
    """A 完成转移：taking off hat / A→B putting hat on / B wearing hat → 抑制 A taking off。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui", tag="suisui"),
                  ent("c2", "秧秧", caption="Yangyang", tag="yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c2", None, "wearing a hat"),
            stmt("relation", "c1", "c2", "putting her hat on"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "taking off" not in out, out
    assert "putting her hat on Yangyang" in out, out          # 转移保留
    assert "Yangyang is wearing a hat" in out, out             # 最终态保留
    assert out.count("Suisui") == 1                            # 只作主语，无瞬态
    return out


def B():
    """B 只有摘帽子（无转移/最终态）：必须保留。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui")],
        statements=[stmt("attribute", "c1", None, "taking off her hat")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "taking off" in out, out


def C():
    """C 只有转移动作、无 target final state：转移保留、不抑制、不脑补最终态。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[stmt("relation", "c1", "c2", "putting her hat on")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "putting her hat on Yangyang" in out, out
    assert "wearing" not in out, out          # 没有 facts 时不创造最终态
    assert "taking off" not in out            # 本来就没有 removal


def D():
    """D 异物体：taking off hat + transfer scarf + B wearing scarf → 不得删除 hat。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c2", None, "wearing a scarf"),
            stmt("relation", "c1", "c2", "putting her scarf on"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "taking off" in out, out            # hat removal 保留（物体不同）
    assert "putting her scarf on Yangyang" in out, out


def E():
    """E 同人物自身换装：taking off hat + wearing another hat → 不套用人物间转移规则。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c1", None, "wearing another hat"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "taking off" in out, out


def test_completed_transfer_glasses():
    """同物体多词物体（glasses）：suppression 仍生效。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[
            stmt("attribute", "c1", None, "removing her glasses"),
            stmt("attribute", "c2", None, "wearing glasses"),
            stmt("relation", "c1", "c2", "putting her glasses on"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "removing" not in out, out
    assert "putting her glasses on Yangyang" in out, out


def test_facts_unchanged():
    """抑制只影响渲染，facts 原样保留。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c2", None, "wearing a hat"),
            stmt("relation", "c1", "c2", "putting her hat on"),
        ],
    )
    before = [(s.kind, s.subject, s.target, s.text) for s in facts.statements]
    PromptWriter().write_natural_language_scene(facts)
    after = [(s.kind, s.subject, s.target, s.text) for s in facts.statements]
    assert before == after


def test_real_ownership_case():
    """真实 stress 案例 ownership_hat_transfer_03 的 frozen facts 精确期望。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui", tag="suisui"),
                  ent("c2", "秧秧", caption="Yangyang", tag="yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c2", None, "wearing a hat"),
            stmt("relation", "c1", "c2", "putting her hat on"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c1" not in out and "c2" not in out
    assert "taking off" not in out
    assert "putting her hat on Yangyang" in out
    assert "Yangyang is wearing a hat" in out


def test_possession_with_location_phrase():
    """target final state 带地点短语（'wearing a hat on her head'）仍能正确识别物体。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her hat"),
            stmt("attribute", "c2", None, "wearing a hat on her head"),
            stmt("relation", "c1", "c2", "putting her hat on"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "taking off" not in out, out
    assert "putting her hat on Yangyang" in out, out
    assert "Yangyang is wearing a hat on her head" in out, out


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", fn.__name__, "->", str(e)[:200])
    print(f"\n=== {len(fns) - failed}/{len(fns)} passed ===")
    sys.exit(1 if failed else 0)
