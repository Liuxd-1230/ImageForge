"""Backend API tests: LoRA source management, migrations, security, edge cases."""
import os
import sys
import shutil
import json
import tempfile
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
FIXTURE = os.path.join(os.path.dirname(__file__), "testsrc")
FIXTURE2 = os.path.join(os.path.dirname(__file__), "testsrc2")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def make_fixture():
    for d in (FIXTURE, FIXTURE2):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    for rel in [
        "Anima/foo_style_v1.safetensors",
        "bar_boost.safetensors",
        "baz_detail.ckpt",
        "deep/nested/thing.pt",
        "not_a_lora.txt",
        "Anima/dup_name.safetensors",
        "dup_name.safetensors",
    ]:
        p = os.path.join(FIXTURE, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\x00fake-lora")
    # second source with a same-basename file (cross-source conflict case)
    with open(os.path.join(FIXTURE2, "dup_name.safetensors"), "wb") as f:
        f.write(b"\x00fake-lora-2")


def clean():
    for d in (FIXTURE, FIXTURE2):
        if os.path.exists(d):
            shutil.rmtree(d)
    srcs = api("GET", "/api/loras/sources")[1]
    for s in srcs:
        api("DELETE", f"/api/loras/sources/{s['id']}")
    loras = api("GET", "/api/loras")[1]
    for l in loras:
        if (l.get("source_path") or "").startswith(os.path.dirname(FIXTURE)):
            api("DELETE", f"/api/loras/{l['id']}")


def main():
    results = []
    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print(("PASS" if cond else "FAIL"), name, detail)

    clean()
    make_fixture()

    # ── 1. 旧 DB 迁移修复 ──
    st, body = api("POST", "/api/loras", {
        "name": "Migration Test Lora", "filename": "migration_test_lora.safetensors",
        "trigger_words": "mt", "default_strength": 0.8, "category": "测试",
    })
    check("POST /api/loras (old-DB NOT NULL fix)", st == 200, str(body)[:100])
    if st == 200:
        api("DELETE", f"/api/loras/{body['id']}")

    # ── 2. fresh DB 首次启动（审计 P0） ──
    from app.database import _migrate_legacy_sqlite
    from sqlmodel import SQLModel, create_engine, Session
    from app.models.lora import Lora
    fresh_dir = tempfile.mkdtemp()
    fresh_db = os.path.join(fresh_dir, "fresh.db")
    fresh_url = f"sqlite:///{fresh_db}"
    try:
        _migrate_legacy_sqlite(fresh_url)  # 表不存在时必须无操作、不崩溃
        fresh_engine = create_engine(fresh_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as s:
            l = Lora(name="Fresh", filename="fresh_ok.safetensors")
            s.add(l)
            s.commit()
            s.refresh(l)
        import sqlite3
        c = sqlite3.connect(fresh_db)
        cols = {r[1]: r[3] for r in c.execute("PRAGMA table_info(loras)")}
        c.close()
        check("fresh DB 首次启动不崩溃且可写入", True)
        check("fresh DB loras.source_path 存在", "source_path" in cols)
        check("fresh DB loras.is_enabled nullable", cols.get("is_enabled") == 0)
    except Exception as e:
        check("fresh DB 首次启动不崩溃且可写入", False, str(e))
    finally:
        shutil.rmtree(fresh_dir, ignore_errors=True)

    # ── 3. WSL 路径转译 ──
    from app.services.pathutils import windows_to_wsl, normalize_separators, safe_relative, join_within_root
    check("WSL D:\\\\ conversion", windows_to_wsl(r"D:\ComfyUI\models\loras\Anima") == "/mnt/d/ComfyUI/models/loras/Anima")
    check("WSL D:/ conversion", windows_to_wsl("D:/Models/LoRA") == "/mnt/d/Models/LoRA")
    check("non-drive untouched", windows_to_wsl("/home/me/models") is None)
    check("normalize separators", normalize_separators(r"a\b\c") == "a/b/c")
    # 安全相对路径（审计：恶意/越界路径）
    check("safe_relative rejects ..", safe_relative("../evil.safetensors") is None)
    check("safe_relative rejects abs", safe_relative("/etc/passwd") is None)
    check("safe_relative rejects drive", safe_relative("D:/evil/x.safetensors") is None)
    check("safe_relative accepts nested", safe_relative("a/b/c.safetensors") == "a/b/c.safetensors")
    check("join_within_root ok", join_within_root(FIXTURE, "bar_boost.safetensors") == os.path.join(FIXTURE, "bar_boost.safetensors"))
    check("join_within_root blocks escape", join_within_root(FIXTURE, "../testsrc2/dup_name.safetensors") is None)

    # ── 4. resolve-path 预览 API（审计：UI 不得自己猜 /mnt） ──
    st, rp = api("POST", "/api/loras/resolve-path", {"display_path": FIXTURE})
    check("resolve-path returns resolved", st == 200 and rp.get("resolved_path") == FIXTURE, str(rp)[:160])
    check("resolve-path counts lora files", rp.get("lora_file_count") == 6, str(rp.get("lora_file_count")))
    st, rp2 = api("POST", "/api/loras/resolve-path", {"display_path": "/no/such/path"})
    check("resolve-path missing path ok", st == 200 and rp2.get("exists") is False)

    # ── 5. 来源 CRUD ──
    st, body = api("POST", "/api/loras/sources", {"display_path": FIXTURE, "recursive": True})
    check("add source", st == 201, str(body)[:120])
    src_id = body.get("id")
    st, _ = api("POST", "/api/loras/sources", {"display_path": FIXTURE + "/", "recursive": True})
    check("duplicate source rejected", st == 409)
    st, _ = api("POST", "/api/loras/sources", {"display_path": "/no/such/dir", "recursive": True})
    check("nonexistent path rejected", st == 400)

    # ── 6. 扫描 + ComfyUI 离线检测（审计 P1） ──
    st, scan = api("POST", f"/api/loras/sources/{src_id}/scan")
    check("scan ok", st == 200)
    if st == 200:
        s = scan["summary"]
        check("scan total", s["total"] == 6, str(s))
        check("scan conflict detected", s["basename_conflicts"] >= 2, str(s))
        cands = scan["candidates"]
        check("candidate fields present", all(
            "relative_path" in c and "comfy_recognized" in c and "exists_in_db" in c and "full_path" in c
            for c in cands))

        # ── 7. 导入：服务端权威重验 + 同批同 filename 只写一次（审计 P0/P1） ──
        new_rel = [c["relative_path"] for c in cands if not c["exists_in_db"]][:2]
        before = len(api("GET", "/api/loras")[1])
        st, imp = api("POST", "/api/loras/import", {"source_id": src_id, "relative_paths": new_rel})
        check("import ok", st == 200, str(imp)[:200])
        check("import added exactly selected", len(imp.get("imported", [])) == len(new_rel), str(imp)[:150])
        after = len(api("GET", "/api/loras")[1])
        check("db count matches", after == before + len(new_rel))
        # 同批重复提交同一 filename：第二次应被跳过（循环内去重）
        st, imp2 = api("POST", "/api/loras/import", {"source_id": src_id, "relative_paths": new_rel + new_rel})
        check("same-batch duplicate skipped", st == 200 and len(imp2.get("imported", [])) == 0 and len(imp2.get("skipped", [])) >= 1, str(imp2)[:200])
        # 恶意/过期路径
        st, imp3 = api("POST", "/api/loras/import", {"source_id": src_id, "relative_paths": ["../testsrc2/dup_name.safetensors", "/etc/passwd", "not_a_lora.txt"]})
        check("malicious paths rejected", st == 200 and len(imp3.get("errors", [])) == 3, str(imp3)[:250])
        # 已删除文件（stale）
        gone = os.path.join(FIXTURE, "gone.safetensors")
        with open(gone, "wb") as f:
            f.write(b"x")
        os.remove(gone)
        st, imp4 = api("POST", "/api/loras/import", {"source_id": src_id, "relative_paths": ["gone.safetensors"]})
        check("stale path rejected", len(imp4.get("errors", [])) == 1 and "已移动" in imp4["errors"][0]["reason"], str(imp4)[:200])

    # ── 8. 跨来源同 basename：冲突与识别判定（审计 P0/P1） ──
    from app.api.loras import _match_comfy, _comfy_basenames
    comfy = ["dir1/foo.safetensors"]
    bn = _comfy_basenames(comfy)
    check("exact comfy match", _match_comfy("dir1/foo.safetensors", "foo.safetensors", comfy, bn, ambiguous=False) == "dir1/foo.safetensors")
    check("ambiguous same-basename NOT recognized", _match_comfy("dir2/foo.safetensors", "foo.safetensors", comfy, bn, ambiguous=True) is None)
    check("unambiguous basename fallback ok", _match_comfy("dir2/foo.safetensors", "foo.safetensors", comfy, bn, ambiguous=False) == "dir1/foo.safetensors")
    # 第二来源与第一来源同名文件（跨来源冲突）
    st, body2 = api("POST", "/api/loras/sources", {"display_path": FIXTURE2, "recursive": True})
    check("second source added", st == 201)
    src2 = body2.get("id")
    st, scan2 = api("POST", f"/api/loras/sources/{src2}/scan")
    if st == 200:
        dup = [c for c in scan2["candidates"] if c["basename"] == "dup_name.safetensors"]
        check("second-source dup flagged conflict", len(dup) == 1 and dup[0]["basename_conflict"] is True, str(dup)[:200])
        api("DELETE", f"/api/loras/sources/{src2}")

    # ── 8b. ComfyUI 离线检测（显式 health check，不依赖 get_loras 吞异常） ──
    import asyncio
    from app.api.loras import _fetch_comfy_loras
    from app.services.comfyui.client import ComfyUIClient
    dead_client = ComfyUIClient(base_url="http://127.0.0.1:59999")
    ok_offline, names_offline = asyncio.run(_fetch_comfy_loras(dead_client))
    check("offline detected via health check", ok_offline is False and names_offline == [])
    ok_live, names_live = asyncio.run(_fetch_comfy_loras())
    check("live comfy detected", ok_live is True and isinstance(names_live, list))

    # ── 9. 删除来源不删库记录 ──
    cnt = len(api("GET", "/api/loras")[1])
    api("DELETE", f"/api/loras/sources/{src_id}")
    check("library records kept after source delete", len(api("GET", "/api/loras")[1]) == cnt)

    # ── 10. sync-comfyui 仅校验不导入 ──
    cnt = len(api("GET", "/api/loras")[1])
    st, body9 = api("POST", "/api/loras/sync-comfyui")
    check("sync-comfyui ok", st == 200, str(body9)[:160])
    check("sync-comfyui no new records", len(api("GET", "/api/loras")[1]) == cnt)

    # ── 11. settings 类型解析（审计 P2：数字字符串不无差别转 int） ──
    st, stg = api("GET", "/api/settings")
    if st == 200:
        check("timeout parsed as int", isinstance(stg.get("GENERATE_TIMEOUT_SECONDS"), int))
        check("base url stays string", isinstance(stg.get("COMFYUI_BASE_URL"), str))

    clean()
    failed = [r for r in results if not r[1]]
    print(f"\n=== {len(results) - len(failed)}/{len(results)} passed ===")
    if failed:
        print("FAILED:", [r[0] for r in failed])
        sys.exit(1)


if __name__ == "__main__":
    main()
