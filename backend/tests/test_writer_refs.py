"""PromptWriter 确定性单元测试（无 LLM）— Candidate B 实体引用解析。

覆盖：
1. "c2's" → "Suisui's"（所有格）
2. "holding hands with c2" → 引用替换（attribute 文本）
3. relation 文本已含 target 名 → 不重复追加
4. c1 与 c10 同时存在 → 不发生部分替换（boundary-aware）
5. 未知 c99 → 不偷偷映射，保留给 validator/benchmark 报告
6. scene / general 中的已知实体 id → 同样解析
7. 原失败案例 action_b_to_a_08 / complex_long_25 的精确期望
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


def test_possessive_ref():
    """1. c2's → Suisui's，且 relation 不重复追加 target。"""
    facts = SemanticFacts(
        entities=[ent("c1", "秧秧", caption="Yangyang", tag="yangyang"),
                  ent("c2", "穗穗", caption="Suisui", tag="suisui")],
        statements=[stmt("relation", "c1", "c2", "catching up with c2 and holding c2's wrist")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c2" not in out and "c1" not in out
    assert "holding Suisui's wrist" in out
    assert "catching up with Suisui" in out
    assert out.count("Suisui") == 2, out  # 无 "…Suisui Suisui" 追加
    assert out.startswith("Yangyang is ")


def test_plain_ref_in_attribute():
    """2. attribute 文本里的实体引用也解析。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[stmt("attribute", "c1", None, "holding hands with c2")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c2" not in out
    assert "holding hands with Yangyang" in out
    assert out.count("Yangyang") == 1


def test_relation_target_already_present():
    """3. relation 文本已含 target 名 → 不追加。"""
    facts = SemanticFacts(
        entities=[ent("c1", "秧秧", caption="Yangyang"), ent("c2", "穗穗", caption="Suisui")],
        statements=[stmt("relation", "c1", "c2", "hugging Suisui")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert out == "Yangyang is hugging Suisui.", out
    assert out.count("Suisui") == 1


def test_c1_vs_c10_no_partial():
    """4. c1 与 c10 同时存在：boundary-aware，不发生部分替换。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c10", "小十", caption="Ten")],
        statements=[
            stmt("attribute", "c1", None, "standing next to c10"),
            stmt("attribute", "c10", None, "with c1 and c10"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c10" not in out and "c1" not in out
    assert "standing next to Ten" in out
    assert "with Suisui and Ten" in out


def test_unknown_ref_kept():
    """5. 未知 c99 不偷偷映射，保留给 validator/benchmark 报告。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui")],
        statements=[stmt("attribute", "c1", None, "talking to c99")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c99" in out
    assert "c1" not in out


def test_scene_general_refs():
    """6. scene / general 中的已知实体 id 同样解析。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui")],
        statements=[
            stmt("scene", None, None, "c1 is near the sea"),
            stmt("general", None, None, "the camera focuses on c1"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c1" not in out
    assert "Suisui is near the sea" in out
    assert "the camera focuses on Suisui" in out


def test_original_action_b_to_a():
    """原失败案例 action_b_to_a_08：无 c1/c2 泄漏，动作方向不变。"""
    facts = SemanticFacts(
        entities=[ent("c1", "秧秧", caption="Yangyang", tag="yangyang"),
                  ent("c2", "穗穗", caption="Suisui", tag="suisui")],
        statements=[
            stmt("attribute", "c1", None, "catching up with c2"),
            stmt("relation", "c1", "c2", "holding c2's wrist"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c1" not in out and "c2" not in out
    assert out == "Yangyang is catching up with Suisui and holding Suisui's wrist.", out
    assert out.count("Suisui") == 2


def test_original_complex_long():
    """原失败案例 complex_long_25：holding hands 无泄漏，绑定不破坏。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui"), ent("c2", "秧秧", caption="Yangyang")],
        statements=[
            stmt("scene", None, None, "at the seaside at dusk"),
            stmt("attribute", "c1", None, "wearing a white swimsuit"),
            stmt("attribute", "c1", None, "holding hands with c2"),
            stmt("attribute", "c2", None, "smiling"),
            stmt("attribute", "c1", None, "looking at the distant sunset"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "c2" not in out and "c1" not in out
    assert "holding hands with Yangyang" in out
    assert "wearing a white swimsuit" in out  # 泳装只属于 Suisui
    # Yangyang 出现 2 次：Suisui 句里的引用 + 秧秧自己作为主语（smiling）——都正确
    assert out.count("Yangyang") == 2, out
    assert "Yangyang is smiling" in out  # 两人 smiling 保留
    assert "at the seaside at dusk" in out  # 场景保留


def test_name_priority_fallback():
    """名称优先级：caption_name → canonical_tag → name → the character。"""
    facts = SemanticFacts(
        entities=[ent("c1", "路人甲", tag="tag_only", caption=None),
                  ent("c2", "路人乙", tag=None, caption=None)],
        statements=[stmt("attribute", "c1", None, "standing"), stmt("attribute", "c2", None, "sitting")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "tag_only is standing" in out or "tag_only standing" in out
    assert "路人乙 sitting" in out or "路人乙 is sitting" in out


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
