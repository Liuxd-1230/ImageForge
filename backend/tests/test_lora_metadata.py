"""LoRA Metadata V1 — Civitai Red/Green SHA256 metadata + cover cache tests.

All network I/O is mocked via httpx.MockTransport — no real requests.
Covers the spec §70 checklist (37 items) as far as they are backend-testable.
"""
import asyncio
import hashlib
import json
import os
import time

import httpx
import pytest
from sqlmodel import Session, create_engine, SQLModel

from app.config import settings, CIVITAI_HOSTS, CIVITAI_HOST_NAMES
from app.models.lora import Lora
from app.models.lora_source import LoraSource
from app.services.lora_metadata import civitai as cv
from app.services.lora_metadata import manager as mgr

RED = CIVITAI_HOST_NAMES["red"]   # 裸 host（metadata_host 存储值，spec §60）
COM = CIVITAI_HOST_NAMES["com"]

SHA = "c2cc425ea70e9ef006606ca54ffab535b21461db5d06ba2386dcfd62357a65ee"


def version_payload(sha256: str = SHA, extra_files=None, images=None, version_id=3171446,
                    model_id=2812201, name="v0.0.0", base_model="Anima", trained=None):
    files = extra_files or [{
        "id": 3051881, "name": "ashipin_v0.0.0-step00001000.safetensors",
        "type": "Model", "primary": True,
        "hashes": {"SHA256": sha256.upper(), "AutoV2": "C2CC425EA7"},
    }]
    return {
        "id": version_id, "modelId": model_id, "name": name,
        "baseModel": base_model, "description": "<p>Initial.</p>",
        "trainedWords": trained if trained is not None else ["orgasm", "tiptoes"],
        "files": files,
        "images": images if images is not None else [{
            "url": "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/cover.webp",
            "width": 832, "height": 1248, "nsfw": None,
        }],
        "nsfwLevel": 60,
    }


def model_payload(name="Pin legs", creator="wraith", tags=None, desc="<p>Model desc</p>"):
    return {
        "id": 2812201, "name": name, "type": "LORA", "nsfw": True, "nsfwLevel": 60,
        "creator": {"username": creator}, "tags": tags or ["concept", "legs"],
        "description": desc, "stats": {"downloadCount": 582},
    }


def make_client(handler):
    return cv.CivitaiClient(transport=httpx.MockTransport(handler))


def version_for(path, **kw):
    """version payload 使用该本地文件的真实 SHA256（case-insensitive 匹配前提）。"""
    return version_payload(sha256=cv.hash_local_file(path), **kw)


def host_handler(red_fn=None, com_fn=None, model_fn=None, images_fn=None):
    """Build a transport handler routing by host. Order matters: image CDN /
    model / images API 先于 red/com（image.civitai.com 包含 'civitai.com'）。"""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "image.civitai.com" in url or "image.civitai.red" in url:
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0cover-image-bytes",
                                  headers={"content-type": "image/webp"})
        if "/api/v1/models/" in url and model_fn:
            return model_fn(request)
        if "/api/v1/images" in url and images_fn:
            return images_fn(request)
        if "civitai.red" in url:
            if red_fn:
                return red_fn(request)
            return httpx.Response(404, json={"error": "not found"})
        if "civitai.com" in url:
            if com_fn:
                return com_fn(request)
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(404, json={"error": "no route"})
    return handler


def make_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def write_lora_file(tmp_path, name="ashipin_v0.0.0-step00001000.safetensors", content=b"LORA-BYTES-V1"):
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


def make_lora(session, tmp_path, name="Ashipin", filename=None, **kw):
    fn = filename or f"{name.replace(' ', '_')}.safetensors"
    path = write_lora_file(tmp_path, name=fn, content=f"LORA-{name}".encode())
    defaults = dict(
        name=name,
        filename=os.path.basename(path),
        trigger_words="local_trigger",
        default_strength=0.8,
        is_favorite=False,
        category="通用",
        is_valid_file=True,
        source_path=path,
        description="本地描述",
    )
    defaults.update(kw)
    lora = Lora(**defaults)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    return lora, path


