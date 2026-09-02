"""PromptWriter relation-target 代词渲染单测（无 LLM）— Candidate D1。

只替换 relation 介词宾语位的 target 代词（on/to/around/... her/him/them → target 名）；
不全局替换 her/him/them；已含 target 名不重复追加。
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


def render(text, target_name):
    return PromptWriter._render_relation_target(text, target_name)


def test_on_her():
    assert render("putting the coat on her", "Yangyang") == "putting the coat on Yangyang"


def test_to_him():
    assert render("handing the book to him", "Yangyang") == "handing the book to Yangyang"


def test_around_her():
    assert render("wrapping the scarf around her", "Xiaoxia") == "wrapping the scarf around Xiaoxia"


def test_onto_them():
    assert render("putting the blanket onto them", "Xiaoxia") == "putting the blanket onto Xiaoxia"


def test_holding_her_own_hat_untouched():
    """非 relation 宾语位代词不得替换。"""
    assert render("holding her own hat", "Yangyang") == "holding her own hat"


def test_no_target_pronoun_untouched():
    assert render("putting hat on", "Yangyang") == "putting hat on"  # 无代词，保持原样（由外层追加）


def test_already_contains_target_no_duplication():
    """relation text 已含 target 名 → 追加逻辑应跳过（rendering 整体验证）。"""
    facts = SemanticFacts(
        entities=[ent("c1", "秧秧", caption="Yangyang"), ent("c2", "穗穗", caption="Suisui")],
        statements=[stmt("relation", "c1", "c2", "hugging Suisui")],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert out == "Yangyang is hugging Suisui.", out
    assert out.count("Suisui") == 1


def test_real_coat_case_no_double_name():
    """真实 coat 案例：putting the coat on her + target 秧秧 → on Yangyang，不得 on her Yangyang。"""
    facts = SemanticFacts(
        entities=[ent("c1", "穗穗", caption="Suisui", tag="suisui"),
                  ent("c2", "秧秧", caption="Yangyang", tag="yangyang")],
        statements=[
            stmt("attribute", "c1", None, "taking off her coat"),
            stmt("relation", "c1", "c2", "putting the coat on her"),
        ],
    )
    out = PromptWriter().write_natural_language_scene(facts)
    assert "her Yangyang" not in out, out
    assert "putting the coat on Yangyang" in out, out


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
