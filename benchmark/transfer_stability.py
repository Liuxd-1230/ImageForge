#!/usr/bin/env python3
"""Candidate D6 — completed-vs-progressive transfer extraction stability.

对带 d_contract 的案例各跑 N 次完整 pipeline，统计：
  completed:    接收方 final visual state 被抽取的 x/N
  in_progress/unconfirmed: 接收方 final visual state 被错误脑补的 x/N

检测用确定性规则（接收方是否出现 wearing/holding/catching/with + 物体）。
输出 JSON/MD。
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_benchmark import load_cases, setup_db, run_case, entity_text  # noqa: E402
from app.services.llm.lm_studio import LMStudioProvider  # noqa: E402
from app.services.prompt_engine.pipeline import PromptPipeline  # noqa: E402
from sqlmodel import Session  # noqa: E402

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = "qwen3.6-35b-a3b-uncensored-genesis-hermes-v6"
REASONING = "off"
POSSESS_VERBS = ("wearing", "wear", "holding", "hold", "carrying", "carry", "catching", "catch", "with")


def recipient_has_final_state(rec, recipient, obj) -> bool:
    ff = rec.get("stages", {}).get("3_final_facts", {})
    for e in ff.get("entities", []):
        if e["name"] != recipient:
            continue
        for s in ff.get("statements", []):
            if s.get("subject") != e.get("id"):
                continue
            text = (s.get("text") or "").lower()
            if any(v in text for v in POSSESS_VERBS) and obj.lower() in text:
                return True
    return False


async def main():
    cases = [c for c in load_cases() if c.get("d_contract")]
    engine = setup_db()
    llm = LMStudioProvider(base_url="http://127.0.0.1:1234", api_key="")
    with Session(engine) as session:
        pipeline = PromptPipeline(session=session, llm_provider=llm)
        rows = []
        for case in cases:
            dc = case["d_contract"]
            hits = 0
            recs = []
            for i in range(4):
                print(f"[{case['id']}] run {i+1}/4 ...", flush=True)
                rec = await run_case(pipeline, case)
                recs.append(rec)
                if recipient_has_final_state(rec, dc["recipient"], dc["object"]):
                    hits += 1
            rows.append({
                "id": case["id"], "mode": dc["mode"], "recipient": dc["recipient"],
                "object": dc["object"], "input": case["input"],
                "final_state_present": hits,
                "runs": 4,
                "final_prompts": [r.get("final_prompt", "") for r in recs],
            })

    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(BENCH_DIR, "results", f"transfer_stability_{ts}.json")
    md_path = os.path.join(BENCH_DIR, "results", f"transfer_stability_{ts}.md")

    lines = ["# Candidate D6 — Completed vs Progressive Transfer Extraction Stability", "",
             f"- 时间：{ts}｜每例 4 次全量 pipeline", ""]
    summary = []
    for r in rows:
        ok = (r["mode"] == "completed" and r["final_state_present"] == 4) or \
             (r["mode"] in ("in_progress", "unconfirmed") and r["final_state_present"] == 0)
        summary.append({"id": r["id"], "mode": r["mode"], "object": r["object"],
                        "final_state_present": f"{r['final_state_present']}/4", "contract_held": ok})
        lines.append(f"### {r['id']}（{r['mode']} / {r['object']}）")
        lines.append(f"- 输入：{r['input']}")
        lines.append(f"- 接收方 final state 出现：{r['final_state_present']}/4"
                     f"（{'✓ contract' if ok else '✗ contract 未达成'}）")
        lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "rows": rows, "summary": summary}, f, ensure_ascii=False, indent=2)

    print(f"\n===== transfer stability =====")
    for s in summary:
        print(f"  {s['id']} [{s['mode']}/{s['object']}]: final={s['final_state_present']} {'OK' if s['contract_held'] else 'GAP'}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
