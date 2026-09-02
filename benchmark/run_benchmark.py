#!/usr/bin/env python3
"""ImageForge Prompt Benchmark runner.

Runs every case in benchmark/prompt_cases.json (Baseline) + stress_cases.json
(Stress) through the REAL pipeline and records each stage:

    INPUT
      ↓  (stage 1) FACT EXTRACTION        extractor.extract
      ↓  (stage 2) CHARACTER RESOLUTION   resolver.resolve_entities_async
      ↓  (stage 3) FINAL FACTS            validator.validate_and_sanitize
      ↓  (stage 4) PROMPT ASSEMBLY        pipeline.build_prompt (safety/artist/lora injected)

Checks are deterministic RULES (no LLM judge). Stress features:
  - variants: 同一输入只抽取一次，按 variant 组装（Artist/LoRA/Safety），并做 scene 文本不变性检查
  - ambiguity_expected / capability_gap 分类
  - --repeat: 对失败案例重跑 N 次，按稳定性分类（deterministic / highly_reproducible /
    intermittent / unstable_extraction）
Output: benchmark/results/stress_<timestamp>.json + .md
"""
import asyncio
import json
import os
import re
import sys
import time

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BENCH_DIR, "..", "backend"))

from sqlmodel import Session, create_engine, SQLModel  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.preset import Preset  # noqa: E402
from app.models.trigger_cache import CharacterTriggerCache  # noqa: E402
from app.models.prompt_engine import (  # noqa: E402
    SemanticFacts, PromptBuildRequest, LoraBuildItem,
)
from app.services.llm.lm_studio import LMStudioProvider  # noqa: E402
from app.services.prompt_engine.pipeline import PromptPipeline  # noqa: E402

LM_BASE = "http://127.0.0.1:1234"
MODEL = "qwen3.6-35b-a3b-uncensored-genesis-hermes-v6"
REASONING = "off"


def load_cases():
    cases = []
    with open(os.path.join(BENCH_DIR, "prompt_cases.json"), "r", encoding="utf-8") as f:
        for c in json.load(f)["cases"]:
            c["dataset"] = "baseline"
            cases.append(c)
    with open(os.path.join(BENCH_DIR, "stress_cases.json"), "r", encoding="utf-8") as f:
        for c in json.load(f)["cases"]:
            c["dataset"] = "stress"
            cases.append(c)
    return cases


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Preset(name="Default", positive_prefix="",
                     default_negative="lowres, bad anatomy, bad hands, text", is_default=True))
        # 角色书：小雨（默认绿色背带裙 / 棕色双马尾）
        s.add(Character(
            name="小雨", gender="girl", age_group="young adult", body="petite",
            hair_color="brown", hair_style="twintails", hair_length="long",
            top="绿色背带裙", default_expression="cheerful",
        ))
        # Trigger 缓存（与 App 真实使用一致：已解析过的角色会写入 cache）
        s.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui", caption_name="Suisui"))
        s.add(CharacterTriggerCache(name="秧秧", canonical_tag="yangyang", caption_name="Yangyang"))
        s.add(CharacterTriggerCache(name="小夏", canonical_tag="xiaoxia", caption_name="Xiaoxia"))
        s.commit()
    return engine


def entity_text(entity, statements):
    parts = [stmt.text or "" for stmt in statements if stmt.subject == entity.id]
    if entity.custom_description:
        parts.append(entity.custom_description)
    return " ".join(parts).lower()


def matches_kw(text: str, kw: str) -> bool:
    """关键词匹配：容忍英文动词 -ing 变形（smile ↔ smiling，wave ↔ waving）。
    kw 本身或其去尾 e 的词干出现在 text 即命中。"""
    k = kw.lower()
    if k in text:
        return True
    if k.endswith("e") and len(k) > 3 and k[:-1] in text:
        return True
    return False


