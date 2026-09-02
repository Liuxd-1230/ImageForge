#!/usr/bin/env python3
"""Candidate E — character entity boundary stability.

对带 e_contract 的案例各跑 N 次完整 pipeline，统计：
  - contract_held: 案例确定性检查全过（entity_count / 物体保留 / 无多余实体）
  - entity_count 实际值分布（验证 generic 动物/物件/车辆不成 entity、具名非人角色不被过滤）
输出 JSON/MD。
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_benchmark import load_cases, setup_db, run_case  # noqa: E402
from app.services.llm.lm_studio import LMStudioProvider  # noqa: E402
from app.services.prompt_engine.pipeline import PromptPipeline  # noqa: E402
from sqlmodel import Session  # noqa: E402

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = "qwen3.6-35b-a3b-uncensored-genesis-hermes-v6"
REASONING = "off"


def entity_names(rec):
    return [e["name"] for e in rec.get("stages", {}).get("3_final_facts", {}).get("entities", [])]


async def main():
    cases = [c for c in load_cases() if c.get("e_contract")]
    engine = setup_db()
    llm = LMStudioProvider(base_url="http://127.0.0.1:1234", api_key="")
    with Session(engine) as session:
        pipeline = PromptPipeline(session=session, llm_provider=llm)
        rows = []
        for case in cases:
            ec = case["e_contract"]
            pass_n = 0
            counts = {}
            recs = []
            for i in range(4):
                print(f"[{case['id']}] run {i+1}/4 ...", flush=True)
                rec = await run_case(pipeline, case)
                recs.append(rec)
                if not rec["failed"]:
                    pass_n += 1
                n = len(rec.get("stages", {}).get("3_final_facts", {}).get("entities", []))
                counts[n] = counts.get(n, 0) + 1
            rows.append({
                "id": case["id"], "mode": ec.get("mode"), "input": case["input"],
                "expected_entity_count": ec.get("expected_entity_count"),
                "passed": pass_n, "runs": 4,
                "entity_count_dist": counts,
                "entity_names": [entity_names(r) for r in recs],
                "contract_held": pass_n == 4,
            })

    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(BENCH_DIR, "results", f"entity_boundary_{ts}.json")
    md_path = os.path.join(BENCH_DIR, "results", f"entity_boundary_{ts}.md")

    lines = ["# Candidate E — Character Entity Boundary Stability", "",
             f"- 时间：{ts}｜每例 4 次全量 pipeline", ""]
    for r in rows:
        lines.append(f"### {r['id']}（{r['mode']}）")
        lines.append(f"- 输入：{r['input']}")
        lines.append(f"- 通过：{r['passed']}/4（{'✓ contract' if r['contract_held'] else '✗ 不稳定'}）")
        lines.append(f"- entity_count 分布：{json.dumps(r['entity_count_dist'])}（期望 {r['expected_entity_count']}）")
        lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "rows": rows}, f, ensure_ascii=False, indent=2)

    print(f"\n===== entity boundary stability =====")
    for r in rows:
        print(f"  {r['id']} [{r['mode']}]: {r['passed']}/4 pass, ec={r['entity_count_dist']} (want {r['expected_entity_count']}) {'OK' if r['contract_held'] else 'GAP'}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
