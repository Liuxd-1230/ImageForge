"""显式角色标记 <角色名> pre-parser — 确定性测试。"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.services.prompt_engine.markers import parse_explicit_markers  # noqa: E402


def test_simple_marker():
    clean, names = parse_explicit_markers("<三月七>站在车站里")
    assert clean == "三月七站在车站里"
    assert names == ["三月七"]


def test_multiple_markers():
    clean, names = parse_explicit_markers("<三月七>和<流萤>坐在长椅上")
    assert clean == "三月七和流萤坐在长椅上"
    assert names == ["三月七", "流萤"]


def test_dedupe_and_strip():
    clean, names = parse_explicit_markers("< 穗穗 > <穗穗>")
    assert names == ["穗穗"]
    assert clean == "穗穗 穗穗"


def test_explicit_characters_not_blocked_by_generic():
    # 中文 substring generic 判断已删除：<花火>/<小鸟游六花>/<猫又>/<皮卡丘> 都是显式角色
    for name in ["花火", "小鸟游六花", "猫又", "皮卡丘"]:
        clean, names = parse_explicit_markers(f"<{name}>站在画面中")
        assert names == [name], f"{name} 应被识别为显式角色"
        assert "<" not in clean and ">" not in clean


def test_lora_syntax_not_a_marker():
    clean, names = parse_explicit_markers("<lora:water_dress:1> 画面中只有一个人")
    assert names == []
    assert "<lora:water_dress:1>" in clean  # 原样保留，不被剥离


def test_nested_and_control_not_markers():
    assert parse_explicit_markers("<a<b>c> 内容")[1] == []
    assert parse_explicit_markers("<foo(bar)>")[1] == []
    assert parse_explicit_markers("<a=b>")[1] == []


def test_newline_inside_not_marker():
    assert parse_explicit_markers("<三月\n七>")[1] == []


def test_too_long_not_marker():
    assert parse_explicit_markers("<" + "三" * 70 + ">")[1] == []


def test_empty_angle_not_marker():
    assert parse_explicit_markers("<>内容")[1] == []


def test_no_markers():
    clean, names = parse_explicit_markers("普通句子，没有尖括号")
    assert clean == "普通句子，没有尖括号"
    assert names == []


def test_unclosed_bracket_left_as_is():
    clean, names = parse_explicit_markers("看<没闭合")
    assert names == []
    assert "<" in clean