def run_checks(case, final_facts, final_prompt, negative_prompt, variant_meta=None):
    """确定性规则检查。返回 [(stage, message)]。"""
    issues = []
    exp = dict(case.get("expect", {}))
    if variant_meta:
        if variant_meta.get("expect_artist"):
            exp["artist_tag_present"] = variant_meta["expect_artist"]
        if variant_meta.get("expect_lora"):
            exp["lora_trigger_present"] = variant_meta["expect_lora"]
        if variant_meta.get("expect_safety"):
            exp["safety_tag"] = variant_meta["expect_safety"]
        if variant_meta.get("expect_lora_no"):
            exp["lora_no_trigger"] = variant_meta["expect_lora_no"]
    entities_by_name = {e.name: e for e in final_facts.entities}
    statements = final_facts.statements

    # ── extraction: entity 数量 ──
    ec = exp.get("entity_count")
    if ec is not None and len(final_facts.entities) != ec:
        issues.append(("extraction", f"实体数量 {len(final_facts.entities)} != 预期 {ec}"))

    # ── per entity ──
    for e in exp.get("entities", []):
        ent = entities_by_name.get(e["name"])
        if not ent:
            issues.append(("extraction", f"缺少实体【{e['name']}】"))
            continue
        src = e.get("source")
        if src and ent.source != src:
            issues.append(("character_resolution", f"【{e['name']}】来源 {ent.source} != 预期 {src}"))
        if ent.source == "model_character" and not ent.canonical_tag:
            issues.append(("trigger_resolution", f"【{e['name']}】model_character 未解析 canonical_tag"))
        if ent.source == "user_defined" and not ent.custom_description:
            issues.append(("character_resolution", f"【{e['name']}】角色书实体缺少 custom_description"))
        for kw in e.get("rolebook_keywords", []):
            if kw.lower() not in (ent.custom_description or "").lower():
                issues.append(("character_resolution", f"【{e['name']}】角色书属性 {kw} 未出现在描述中"))
        mh = e.get("must_have_en", [])
        if mh and not any(matches_kw(entity_text(ent, statements), kw) for kw in mh):
            issues.append(("extraction", f"【{e['name']}】缺少属性 {e.get('label_zh') or mh}"))
        for kw in e.get("must_not_have_en", []):
            if matches_kw(entity_text(ent, statements), kw):
                issues.append(("extraction", f"【{e['name']}】出现被禁止/被覆盖的内容 {kw}"))

    # ── any_has_en：任一关键词在任一实体上命中即过（匿名/共享属性用）──
    ah = exp.get("any_has_en", [])
    if ah and not any(matches_kw(entity_text(e, statements), kw) for e in final_facts.entities for kw in ah):
        issues.append(("extraction", f"没有任何实体包含 {ah}"))

    # ── 实体占位符泄漏 invariant ──
    for e in final_facts.entities:
        if e.id and re.search(rf"\b{re.escape(str(e.id))}\b", final_prompt):
            issues.append(("prompt_assembly",
                           f"unresolved internal entity reference {e.id} in final prompt"))
            break

    # ── must_not_bind ──
    for mb in exp.get("must_not_bind", []):
        ent = entities_by_name.get(mb["other"])
        if not ent:
            continue
        if any(matches_kw(s.text or "", mb["keyword_en"]) and s.subject == ent.id for s in statements):
            issues.append(("extraction", f"错误绑定：{mb['keyword_en']} 出现在【{mb['other']}】上（{mb.get('label_zh') or ''}）"))

    # ── relations ──
    for r in exp.get("relations", []):
        a = entities_by_name.get(r["from"])
        b = entities_by_name.get(r["to"])
        if not a or not b:
            issues.append(("extraction", f"关系 {r.get('label_zh') or r['from']} 缺少实体"))
            continue
        hit = False
        for s in statements:
            if s.kind == "relation" and s.subject == a.id and s.target == b.id \
               and any(matches_kw(s.text or "", k) for k in r["must_have_en"]):
                hit = True
                break
            if s.kind == "attribute" and s.subject == a.id \
               and any(matches_kw(s.text or "", k) for k in r["must_have_en"]):
                if b.id and re.search(rf"\b{re.escape(str(b.id))}\b", s.text or ""):
                    hit = True
                    break
        if not hit:
            issues.append(("extraction", f"关系未抽取：{r.get('label_zh') or r['from']}→{r['to']}"))

    # ── prompt_assembly ──
    for t in exp.get("artist_tag_present", []):
        norm = t.lower().replace("_", " ")
        if norm not in final_prompt.lower().replace("_", " "):
            issues.append(("prompt_assembly", f"artist tag {t} 未出现在最终 Prompt"))
    for t in exp.get("lora_trigger_present", []):
        if t.lower() not in final_prompt.lower():
            issues.append(("prompt_assembly", f"LoRA trigger {t} 未出现在最终 Prompt"))
    for t in exp.get("lora_no_trigger", []):
        if t.lower() in final_prompt.lower():
            issues.append(("prompt_assembly", f"无 trigger 的 LoRA 不应注入 {t}"))
    if exp.get("safety_tag"):
        if exp["safety_tag"].lower() not in final_prompt.lower():
            issues.append(("prompt_assembly", f"safety tag {exp['safety_tag']} 未出现在最终 Prompt"))
    # ── 渲染级检查（final prompt 层面，assembly 阶段）──
    for kw in exp.get("prompt_has_en", []):
        if not matches_kw(final_prompt, kw):
            issues.append(("prompt_assembly", f"最终 Prompt 缺少 {kw}"))
    for kw in exp.get("prompt_not_has_en", []):
        if matches_kw(final_prompt, kw):
            issues.append(("prompt_assembly", f"最终 Prompt 不得出现瞬态/冲突片段 {kw}"))
    return issues


