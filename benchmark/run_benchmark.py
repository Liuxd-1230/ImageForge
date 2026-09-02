#!/usr/bin/env python3
"""ImageForge Prompt Benchmark runner — Baseline A.

Runs every case in benchmark/prompt_cases.json through the REAL pipeline and
records each stage:

    INPUT
      ↓  (stage 1) FACT EXTRACTION        extractor.extract
      ↓  (stage 2) CHARACTER RESOLUTION   resolver.resolve_entities_async
      ↓  (stage 3) FINAL FACTS            validator.validate_and_sanitize
      ↓  (stage 4) PROMPT ASSEMBLY        pipeline.build_prompt (safety/artist/lora injected)

Checks are deterministic RULES (entity count / must-have / binding / prohibited
binding / unresolved trigger / source / artist / lora / safety / no-brain-fill).
No LLM-as-judge. Human review of free-text quality happens separately.

Output: benchmark/results/<timestamp>.json + .md
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
    with open(os.path.join(BENCH_DIR, "prompt_cases.json"), "r", encoding="utf-8") as f:
        return json.load(f)["cases"]


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
    """所有与该实体绑定的文本（statement.text + custom_description），用于关键词检查。"""
    parts = [stmt.text or "" for stmt in statements if stmt.subject == entity.id]
    if entity.custom_description:
        parts.append(entity.custom_description)
    return " ".join(parts).lower()


def run_checks(case, final_facts, final_prompt, negative_prompt):
    """确定性规则检查。返回 [(stage, message)]。stage ∈ extraction/character_resolution/
    trigger_resolution/prompt_assembly。"""
    issues = []
    exp = case.get("expect", {})
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
        # character resolution / trigger resolution
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
        # must_have_en（同义词列表：只要有一个命中就算该属性存在并绑定到该实体）
        mh = e.get("must_have_en", [])
        if mh and not any(kw.lower() in entity_text(ent, statements) for kw in mh):
            issues.append(("extraction", f"【{e['name']}】缺少属性 {e.get('label_zh') or mh}"))
        # must_not_have_en（未指定属性不能脑补 / 不得残留被覆盖的属性）
        for kw in e.get("must_not_have_en", []):
            if kw.lower() in entity_text(ent, statements):
                issues.append(("extraction", f"【{e['name']}】出现被禁止/被覆盖的内容 {kw}"))

    # ── 实体占位符泄漏 invariant（精确到本案例事实的实体 id，不笼统删 c数字）──
    for e in final_facts.entities:
        if e.id and re.search(rf"\b{re.escape(str(e.id))}\b", final_prompt):
            issues.append(("prompt_assembly",
                           f"unresolved internal entity reference {e.id} in final prompt"))
            break

    # ── must_not_bind（属性不得绑定到错误实体）──
    for mb in exp.get("must_not_bind", []):
        ent = entities_by_name.get(mb["other"])
        if not ent:
            continue
        if any(mb["keyword_en"].lower() in (s.text or "").lower() and s.subject == ent.id for s in statements):
            issues.append(("extraction", f"错误绑定：{mb['keyword_en']} 出现在【{mb['other']}】上（{mb.get('label_zh') or ''}）"))

    # ── relations（A→B / B→A 主客体）；接受 relation 或带对方引用的 attribute ──
    for r in exp.get("relations", []):
        a = entities_by_name.get(r["from"])
        b = entities_by_name.get(r["to"])
        if not a or not b:
            issues.append(("extraction", f"关系 {r.get('label_zh') or r['from']} 缺少实体"))
            continue
        hit = False
        for s in statements:
            if s.kind == "relation" and s.subject == a.id and s.target == b.id \
               and any(k.lower() in (s.text or "").lower() for k in r["must_have_en"]):
                hit = True
                break
            # attribute 引用对方实体（text 里带 b.id 或 b 的 caption）
            if s.kind == "attribute" and s.subject == a.id \
               and any(k.lower() in (s.text or "").lower() for k in r["must_have_en"]):
                if b.id and re.search(rf"\b{re.escape(str(b.id))}\b", s.text or ""):
                    hit = True
                    break
        if not hit:
            issues.append(("extraction", f"关系未抽取：{r.get('label_zh') or r['from']}→{r['to']}"))

    # ── prompt_assembly ──
    for t in exp.get("artist_tag_present", []):
        # 策略会把下划线格式化为空格（@mika_pikazo → @mika pikazo）
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
    return issues


async def run_case(pipeline, case, frozen_facts=None):
    """跑单个案例。frozen_facts 非空时（Candidate B1）跳过 extraction/resolution，
    只用冻结的 facts 重新执行 Prompt Assembly —— A/B 唯一变量就是 PromptWriter。"""
    rec = {
        "id": case["id"],
        "category": case.get("category", ""),
        "input": case["input"],
        "safety": case.get("safety", "Safe"),
        "mode": "frozen" if frozen_facts is not None else "full",
        "stages": {},
        "checks": [],
        "failed": [],
    }
    try:
        if frozen_facts is None:
            # stage 1: extraction
            raw_facts = await pipeline.extractor.extract(
                user_input=case["input"], rules_context="",
                model=MODEL, reasoning_effort=REASONING,
            )
            rec["stages"]["1_extraction"] = {
                "entities": [e.model_dump() for e in raw_facts.entities],
                "statements": [s.model_dump() for s in raw_facts.statements],
            }
            # stage 2: character resolution
            resolved_entities = await pipeline.resolver.resolve_entities_async(
                entities=raw_facts.entities, statements=raw_facts.statements,
                model=MODEL, reasoning_effort=REASONING,
            )
            rec["stages"]["2_character_resolution"] = {
                "entities": [e.model_dump() for e in resolved_entities],
            }
            # stage 3: final facts (validation)
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
        # stage 4: prompt assembly (safety / artist / lora injection)
        lora_items = [
            LoraBuildItem(filename=li["filename"], trigger_words=li.get("trigger_words", ""),
                          strength=li.get("strength", 0.8), is_enabled=li.get("is_enabled", True))
            for li in case.get("lora_items", [])
        ]
        build = pipeline.build_prompt(PromptBuildRequest(
            facts=facts, safety=case.get("safety", "Safe"),
            artist_tags=case.get("artist_tags", []), lora_items=lora_items,
        ))
        rec["stages"]["4_prompt_assembly"] = {
            "positive": build.prompt,
            "negative": build.negative_prompt,
        }
        rec["final_prompt"] = build.prompt
        rec["negative_prompt"] = build.negative_prompt

        issues = run_checks(case, facts, build.prompt, build.negative_prompt)
        rec["checks"] = [{"stage": s, "message": m} for s, m in issues]
        rec["failed"] = [{"stage": s, "message": m} for s, m in issues]
    except Exception as e:
        rec["stages"]["1_extraction"] = rec["stages"].get("1_extraction", {})
        rec["stages"]["1_extraction"]["error"] = f"{type(e).__name__}: {e}"
        rec["failed"] = [{"stage": "extraction", "message": f"运行异常 {type(e).__name__}: {e}"}]
    return rec


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="ImageForge Prompt Benchmark")
    parser.add_argument("--frozen", type=str, default=None,
                        help="Candidate B1: 冻结 baseline JSON 的 3_final_facts，只重跑 Prompt Assembly")
    args = parser.parse_args()

    cases = load_cases()
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
            tag = "frozen" if frozen is not None else ("no-frozen-facts" if mode == "frozen" else "full")
            print(f"[{idx+1}/{len(cases)}] {case['id']} ({tag}) ...", flush=True)
            rec = await run_case(pipeline, case, frozen_facts=frozen)
            results.append(rec)
            if rec["failed"]:
                for f in rec["failed"]:
                    print(f"    ✗ [{f['stage']}] {f['message']}", flush=True)
            else:
                print("    ✓", flush=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = "_frozen" if mode == "frozen" else ""
    os.makedirs(os.path.join(BENCH_DIR, "results"), exist_ok=True)
    json_path = os.path.join(BENCH_DIR, "results", f"{ts}{suffix}.json")
    md_path = os.path.join(BENCH_DIR, "results", f"{ts}{suffix}.md")

    total = len(results)
    passed = sum(1 for r in results if not r["failed"])
    fail_by_stage = {}
    for r in results:
        for f in r["failed"]:
            fail_by_stage.setdefault(f["stage"], []).append(r["id"])

    report = {
        "timestamp": ts, "model": MODEL, "reasoning_effort": REASONING,
        "mode": mode, "frozen_baseline": args.frozen,
        "total": total, "passed": passed, "failed": total - passed,
        "fail_by_stage": {k: {"count": len(v), "cases": v} for k, v in fail_by_stage.items()},
        "results": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    title = "Candidate B1 (frozen facts — assembly regression)" if mode == "frozen" else "Candidate B2 (full pipeline)"
    lines = [
        f"# ImageForge Prompt Benchmark — {title}",
        "",
        f"- 时间：{ts}",
        f"- 模型：{MODEL}（LM Studio），reasoning={REASONING}",
        f"- 模式：{mode}",
        f"- 总案例：{total}｜通过：{passed}｜失败：{total - passed}",
        "",
        "## 失败阶段分布",
        "",
    ]
    if fail_by_stage:
        for stage, ids in fail_by_stage.items():
            lines.append(f"- **{stage}**：{len(ids)} 例 — {', '.join(ids)}")
    else:
        lines.append("- 无")
    lines += ["", "## 失败明细", ""]
    for r in results:
        if r["failed"]:
            lines.append(f"### {r['id']}（{r['category']}）")
            lines.append(f"- 输入：{r['input']}")
            for f in r["failed"]:
                lines.append(f"- ✗ `{f['stage']}`：{f['message']}")
            lines.append("")
    lines += ["", "## 全部案例最终 Prompt（人工复核用）", ""]
    for r in results:
        lines.append(f"### {r['id']}（{r['category']}）")
        lines.append(f"- 输入：{r['input']}")
        lines.append(f"- Prompt：`{r.get('final_prompt', '')}`")
        lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n===== {passed}/{total} passed =====")
    for stage, ids in fail_by_stage.items():
        print(f"  {stage}: {len(ids)} — {', '.join(ids)}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
