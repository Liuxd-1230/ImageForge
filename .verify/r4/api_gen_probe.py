"""Validate ImageForge /api/comfyui/* monitor chain with a real small generation."""
import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def post(path, body):
    req = urllib.request.Request(BASE + path, method="POST", data=json.dumps(body).encode())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    # small real generation through the ImageForge backend
    st, res = post("/api/comfyui/generate", {
        "positive_prompt": "1girl, blue hair, portrait, masterpiece",
        "negative_prompt": "bad anatomy, text",
        "unet_name": "anima29B_v10.safetensors",
        "clip_name": "qwen_3_06b_base.safetensors",
        "vae_name": "qwen_image_vae.safetensors",
        "loras": [],
        "width": 256, "height": 256, "steps": 8, "cfg": 4.5,
        "sampler_name": "euler", "scheduler": "sgm_uniform", "seed": 777001,
    })
    print("generate:", st, str(res)[:200])
    if st != 200:
        print("FAIL", res)
        return
    pid = res.get("prompt_id")
    # poll status like the frontend does
    transitions = []
    last = None
    for i in range(60):
        sts = get(f"/api/comfyui/status/{pid}")
        key = (sts["stage"], sts["progress_value"], sts["progress_max"], sts["queue_position"])
        if key != last:
            transitions.append(key)
            last = key
            print(f"  [{i}] stage={sts['stage']} progress={sts['progress_value']}/{sts['progress_max']} pos={sts['queue_position']} running={sts['is_running']}")
        if sts["stage"] in ("done", "error", "cancelled"):
            break
        time.sleep(1)
    hist = get(f"/api/comfyui/history/{pid}")
    h = hist.get(pid, {})
    print("history status:", json.dumps(h.get("status", {}))[:200])
    imgs = []
    for nid, out in (h.get("outputs") or {}).items():
        imgs.extend(out.get("images", []))
    print("images:", json.dumps(imgs, ensure_ascii=False)[:200])
    # bad model → categorized error
    st, err = post("/api/comfyui/generate", {
        "positive_prompt": "x", "negative_prompt": "y",
        "unet_name": "nope.safetensors", "clip_name": "qwen_3_06b_base.safetensors",
        "vae_name": "qwen_image_vae.safetensors", "loras": [],
        "width": 64, "height": 64, "steps": 1, "cfg": 4.5,
        "sampler_name": "euler", "scheduler": "sgm_uniform", "seed": 1,
    })
    print("bad-model generate:", st, "summary:", err.get("detail", {}).get("summary") if isinstance(err.get("detail"), dict) else str(err)[:200])


if __name__ == "__main__":
    main()
