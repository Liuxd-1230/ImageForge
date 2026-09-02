"""ComfyUI 0.34.2 probe v3 — handles submit failures, forces non-cached runs.
Answers:
  1. progress WS messages on a real (non-cached) run: {value, max, prompt_id, node}
  2. queue structure while running (arrays [number, prompt_id, inputs])
  3. submit-time 400 body for a missing model (A8 categorization)
  4. DELETE /queue/{prompt_id} task-scoped cancel
  5. POST /interrupt global semantics + history status_str
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))

import httpx
import websockets

BASE = "http://127.0.0.1:8188"
WS = "ws://127.0.0.1:8188/ws"


def build_tiny(steps: int, seed: int, size: int = 64, unet: str = "anima29B_v10.safetensors"):
    from app.services.comfyui.workflow import build_anima_29b_workflow
    return build_anima_29b_workflow(
        positive_prompt=f"probe seed {seed}, 1girl, blue hair",
        negative_prompt="bad anatomy, text",
        unet_name=unet,
        clip_name="qwen_3_06b_base.safetensors",
        vae_name="qwen_image_vae.safetensors",
        loras=[],
        width=size, height=size, batch_size=1, steps=steps, cfg=4.5,
        sampler_name="euler", scheduler="sgm_uniform", seed=seed,
    )


async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        # ── 1. real non-cached run: progress + queue structure ──
        print("=== 1) real (non-cached) run ===")
        wf = build_tiny(steps=8, seed=191919, size=192)  # unique seed -> not cached
        async with websockets.connect(f"{WS}?clientId=probeA") as ws:
            r = await c.post(f"{BASE}/prompt", json={"prompt": wf, "client_id": "probeA"})
            body = r.json()
            pid = body.get("prompt_id")
            print("  submit:", r.status_code, "prompt_id:", pid)
            # poll queue a few times while running
            for i in range(10):
                q = (await c.get(f"{BASE}/queue")).json()
                run = q.get("queue_running", [])
                pend = q.get("queue_pending", [])
                print(f"  queue[{i}]: running={json.dumps(run)[:220]} pending={len(pend)}")
                if not run and not pend:
                    break
                await asyncio.sleep(1)
            progs = []
            execs = []
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=90)
                except asyncio.TimeoutError:
                    print("  (ws timeout)")
                    break
                m = json.loads(msg)
                t = m.get("type")
                if t == "progress":
                    progs.append(m["data"])
                    if len(progs) <= 4:
                        print("  progress:", json.dumps(m["data"]))
                elif t == "executing" and (m.get("data") or {}).get("node") is not None:
                    execs.append(m["data"])
                elif t in ("execution_success", "execution_error", "execution_interrupted"):
                    print("  terminal:", t, json.dumps(m.get("data"))[:160])
                    break
            print("  total progress msgs:", len(progs), "| executing nodes:", json.dumps(execs[:6]))
            if progs:
                print("  progress shape sample:", json.dumps(progs[0]))
            hist = (await c.get(f"{BASE}/history/{pid}")).json().get(pid, {}) if pid else {}
            print("  history status:", json.dumps(hist.get("status", {}))[:250])

        # ── 2. submit-time 400 for missing model (A8) ──
        print("=== 2) missing model -> submit 400 body ===")
        bad = build_tiny(steps=1, seed=1, unet="does_not_exist.safetensors")
        r = await c.post(f"{BASE}/prompt", json={"prompt": bad, "client_id": "probeB"})
        print("  status:", r.status_code)
        print("  body:", r.text[:500])

        # ── 3. task-scoped cancel: DELETE /queue/{prompt_id} ──
        print("=== 3) DELETE /queue/{prompt_id} ===")
        wf2 = build_tiny(steps=2, seed=202020, size=64)
        r2 = await c.post(f"{BASE}/prompt", json={"prompt": wf2, "client_id": "probeC"})
        pid2 = r2.json().get("prompt_id")
        print("  submitted:", pid2)
        d2 = await c.delete(f"{BASE}/queue/{pid2}")
        print("  DELETE ->", d2.status_code, d2.text[:120])
        q = (await c.get(f"{BASE}/queue")).json()
        print("  queue after:", json.dumps({"running": q["queue_running"], "pending": q["queue_pending"]})[:300])

        # ── 4. global interrupt on a real run ──
        print("=== 4) POST /interrupt ===")
        wf3 = build_tiny(steps=30, seed=333333, size=256)  # long enough to interrupt
        async with websockets.connect(f"{WS}?clientId=probeD") as ws:
            r3 = await c.post(f"{BASE}/prompt", json={"prompt": wf3, "client_id": "probeD"})
            pid3 = r3.json().get("prompt_id")
            print("  submitted:", pid3)
            saw_progress = False
            async def drain():
                nonlocal saw_progress
                while True:
                    try:
                        m = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                    except asyncio.TimeoutError:
                        return None
                    if m.get("type") == "progress":
                        saw_progress = True
                    if m.get("type") in ("execution_success", "execution_error", "execution_interrupted"):
                        return m
            task = asyncio.ensure_future(drain())
            await asyncio.sleep(4)  # let it start (model already warm from step 1)
            ir = await c.post(f"{BASE}/interrupt")
            print("  POST /interrupt ->", ir.status_code)
            term = await asyncio.wait_for(task, timeout=30)
            print("  terminal msg:", json.dumps(term)[:300] if term else "(none)")
            print("  saw progress before interrupt:", saw_progress)
            h3 = (await c.get(f"{BASE}/history/{pid3}")).json().get(pid3, {})
            print("  history status after interrupt:", json.dumps(h3.get("status", {}))[:400])


if __name__ == "__main__":
    asyncio.run(main())