def _build_lora_items(items):
    return [
        LoraBuildItem(filename=li["filename"], trigger_words=li.get("trigger_words", ""),
                      strength=li.get("strength", 0.8), is_enabled=li.get("is_enabled", True))
        for li in (items or [])
    ]


async def run_case(pipeline, case, frozen_facts=None):
    rec = {
        "id": case["id"],
        "dataset": case.get("dataset", "baseline"),
        "category": case.get("category", ""),
        "input": case["input"],
        "safety": case.get("safety", "Safe"),
        "expected": case.get("expect", {}),
        "ambiguity_expected": bool(case.get("ambiguity_expected")),
        "capability_gap": case.get("capability_gap"),
        "mode": "frozen" if frozen_facts is not None else "full",
        "stages": {},
        "checks": [],
        "failed": [],
        "variant_results": [],
    }
    try:
        if frozen_facts is None:
            raw_facts = await pipeline.extractor.extract(
                user_input=case["input"], rules_context="",
                model=MODEL, reasoning_effort=REASONING,
            )
            rec["stages"]["1_extraction"] = {
                "entities": [e.model_dump() for e in raw_facts.entities],
                "statements": [s.model_dump() for s in raw_facts.statements],
            }
            resolved_entities = await pipeline.resolver.resolve_entities_async(
                entities=raw_facts.entities, statements=raw_facts.statements,
                model=MODEL, reasoning_effort=REASONING,
            )
            rec["stages"]["2_character_resolution"] = {
                "entities": [e.model_dump() for e in resolved_entities],
            }
            facts = pipeline.validator.validate_and_sanitize(
                SemanticFacts(entities=resolved_entities, statements=raw_facts.statements)
            )
        else:
            facts = frozen_facts
            rec["stages"]["1_extraction"] = {"frozen": True}
            rec["stages"]["2_character_resolution"] = {"frozen": True}
        rec["stages"]["3_final_facts"] = {
            "entities": [e.model_dump() for e in facts.entities],
            "statements": [s.model_dump() for s in facts.statements],
        }

        variants = case.get("variants")
        if variants:
            for v in variants:
                build = pipeline.build_prompt(PromptBuildRequest(
                    facts=facts,
                    safety=v.get("safety", case.get("safety", "Safe")),
                    artist_tags=v.get("artist_tags", case.get("artist_tags", [])),
                    lora_items=_build_lora_items(v.get("lora_items", case.get("lora_items", []))),
                ))
                issues = run_checks(case, facts, build.prompt, build.negative_prompt, variant_meta=v)
                rec["variant_results"].append({
                    "name": v.get("name", "variant"),
                    "final_prompt": build.prompt,
                    "negative": build.negative_prompt,
                    "failed": [{"stage": s, "message": m} for s, m in issues],
                })
            # scene 文本不变性：同一 facts 下，组件（Artist/LoRA/Safety）不得改变 scene 部分
            if len(rec["variant_results"]) > 1:
                nls = []
                for vr in rec["variant_results"]:
                    p = vr["final_prompt"]
                    nls.append(p.split(". ", 1)[1] if ". " in p else p)
                if len(set(nls)) != 1:
                    for vr in rec["variant_results"]:
                        vr["failed"].append({"stage": "prompt_assembly",
                                             "message": "variants 间 scene 文本不一致（组件不应改变人物/场景语义）"})
            rec["final_prompt"] = rec["variant_results"][0]["final_prompt"]
            rec["negative_prompt"] = rec["variant_results"][0]["negative"]
            for vr in rec["variant_results"]:
                for f in vr["failed"]:
                    f2 = dict(f)
                    f2["variant"] = vr["name"]
                    rec["failed"].append(f2)
        else:
            build = pipeline.build_prompt(PromptBuildRequest(
                facts=facts, safety=case.get("safety", "Safe"),
                artist_tags=case.get("artist_tags", []),
                lora_items=_build_lora_items(case.get("lora_items", [])),
            ))
            rec["stages"]["4_prompt_assembly"] = {
                "positive": build.prompt, "negative": build.negative_prompt,
            }
            rec["final_prompt"] = build.prompt
            rec["negative_prompt"] = build.negative_prompt
            issues = run_checks(case, facts, build.prompt, build.negative_prompt)
            rec["failed"] = [{"stage": s, "message": m} for s, m in issues]
    except Exception as e:
        rec["stages"]["1_extraction"] = rec["stages"].get("1_extraction", {})
        rec["stages"]["1_extraction"]["error"] = f"{type(e).__name__}: {e}"
        rec["failed"] = [{"stage": "extraction", "message": f"运行异常 {type(e).__name__}: {e}"}]
    return rec


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="ImageForge Prompt Benchmark (Baseline + Stress)")
    parser.add_argument("--frozen", type=str, default=None,
                        help="冻结 baseline JSON 的 3_final_facts，只重跑 Prompt Assembly")
    parser.add_argument("--repeat", type=int, default=0,
                        help="对失败案例重跑次数（默认 0；Stress 用 3）")
    parser.add_argument("--only", type=str, default=None,
                        help="只跑指定 dataset（baseline/stress）")
    parser.add_argument("--limit", type=int, default=None,
                        help="只跑前 N 个案例（冒烟用）")
    args = parser.parse_args()

    cases = load_cases()
    if args.only:
        cases = [c for c in cases if c.get("dataset") == args.only]
    if args.limit:
        cases = cases[: args.limit]
    engine = setup_db()

    frozen_by_id = {}
    mode = "full"
    if args.frozen:
        mode = "frozen"
        with open(args.frozen, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        for br in baseline.get("results", []):
            ff = (br.get("stages") or {}).get("3_final_facts")
            if ff:
                frozen_by_id[br["id"]] = SemanticFacts(**ff)

    llm = LMStudioProvider(base_url=LM_BASE, api_key="")
    with Session(engine) as session:
        pipeline = PromptPipeline(session=session, llm_provider=llm)
        results = []
        for idx, case in enumerate(cases):
            frozen = frozen_by_id.get(case["id"])
            tag = "frozen" if frozen is not None else "full"
            print(f"[{idx+1}/{len(cases)}] {case['id']} ({case.get('dataset')}/{tag}) ...", flush=True)
            rec = await run_case(pipeline, case, frozen_facts=frozen)
            results.append(rec)
            if rec["failed"]:
                for f in rec["failed"]:
                    print(f"    ✗ [{f['stage']}] {f['message']}", flush=True)
            else:
                print("    ✓", flush=True)

        # ── 失败重跑（稳定性分类）──
        if args.repeat > 0:
            print(f"\n=== 失败案例重跑 {args.repeat} 次（稳定性分类）===", flush=True)
            for rec in results:
                if not rec["failed"]:
                    continue
                case = next(c for c in cases if c["id"] == rec["id"])
                fails = 1
                for i in range(args.repeat):
                    print(f"  re-run {rec['id']} ({i+1}/{args.repeat}) ...", flush=True)
                    r2 = await run_case(pipeline, case)
                    if r2["failed"]:
                        fails += 1
                rec["repeat"] = {"attempts": 1 + args.repeat, "fails": fails}
                if fails >= 1 + args.repeat:
                    rec["stability"] = "deterministic"
                elif fails >= max(2, (1 + args.repeat) // 2):
                    rec["stability"] = "highly_reproducible"
                elif fails == 1:
                    rec["stability"] = "unstable_extraction"
                else:
                    rec["stability"] = "intermittent"
                print(f"  → {rec['id']}: {fails}/{1+args.repeat} fail -> {rec['stability']}", flush=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = "_frozen" if mode == "frozen" else ""
    os.makedirs(os.path.join(BENCH_DIR, "results"), exist_ok=True)
    json_path = os.path.join(BENCH_DIR, "results", f"stress_{ts}{suffix}.json")
    md_path = os.path.join(BENCH_DIR, "results", f"stress_{ts}{suffix}.md")

    total = len(results)
    passed = sum(1 for r in results if not r["failed"])
    baseline_n = sum(1 for r in results if r["dataset"] == "baseline")
    baseline_pass = sum(1 for r in results if r["dataset"] == "baseline" and not r["failed"])
    stress_n = sum(1 for r in results if r["dataset"] == "stress")
    stress_pass = sum(1 for r in results if r["dataset"] == "stress" and not r["failed"])

    # fail_by_stage 按 unique 失败案例统计；failed_checks_by_stage 记录失败 constraint 总数
    fail_by_stage: dict = {}
    fail_checks_by_stage: dict = {}
    fail_by_category: dict = {}
    for r in results:
        if r["failed"]:
            for f in r["failed"]:
                fail_checks_by_stage[f["stage"]] = fail_checks_by_stage.get(f["stage"], 0) + 1
                s = fail_by_stage.setdefault(f["stage"], set())
                s.add(r["id"])
            fail_by_category.setdefault(r["category"], []).append(r["id"])
    fail_by_stage = {k: {"count": len(v), "cases": sorted(v)} for k, v in fail_by_stage.items()}

    deterministic = [r["id"] for r in results if r.get("stability") == "deterministic"]
    high_rep = [r["id"] for r in results if r.get("stability") == "highly_reproducible"]
    intermittent = [r["id"] for r in results if r.get("stability") == "intermittent"]
    unstable = [r["id"] for r in results if r.get("stability") == "unstable_extraction"]
    ambiguous_cases = [r["id"] for r in results if r["ambiguity_expected"]]
    gap_cases = [r["id"] for r in results if r["capability_gap"] and r["failed"]]
    gap_ok_cases = [r["id"] for r in results if r["capability_gap"] and not r["failed"]]

    report = {
        "timestamp": ts, "model": MODEL, "reasoning_effort": REASONING,
        "mode": mode, "repeat": args.repeat,
        "total": total, "passed": passed, "failed": total - passed,
        "baseline": {"total": baseline_n, "passed": baseline_pass},
        "stress": {"total": stress_n, "passed": stress_pass},
        "fail_by_stage": {k: {"count": len(v), "cases": v} for k, v in fail_by_stage.items()},
        "failed_checks_by_stage": fail_checks_by_stage,
        "fail_by_category": {k: {"count": len(v), "cases": v} for k, v in fail_by_category.items()},
        "stability": {
            "deterministic": deterministic, "highly_reproducible": high_rep,
            "intermittent": intermittent, "unstable_extraction": unstable,
        },
        "ambiguous_cases": ambiguous_cases,
        "capability_gaps_failed": gap_cases,
        "capability_gaps_passed": gap_ok_cases,
        "results": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    title = "Semantic Stress Benchmark"
    lines = [
        f"# ImageForge Prompt Benchmark — {title}",
        "",
        f"- 时间：{ts}",
        f"- 模型：{MODEL}（LM Studio），reasoning={REASONING}",
        f"- 总案例：{total}｜通过：{passed}｜失败：{total - passed}（PASS rate {passed/total:.0%}）",
        f"- Baseline 25：{baseline_pass}/{baseline_n}",
        f"- Stress：{stress_pass}/{stress_n}",
        f"- 失败重跑：{args.repeat} 次/例",
        "",
        "## 按失败阶段分布", "",
    ]
    if fail_by_stage:
        for stage, ids in fail_by_stage.items():
            lines.append(f"- **{stage}**：{len(ids)} 例 — {', '.join(ids)}")
    else:
        lines.append("- 无")
    lines += ["", "## 按 Stress 类别分布", ""]
    if fail_by_category:
        for cat, ids in fail_by_category.items():
            lines.append(f"- {cat}：{len(ids)} 例 — {', '.join(ids)}")
    else:
        lines.append("- 无")
    lines += ["", "## 稳定性分类", ""]
    lines.append(f"- **deterministic**（首跑+重跑全失败）：{', '.join(deterministic) if deterministic else '无'}")
    lines.append(f"- **highly_reproducible**：{', '.join(high_rep) if high_rep else '无'}")
    lines.append(f"- **intermittent**：{', '.join(intermittent) if intermittent else '无'}")
    lines.append(f"- **unstable_extraction**（仅 1 次失败）：{', '.join(unstable) if unstable else '无'}")
    lines += ["", "## 歧义案例", ""]
    lines.append(f"- {', '.join(ambiguous_cases) if ambiguous_cases else '无'}")
    lines += ["", "## Capability Gaps", ""]
    if gap_cases:
        for r in results:
            if r["capability_gap"] and r["failed"]:
                lines.append(f"- **{r['id']}**：{r['capability_gap']}")
    else:
        lines.append("- 无")
    if gap_ok_cases:
        lines.append(f"- 已声明但未触发（本案例恰好通过）：{', '.join(gap_ok_cases)}")
    lines += ["", "## 失败案例明细", ""]
    for r in results:
        if r["failed"]:
            lines.append(f"### {r['id']}（{r['category']}｜{r['dataset']}）")
            lines.append(f"- 输入：{r['input']}")
            lines.append(f"- 预期：`{json.dumps(r['expected'], ensure_ascii=False)}`")
            extr = r["stages"].get("1_extraction", {})
            if isinstance(extr, dict) and "error" in extr:
                lines.append(f"- extraction error：{extr['error']}")
            ff = r["stages"].get("3_final_facts", {})
            if ff:
                lines.append(f"- final facts：`{json.dumps(ff, ensure_ascii=False)[:600]}`")
            lines.append(f"- final prompt：`{r.get('final_prompt', '')}`")
            for f in r["failed"]:
                vtag = f.get("variant", "")
                lines.append(f"- ✗ `{f['stage']}`{f'（{vtag}）' if vtag else ''}：{f['message']}")
            if r.get("repeat"):
                lines.append(f"- 重跑：{r['repeat']['fails']}/{r['repeat']['attempts']} → {r.get('stability')}")
            lines.append("")
    lines += ["", "## 全部案例最终 Prompt（人工复核用）", ""]
    for r in results:
        lines.append(f"### {r['id']}（{r['category']}）")
        lines.append(f"- 输入：{r['input']}")
        lines.append(f"- Prompt：`{r.get('final_prompt', '')}`")
        lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n===== {passed}/{total} passed (baseline {baseline_pass}/{baseline_n}, stress {stress_pass}/{stress_n}) =====")
    for stage, info in fail_by_stage.items():
        print(f"  {stage}: {info['count']} case(s) — {', '.join(info['cases'])}")
    if args.repeat:
        print(f"  deterministic: {deterministic}")
        print(f"  high_rep: {high_rep}")
        print(f"  intermittent: {intermittent}")
        print(f"  unstable: {unstable}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
