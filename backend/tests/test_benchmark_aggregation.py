"""Benchmark 报告聚合的确定性测试（无 LLM）— D9 follow-up。

验证 fail_by_stage 的 unique-case 语义与输出结构：
  {stage: {"count": unique_cases, "cases": [ids]}}
  failed_checks_by_stage: {stage: failed_check_count}
不再出现外层 count=dict 键数、cases 嵌套对象的旧 bug。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "benchmark"))

from run_benchmark import summarize_failures  # noqa: E402


def mk_result(cid, failed, category="x"):
    return {"id": cid, "dataset": "stress", "category": category, "failed": failed}


def test_unique_case_count_not_check_count():
    """同一案例多个失败 constraint 只算 1 个 unique case。"""
    results = [
        mk_result("a", [
            {"stage": "extraction", "message": "m1"},
            {"stage": "extraction", "message": "m2"},
            {"stage": "prompt_assembly", "message": "m3"},
        ]),
        mk_result("b", [{"stage": "extraction", "message": "m4"}]),
        mk_result("c", []),
    ]
    fbs, fcs, fbc = summarize_failures(results)
    assert fbs["extraction"] == {"count": 2, "cases": ["a", "b"]}, fbs["extraction"]
    assert fbs["prompt_assembly"] == {"count": 1, "cases": ["a"]}, fbs["prompt_assembly"]
    assert fcs["extraction"] == 3, fcs          # a 有 2 个 extraction checks + b 1 个
    assert fcs["prompt_assembly"] == 1, fcs
    assert fbc == {"x": ["a", "b"]}, fbc


def test_no_nested_object_bug():
    """旧 bug：外层 count=dict 键数(2)、cases=整个 dict。新结构必须是 flat list。"""
    results = [
        mk_result("p", [{"stage": "extraction", "message": "x"}]),
        mk_result("q", [{"stage": "extraction", "message": "y"}, {"stage": "extraction", "message": "z"}]),
        mk_result("r", [{"stage": "extraction", "message": "w"}]),
    ]
    fbs, fcs, _ = summarize_failures(results)
    e = fbs["extraction"]
    assert e["count"] == 3, e            # 3 个 unique cases，而非 2（旧 bug 数 dict 键）
    assert isinstance(e["cases"], list), e
    assert e["cases"] == ["p", "q", "r"], e
    assert fcs["extraction"] == 4, fcs   # failed checks = 4


def test_all_pass_no_stages():
    results = [mk_result("ok", []), mk_result("ok2", [])]
    fbs, fcs, fbc = summarize_failures(results)
    assert fbs == {} and fcs == {} and fbc == {}


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