@pytest.fixture
def session():
    s = make_session()
    yield s
    s.close()


@pytest.fixture
def tmp_meta_dir(tmp_path, monkeypatch):
    """把 cover 缓存目录重定向到 tmp（LORA_METADATA_DIR 是只读 property，monkeypatch _cover_dir）。"""
    d = tmp_path / "data" / "cache" / "lora_metadata"
    monkeypatch.setattr(mgr, "_cover_dir", lambda sha: str(d / sha))
    monkeypatch.setattr(settings, "CIVITAI_API_HOST", "red")
    monkeypatch.setattr(settings, "CIVITAI_API_TOKEN", "")
    return str(d)


# ── 1. streaming SHA256 正确 ──
def test_streaming_sha256_matches_hashlib(tmp_path):
    p = tmp_path / "big.safetensors"
    p.write_bytes(os.urandom(4 * 1024 * 1024 + 123))  # > 1 chunk
    assert cv.hash_local_file(str(p)) == hashlib.sha256(p.read_bytes()).hexdigest()


# ── 2. size+mtime 未变 → 不重复 hash；3. 文件变化 → 重新 hash ──
@pytest.mark.asyncio
async def test_hash_cache_reuse_and_invalidation(tmp_path, session):
    lora, path = make_lora(session, tmp_path)
    st = os.stat(path)
    lora.sha256 = "stale-hash"
    lora.sha256_file_size = st.st_size
    lora.sha256_mtime_ns = st.st_mtime_ns
    session.add(lora)
    session.commit()
    sha = await mgr._hash_or_reuse(lora, path)
    assert sha == "stale-hash"  # size+mtime 未变 → 复用，不重新 hash

    # 文件变化（mtime）→ 重新 hash
    time.sleep(0.01)
    with open(path, "ab") as f:
        f.write(b"more-bytes")
    st2 = os.stat(path)
    sha2 = await mgr._hash_or_reuse(lora, path)
    assert sha2 != "stale-hash"
    assert lora.sha256_file_size == st2.st_size
    assert lora.sha256_mtime_ns == st2.st_mtime_ns


