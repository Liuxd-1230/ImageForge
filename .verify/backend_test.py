"""Backend API end-to-end tests for LoRA source management + migrations."""
import os
import sys
import shutil
import json
import urllib.request

BASE = "http://127.0.0.1:8000"
FIXTURE = os.path.join(os.path.dirname(__file__), "testsrc")


def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print(("PASS" if cond else "FAIL"), name, detail)

    # ---- fixture dir ----
    if os.path.exists(FIXTURE):
        shutil.rmtree(FIXTURE)
    os.makedirs(os.path.join(FIXTURE, "Anima"))
    os.makedirs(os.path.join(FIXTURE, "deep", "nested"))
    os.makedirs(os.path.join(FIXTURE, "empty_sub"))
    for rel in [
        "Anima/foo_style_v1.safetensors",
        "bar_boost.safetensors",
        "baz_detail.ckpt",
        "deep/nested/thing.pt",
        "not_a_lora.txt",
        "Anima/dup_name.safetensors",
        "dup_name.safetensors",  # same basename as Anima/dup_name -> conflict
    ]:
        p = os.path.join(FIXTURE, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\x00fake-lora")

    # ---- 1. POST /api/loras works now (migration fixed) ----
    st, body = api("POST", "/api/loras", {
        "name": "Migration Test Lora", "filename": "migration_test_lora.safetensors",
        "trigger_words": "mt", "default_strength": 0.8, "category": "测试",
    })
    check("POST /api/loras (old-DB NOT NULL fix)", st == 200, str(body))
    if st == 200:
        api("DELETE", f"/api/loras/{body['id']}")

    # ---- 2. WSL path conversion unit ----
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    from app.services.pathutils import windows_to_wsl, normalize_separators
    check("WSL D:\\\\ conversion", windows_to_wsl(r"D:\ComfyUI\models\loras\Anima") == "/mnt/d/ComfyUI/models/loras/Anima")
    check("WSL D:/ conversion", windows_to_wsl("D:/Models/LoRA") == "/mnt/d/Models/LoRA")
    check("WSL lowercase", windows_to_wsl(r"C:\x") == "/mnt/c/x")
    check("non-drive untouched", windows_to_wsl("/home/me/models") is None)
    check("normalize separators", normalize_separators(r"a\b\c") == "a/b/c")

    # ---- 3. sources CRUD ----
    st, body = api("POST", "/api/loras/sources", {"display_path": FIXTURE, "recursive": True})
    check("add source", st == 201, str(body)[:200])
    src_id = body.get("id") if st == 201 else None
    if src_id:
        check("source resolved+exists", body.get("exists") is True and body.get("is_dir") is True)
        # dedup: same path again -> 409
        st2, b2 = api("POST", "/api/loras/sources", {"display_path": FIXTURE + "/", "recursive": True})
        check("duplicate source rejected", st2 == 409, str(b2)[:120])
        # non-existent path -> 400
        st3, b3 = api("POST", "/api/loras/sources", {"display_path": "/no/such/dir/xyz", "recursive": True})
        check("nonexistent path rejected", st3 == 400, str(b3)[:120])
        # file-not-dir -> 400
        st4, _ = api("POST", "/api/loras/sources", {"display_path": __file__, "recursive": False})
        check("file-as-source rejected", st4 == 400)

        # ---- 4. scan preview (must NOT modify DB) ----
        before = len(api("GET", "/api/loras")[1])
        st5, scan = api("POST", f"/api/loras/sources/{src_id}/scan")
        check("scan ok", st5 == 200, str(scan)[:300])
        if st5 == 200:
            s = scan["summary"]
            check("scan counts total", s["total"] == 6, str(s))
            check("scan conflict detected", s["basename_conflicts"] >= 2, str(s))
            check("scan no db change", len(api("GET", "/api/loras")[1]) == before)
            cands = scan["candidates"]
            check("candidate has fields", all(
                "relative_path" in c and "comfy_recognized" in c and "exists_in_db" in c and "full_path" in c
                for c in cands))

            # ---- 5. import selected (only 2 chosen) ----
            sel = [c for c in cands if not c["exists_in_db"]][:2]
            st6, imp = api("POST", "/api/loras/import", {"items": sel})
            check("import ok", st6 == 200, str(imp)[:300])
            after = len(api("GET", "/api/loras")[1])
            check("import added exactly selected", after == before + len(sel), f"{before}->{after}")
            # import again -> skipped (idempotent)
            st7, imp2 = api("POST", "/api/loras/import", {"items": sel})
            check("re-import skipped", st7 == 200 and len(imp2.get("skipped", [])) == len(sel), str(imp2)[:200])
            # source_path recorded
            db = api("GET", "/api/loras")[1]
            imported = [r for r in db if r.get("source_path")]
            check("source_path recorded", len(imported) >= len(sel), str(imported[:1]))

        # ---- 6. delete source does NOT delete library records ----
        cnt_before_del = len(api("GET", "/api/loras")[1])
        st8, _ = api("DELETE", f"/api/loras/sources/{src_id}")
        check("delete source", st8 == 200)
        check("library records kept", len(api("GET", "/api/loras")[1]) == cnt_before_del)

    # ---- 7. sync-comfyui is validate-only (no import) ----
    cnt = len(api("GET", "/api/loras")[1])
    st9, body9 = api("POST", "/api/loras/sync-comfyui")
    check("sync-comfyui ok (comfy down)", st9 == 200, str(body9)[:200])
    check("sync-comfyui no new records", len(api("GET", "/api/loras")[1]) == cnt)

    # ---- cleanup test loras imported ----
    for r in api("GET", "/api/loras")[1]:
        if (r.get("source_path") or "").startswith(FIXTURE):
            api("DELETE", f"/api/loras/{r['id']}")

    failed = [r for r in results if not r[1]]
    print(f"\n=== {len(results) - len(failed)}/{len(results)} passed ===")
    if failed:
        print("FAILED:", [r[0] for r in failed])
        sys.exit(1)


if __name__ == "__main__":
    main()