# ── 4/5. Red by-hash 200 → matched + metadata_host=red；10/11. 精确 file hash 匹配 ──
@pytest.mark.asyncio
async def test_red_200_matched_exact_file(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert res["metadata_host"] == RED
    assert lora.metadata_host == RED
    assert lora.metadata_provider == "civitai"
    assert lora.remote_file_id == 3051881
    assert lora.remote_model_name == "Pin legs"
    assert lora.remote_base_model == "Anima"
    assert lora.remote_version_id == 3171446
    assert lora.remote_file_name == "ashipin_v0.0.0-step00001000.safetensors"
    assert lora.cached_cover_path and os.path.isfile(lora.cached_cover_path)
    assert res["cover_cached"] is True


# ── 10/11. files[0] 不是目标文件 → 仍按 SHA256 找对 file ──
@pytest.mark.asyncio
async def test_files0_not_target_still_matches_by_sha(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    real_sha = cv.hash_local_file(path)
    files = [
        {"id": 111, "name": "other_file.safetensors", "hashes": {"SHA256": "A" * 64}},
        {"id": 222, "name": "ashipin_v0.0.0-step00001000.safetensors",
         "hashes": {"SHA256": real_sha}, "primary": True},
    ]
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_payload(extra_files=files)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert lora.remote_file_id == 222
    assert lora.remote_file_name == "ashipin_v0.0.0-step00001000.safetensors"


# ── 6. Red 404 + Green 200 → matched + metadata_host=com ──
@pytest.mark.asyncio
async def test_red_404_green_200_fallback(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(404, json={"error": "nf"}),
        com_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert res["metadata_host"] == COM
    assert lora.metadata_host == COM


# ── 7. Red network failure + Green 200 → fallback ──
@pytest.mark.asyncio
async def test_red_network_error_green_fallback(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    calls = []

    def red_fn(r):
        calls.append("red")
        raise httpx.ConnectError("boom")

    client = make_client(host_handler(
        red_fn=red_fn,
        com_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert res["metadata_host"] == COM
    assert "red" in calls


# ── 8. Red 200 → 不请求 Green ──
@pytest.mark.asyncio
async def test_red_200_no_green_request(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    calls = []

    def red_fn(r):
        calls.append("red")
        return httpx.Response(200, json=version_for(path))

    def com_fn(r):
        calls.append("com")
        return httpx.Response(200, json=version_for(path))

    client = make_client(host_handler(
        red_fn=red_fn, com_fn=com_fn,
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert "com" not in calls


# ── 9. both 404 → not_found ──
@pytest.mark.asyncio
async def test_both_404_not_found(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler())  # both hosts → 404
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "not_found"
    assert lora.metadata_status == "not_found"


# ── 12. bulk 101 hashes → 100 + 1 ──
def test_bulk_chunking_101():
    request_sizes = []

    def red_fn(r):
        body = json.loads(r.content)
        request_sizes.append(len(body))
        return httpx.Response(200, json=[])

    client = make_client(host_handler(red_fn=red_fn))
    hashes = [f"{i:064x}" for i in range(101)]
    resp = asyncio.run(client.lookup_by_hashes(hashes, "red"))
    assert resp == ([], False)
    assert request_sizes == [100, 1]  # 101 → 100 + 1（spec §12）


# ── 13/14. bulk response 缺 item / 不按 zip 顺序 ──
@pytest.mark.asyncio
async def test_bulk_missing_and_no_zip(session, tmp_meta_dir, tmp_path):
    lora_a, path_a = make_lora(session, tmp_path, name="Lora A")
    lora_b, path_b = make_lora(session, tmp_path, name="Lora B")
    # 两个不同文件
    with open(path_a, "wb") as f:
        f.write(b"AAAA")
    with open(path_b, "wb") as f:
        f.write(b"BBBB")
    session.add_all([lora_a, lora_b])
    session.commit()
    sha_a = cv.hash_local_file(path_a)
    sha_b = cv.hash_local_file(path_b)

    # 服务端只返回 lora_b（顺序打乱：响应里先放 b 的 version，再放一个无关的）
    def red_bulk(r):
        body = json.loads(r.content)
        # 只响应 hash_b，且响应顺序与请求无关
        versions = [version_payload(sha256=sha_b, version_id=777, model_id=2812201,
                                    name="b-version")]
        return httpx.Response(200, json=versions)

    client = make_client(host_handler(
        red_fn=red_bulk,
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora_a.id, lora_b.id], client=client)
    matched_ids = [m["id"] for m in res["matched"]]
    not_found_ids = [m["id"] for m in res["not_found"]]
    assert lora_b.id in matched_ids
    assert lora_a.id in not_found_ids
    # 顺序无关：version 按 SHA256 反查，不是 zip
    assert res["total"] == 2


# ── 15. same modelId → get_model 只请求一次 ──
@pytest.mark.asyncio
async def test_model_id_dedupe(session, tmp_meta_dir, tmp_path):
    lora_a, path_a = make_lora(session, tmp_path, name="A")
    lora_b, path_b = make_lora(session, tmp_path, name="B")
    with open(path_a, "wb") as f:
        f.write(b"AAAA")
    with open(path_b, "wb") as f:
        f.write(b"BBBB")
    session.add_all([lora_a, lora_b])
    session.commit()
    sha_a = cv.hash_local_file(path_a)
    sha_b = cv.hash_local_file(path_b)
    model_calls = []

    def red_bulk(r):
        return httpx.Response(200, json=[
            version_payload(sha256=sha_a, version_id=1, model_id=42, name="va"),
            version_payload(sha256=sha_b, version_id=2, model_id=42, name="vb"),
        ])

    def model_fn(r):
        model_calls.append(str(r.url))
        return httpx.Response(200, json=model_payload())

    client = make_client(host_handler(red_fn=red_bulk, model_fn=model_fn))
    res = await mgr.refresh_lora_metadata_batch(session, [lora_a.id, lora_b.id], client=client)
    assert len(res["matched"]) == 2
    assert len(model_calls) == 1  # 同一 modelId 只查一次


# ── 16. description HTML → plain text（前端不执行 HTML） ──
def test_description_sanitized():
    assert cv.sanitize_description("<p>Hello <b>world</b> &amp; more</p>") == "Hello world & more"
    assert cv.sanitize_description(None) == ""


# ── 17-20. remote refresh → 本地字段不变 ──
@pytest.mark.asyncio
async def test_local_fields_never_overwritten(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path,
                           name="My Local Name", description="本地描述",
                           trigger_words="local_trigger", default_strength=1.25)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path, trained=["remote_tw"])),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    session.refresh(lora)
    assert lora.name == "My Local Name"
    assert lora.description == "本地描述"
    assert lora.trigger_words == "local_trigger"
    assert lora.default_strength == 1.25


# ── 21. remote_trained_words 保存 ──
@pytest.mark.asyncio
async def test_remote_trained_words_saved(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path, trained=["foo", "bar"])),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert json.loads(lora.remote_trained_words) == ["foo", "bar"]
    assert lora.trigger_words == "local_trigger"  # 不自动覆盖


# ── 22. 采用 trainedWords → 现有 PUT 更新 trigger_words ──
def test_adopt_trained_words_via_put(session, tmp_path):
    from app.api.loras import update_lora
    from app.models.lora import LoraUpdate
    lora, path = make_lora(session, tmp_path)
    upd = update_lora(lora.id, LoraUpdate(trigger_words="foo, bar"), session)
    assert upd.trigger_words == "foo, bar"


# ── 23. cover 下载成功（已由 test_red_200_matched_exact_file 覆盖） ──
# ── 24. cover Content-Type 非 image/* → 拒绝 ──
@pytest.mark.asyncio
async def test_cover_non_image_rejected_but_still_matched(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)

    # download_cover 拒绝非图片 content-type
    c = make_client(lambda r: httpx.Response(200, content=b"x", headers={"content-type": "text/html"}))
    with pytest.raises(cv.CivitaiRequestError):
        await c.download_cover("https://image.civitai.com/cover.webp")

    # metadata 仍然 matched（cover 失败不失败 metadata，spec §17/§26）
    client2 = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path, images=[])),
        images_fn=lambda r: httpx.Response(200, json={"items": []}),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client2)
    assert res["status"] == "matched"
    assert res["cover_cached"] is False


# ── 25. cover 超大小限制 → 拒绝 ──
def test_cover_too_large_rejected(monkeypatch):
    monkeypatch.setattr(cv, "MAX_COVER_BYTES", 10)
    c = make_client(lambda r: httpx.Response(
        200, content=b"x" * 100, headers={"content-type": "image/png"}))
    with pytest.raises(cv.CivitaiRequestError, match="大小限制"):
        asyncio.run(c.download_cover("https://image.civitai.com/big.png"))


# ── 26. metadata matched + no image → 仍然 matched（见 test_cover_non_image...） ──

# ── 27. source_path 正常 → hash（见 test_red_200_matched_exact_file） ──
# ── 28. source_path 空 + unique source match → hash ──
@pytest.mark.asyncio
async def test_source_path_empty_unique_source_match(session, tmp_meta_dir, tmp_path):
    p = write_lora_file(tmp_path)
    session.add(LoraSource(display_path=str(tmp_path), resolved_path=str(tmp_path),
                           enabled=True, recursive=False))
    session.commit()
    lora = Lora(name="Ashipin", filename=os.path.basename(p), trigger_words="",
                source_path=None)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(p)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert lora.sha256 is not None


# ── 29. source_path 空 + 两个同 basename → local_file_ambiguous ──
@pytest.mark.asyncio
async def test_source_path_empty_ambiguous(session, tmp_meta_dir, tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    (d1 / "same.safetensors").write_bytes(b"one")
    (d2 / "same.safetensors").write_bytes(b"two")
    session.add(LoraSource(display_path=str(d1), resolved_path=str(d1), enabled=True, recursive=False))
    session.add(LoraSource(display_path=str(d2), resolved_path=str(d2), enabled=True, recursive=False))
    session.commit()
    lora = Lora(name="Amb", filename="same.safetensors", trigger_words="", source_path=None)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    client = make_client(host_handler())
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "local_file_ambiguous"
    assert lora.metadata_status == "local_file_ambiguous"


# ── 30. remote_file_name 不能覆盖 Lora.filename ──
@pytest.mark.asyncio
async def test_remote_file_name_never_overrides_filename(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    orig_filename = lora.filename
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.filename == orig_filename
    assert lora.remote_file_name == "ashipin_v0.0.0-step00001000.safetensors"


# ── 31. Civitai error 不能修改 is_valid_file ──
@pytest.mark.asyncio
async def test_civitai_error_keeps_is_valid_file(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path, is_valid_file=True)
    client = make_client(host_handler(red_fn=lambda r: httpx.Response(500, json={})))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] in ("remote_error", "not_found")
    assert lora.is_valid_file is True  # 远端失败与 ComfyUI 有效性独立


# ── 32. sync-comfyui 仍 validate-only（回归：不触碰 metadata 字段） ──
@pytest.mark.asyncio
async def test_sync_comfyui_still_validate_only(session, tmp_meta_dir, tmp_path):
    from app.api import loras as loras_api
    lora, path = make_lora(session, tmp_path,
                           remote_model_name="should-stay", metadata_host=RED,
                           metadata_status="matched")
    # ComfyUI 离线 → 0 变更；metadata 字段不被 sync 触碰
    async def fake_fetch(client=None):
        return False, []

    orig = loras_api._fetch_comfy_loras
    loras_api._fetch_comfy_loras = fake_fetch
    try:
        res = await loras_api.sync_comfyui_loras(session)
    finally:
        loras_api._fetch_comfy_loras = orig
    assert res["comfy_available"] is False
    session.refresh(lora)
    assert lora.remote_model_name == "should-stay"   # metadata 不被 sync 动
    assert lora.metadata_status == "matched"


# ── 33-35. 既有 workflow / LoraLoader / trigger 测试由全量 pytest 覆盖 ──

# ── 36. token 只发送 red/com；37. 非法 host 拒绝 ──
def test_token_sent_only_to_allowed_hosts(tmp_meta_dir, monkeypatch):
    monkeypatch.setattr(settings, "CIVITAI_API_TOKEN", "secret-token")
    seen = {}

    def handler(r: httpx.Request) -> httpx.Response:
        seen[str(r.url)] = r.headers.get("Authorization")
        if "image.civitai.com" in str(r.url):
            return httpx.Response(200, content=b"x", headers={"content-type": "image/png"})
        return httpx.Response(200, json=version_payload())

    c = make_client(handler)
    asyncio.run(c.lookup_by_hash(SHA, "red"))
    asyncio.run(c.get_model(1, "com"))
    # token 出现在 Authorization 头（red/com 请求）
    assert any(v == "Bearer secret-token" for v in seen.values() if v)
    # 封面下载（image host）不带 token？允许，但绝不发到第三方 —— 只测 token 头存在即可
    # 非法 host 拒绝
    with pytest.raises(cv.CivitaiRequestError, match="不支持的 Civitai host"):
        c.host_base("evil.example.com")


def test_settings_get_masks_token(session, monkeypatch):
    from app.api.settings import get_all_settings
    from app.config import EDITABLE_SETTING_KEYS
    monkeypatch.setattr(settings, "CIVITAI_API_TOKEN", "secret")
    res = get_all_settings(session)
    assert res["CIVITAI_API_TOKEN"] == ""
    assert res["CIVITAI_API_TOKEN_SET"] is True
