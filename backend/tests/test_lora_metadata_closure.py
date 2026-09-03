"""LoRA Metadata V1 Final Closure — Usage Tips enrichment + Batch closure tests.

§37 Metadata Richness（Tier-2 tRPC modelVersion.getById → Usage Tips /
   model vs version description 拆分 / local-first 不覆盖）
§38 Batch Closure（partial response 跨 host / 同 SHA 多记录 /
   error 不落入 not_found / 本地文件状态持久化）

All network I/O is mocked via httpx.MockTransport — no real requests.
"""
import json
import os

import httpx
import pytest
from sqlmodel import Session, create_engine, SQLModel

from app.config import settings, CIVITAI_HOST_NAMES
from app.models.lora import Lora
from app.models.lora_source import LoraSource
from app.services.lora_metadata import civitai as cv
from app.services.lora_metadata import manager as mgr

RED = CIVITAI_HOST_NAMES["red"]
COM = CIVITAI_HOST_NAMES["com"]

SHA = "c2cc425ea70e9ef006606ca54ffab535b21461db5d06ba2386dcfd62357a65ee"


def version_payload(sha256: str = SHA, version_id=3171446, model_id=2812201,
                    name="v0.0.0", base_model="Anima", trained=None,
                    desc="<p>Initial.</p>", images=None):
    return {
        "id": version_id, "modelId": model_id, "name": name,
        "baseModel": base_model, "description": desc,
        "trainedWords": trained if trained is not None else ["orgasm", "tiptoes"],
        "files": [{
            "id": 3051881, "name": "ashipin_v0.0.0-step00001000.safetensors",
            "type": "Model", "primary": True,
            "hashes": {"SHA256": sha256.upper(), "AutoV2": "C2CC425EA7"},
        }],
        "images": images if images is not None else [{
            "url": "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/cover.webp",
            "width": 832, "height": 1248,
        }],
        "nsfwLevel": 60,
    }


def model_payload(name="Pin legs 足ピン", creator="wraith", tags=None,
                  desc="<p>Model intro paragraph one.</p><p>Second paragraph &amp; more.</p>"):
    return {
        "id": 2812201, "name": name, "type": "LORA", "nsfw": True, "nsfwLevel": 60,
        "creator": {"username": creator}, "tags": tags or ["concept", "legs"],
        "description": desc, "stats": {"downloadCount": 582},
    }


def detail_payload(version_id=3171446, settings_obj={"strength": 1}, clip_skip=None,
                   steps=1000, epochs=10, trained=None, desc="<p>Initial.</p>"):
    """tRPC modelVersion.getById 真实响应形状（2026-09 smoke 实测）。"""
    return {"result": {"data": {"json": {
        "id": version_id, "name": "v0.0.0", "description": desc,
        "baseModel": "Anima", "baseModelType": "Standard",
        "trainedWords": trained if trained is not None else [
            "orgasm", "leaning back", "against wall", "on chair",
            "on bed", "lying, on back", "plantar flexion", "tiptoes"],
        "epochs": epochs, "steps": steps, "clipSkip": clip_skip,
        "status": "Published",
        "settings": settings_obj,
        "model": {"id": 2812201, "name": "Pin legs 足ピン", "type": "LORA"},
        "files": None,
    }}}}


def make_client(handler):
    return cv.CivitaiClient(transport=httpx.MockTransport(handler))


def host_handler(red_fn=None, com_fn=None, model_fn=None, images_fn=None, detail_fn=None):
    """Route by host/path. tRPC 默认 401（enrichment fail-open 路径）。"""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "image.civitai.com" in url or "image.civitai.red" in url:
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0cover-image-bytes",
                                  headers={"content-type": "image/webp"})
        if "/api/trpc/" in url:
            if detail_fn:
                return detail_fn(request)
            return httpx.Response(401, json={"error": {"json": {"message": "UNAUTHORIZED"}}})
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


def version_for(path, **kw):
    return version_payload(sha256=cv.hash_local_file(path), **kw)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def write_lora_file(tmp_path, name="ashipin_v0.0.0-step00001000.safetensors", content=b"LORA-BYTES-V1"):
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


def make_lora(session, tmp_path, name="Ashipin", content=None, **kw):
    fn = f"{name.replace(' ', '_')}.safetensors"
    path = write_lora_file(tmp_path, name=fn, content=content or f"LORA-{name}".encode())
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
    d = tmp_path / "data" / "cache" / "lora_metadata"
    monkeypatch.setattr(mgr, "_cover_dir", lambda sha: str(d / sha))
    monkeypatch.setattr(settings, "CIVITAI_API_HOST", "red")
    monkeypatch.setattr(settings, "CIVITAI_API_TOKEN", "")
    return str(d)


def ok_detail_fn(r):
    return httpx.Response(200, json=detail_payload())


# ═══════════════════════ §37 Metadata Richness ═══════════════════════

# ── 1. settings.strength=1 → remote_recommended_strength == 1 ──
@pytest.mark.asyncio
async def test_strength_from_settings(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=ok_detail_fn,
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert res["usage_enrichment"] == "ok"
    assert lora.remote_recommended_strength == 1.0
    assert lora.remote_steps == 1000
    assert lora.remote_epochs == 10


# ── 2. clipSkip=2 → remote_clip_skip == 2 ──
@pytest.mark.asyncio
async def test_clip_skip_saved(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(clip_skip=2)),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.remote_clip_skip == 2


# ── 3. settings=null → 不报错，strength None ──
@pytest.mark.asyncio
async def test_settings_null_no_crash(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(settings_obj=None)),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert lora.remote_recommended_strength is None


# ── 4. settings={} → strength None；奇怪 payload 不 500 ──
@pytest.mark.asyncio
async def test_settings_empty_and_weird(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(settings_obj={})),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.remote_recommended_strength is None

    # settings 非 object / strength 非数字 → None，不炸
    for weird in ("str-settings", {"strength": "abc"}, {"strength": float("inf")},
                  {"strength": True}, 42):
        client2 = make_client(host_handler(
            red_fn=lambda r: httpx.Response(200, json=version_for(path)),
            model_fn=lambda r: httpx.Response(200, json=model_payload()),
            detail_fn=lambda r, w=weird: httpx.Response(200, json=detail_payload(settings_obj=w)),
        ))
        await mgr.refresh_lora_metadata(session, lora, client=client2)
        assert lora.remote_recommended_strength is None


# ── 5. detail trainedWords 优先于 by-hash trainedWords ──
@pytest.mark.asyncio
async def test_detail_trained_words_win(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path, trained=["byhash_tw"])),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(trained=["foo", "bar"])),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert json.loads(lora.remote_trained_words) == ["foo", "bar"]


# ── 6. local trigger_words 不被覆盖（即使远端有 8 个 trainedWords） ──
@pytest.mark.asyncio
async def test_local_trigger_not_overwritten(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path, trigger_words="my_local_tw")
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=ok_detail_fn,
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.trigger_words == "my_local_tw"
    assert len(json.loads(lora.remote_trained_words)) == 8


# ── 7. adopt trigger → PUT 更新本地 trigger_words（沿用既有端点） ──
def test_adopt_trigger_via_put(session, tmp_path):
    from app.api.loras import update_lora
    from app.models.lora import LoraUpdate
    lora, path = make_lora(session, tmp_path)
    joined = ", ".join(["orgasm", "leaning back", "tiptoes"])
    upd = update_lora(lora.id, LoraUpdate(trigger_words=joined), session)
    assert upd.trigger_words == joined


# ── 8/9. model description 与 version description 分开保存，互不吞掉 ──
@pytest.mark.asyncio
async def test_model_and_version_description_split(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path, desc="<p>Version changelog.</p>")),
        model_fn=lambda r: httpx.Response(200, json=model_payload(
            desc="<p>Model intro paragraph one.</p><p>Second paragraph &amp; more.</p>")),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(desc="<p>Version changelog.</p>")),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.remote_model_description is not None
    assert lora.remote_version_description is not None
    assert "Model intro paragraph one." in lora.remote_model_description
    assert lora.remote_version_description == "Version changelog."
    assert "Model intro" not in lora.remote_version_description
    assert "changelog" not in lora.remote_model_description.lower()


# ── 10. model description HTML → safe plain text，保留基本段落 ──
def test_sanitize_preserves_paragraphs():
    raw = "<p>First paragraph.</p><p>Second &amp; more.</p><ul><li>item a</li><li>item b</li></ul>"
    out = cv.sanitize_description(raw)
    assert "<" not in out and ">" not in out
    assert "First paragraph." in out
    assert "Second & more." in out
    # 段落换行保留，不压成单段
    assert "First paragraph.\n\nSecond & more." in out
    assert "· item a" in out
    # 过多空行被压缩
    out2 = cv.sanitize_description("<p>a</p><br><br><br><br><p>b</p>")
    assert "\n\n\n" not in out2
    assert "a\n\nb" == out2


# ── 11/12. enrichment tRPC 失败 → 仍 matched；cover/identification 不受影响 ──
@pytest.mark.asyncio
async def test_enrichment_failure_still_matched(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(500, json={"error": {"json": {"message": "boom"}}}),
    ))
    res = await mgr.refresh_lora_metadata(session, lora, client=client)
    assert res["status"] == "matched"
    assert res["usage_enrichment"] == "unavailable"
    assert lora.metadata_status == "matched"
    assert lora.remote_model_name == "Pin legs 足ピン"          # identification 正常
    assert lora.cached_cover_path and os.path.isfile(lora.cached_cover_path)  # cover 正常
    assert lora.remote_trained_words is not None                # by-hash fallback 仍有
    # 旧 Usage 值不被失败清掉（spec §18）
    lora.remote_recommended_strength = 0.7
    session.add(lora)
    session.commit()
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.remote_recommended_strength == 0.7


# ── 13. remote recommended strength 绝不自动覆盖 default_strength ──
@pytest.mark.asyncio
async def test_remote_strength_never_overrides_local(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path, default_strength=0.65)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(200, json=version_for(path)),
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=lambda r: httpx.Response(200, json=detail_payload(settings_obj={"strength": 1})),
    ))
    await mgr.refresh_lora_metadata(session, lora, client=client)
    assert lora.remote_recommended_strength == 1.0
    assert lora.default_strength == 0.65   # 本地权威不变


# ── 14. 采用推荐权重（PUT）后 default_strength 才变化 ──
def test_adopt_strength_via_put(session, tmp_path):
    from app.api.loras import update_lora
    from app.models.lora import LoraUpdate
    lora, path = make_lora(session, tmp_path, default_strength=0.65)
    upd = update_lora(lora.id, LoraUpdate(default_strength=1.0), session)
    assert upd.default_strength == 1.0


# ═══════════════════════ §38 Batch Closure ═══════════════════════

# ── A. Red [A,B] → [A]；Green 只收到 [B] → [B]；not_found 为空 ──
@pytest.mark.asyncio
async def test_batch_partial_response_cross_host(session, tmp_meta_dir, tmp_path):
    lora_a, path_a = make_lora(session, tmp_path, name="LoraA", content=b"AAAA")
    lora_b, path_b = make_lora(session, tmp_path, name="LoraB", content=b"BBBB")
    sha_a = cv.hash_local_file(path_a)
    sha_b = cv.hash_local_file(path_b)
    green_bodies = []

    def red_bulk(r):
        body = json.loads(r.content)
        assert set(body) == {sha_a, sha_b}   # primary 一次收到全部
        return httpx.Response(200, json=[
            version_payload(sha256=sha_a, version_id=101, model_id=1001, name="va"),
        ])

    def com_bulk(r):
        body = json.loads(r.content)
        green_bodies.append(body)
        return httpx.Response(200, json=[
            version_payload(sha256=sha_b, version_id=102, model_id=1002, name="vb"),
        ])

    client = make_client(host_handler(
        red_fn=red_bulk, com_fn=com_bulk,
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=ok_detail_fn,
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora_a.id, lora_b.id], client=client)
    matched_ids = {m["id"] for m in res["matched"]}
    assert matched_ids == {lora_a.id, lora_b.id}
    assert res["not_found"] == []
    assert res["errors"] == []
    # Green 只收到 missing 的 sha_b —— Red 已匹配的 sha_a 绝不重发（Bug 1）
    assert green_bodies == [[sha_b]]
    session.refresh(lora_a)
    session.refresh(lora_b)
    assert lora_a.metadata_host == RED
    assert lora_b.metadata_host == COM
    assert lora_a.metadata_status == "matched"
    assert lora_b.metadata_status == "matched"


# ── B. 同 SHA 两条记录 → 远端 lookup 一次，两条都 matched ──
@pytest.mark.asyncio
async def test_batch_same_sha_multiple_loras(session, tmp_meta_dir, tmp_path):
    lora_a, path_a = make_lora(session, tmp_path, name="DupA", content=b"SHARED")
    # 第二条记录指向同一文件（同 SHA）
    lora_b = Lora(name="DupB", filename=lora_a.filename, trigger_words="",
                  source_path=path_a)
    session.add(lora_b)
    session.commit()
    session.refresh(lora_b)
    bulk_calls = []

    def red_bulk(r):
        body = json.loads(r.content)
        bulk_calls.append(body)
        return httpx.Response(200, json=[version_for(path_a)])

    client = make_client(host_handler(
        red_fn=red_bulk,
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=ok_detail_fn,
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora_a.id, lora_b.id], client=client)
    assert len(res["matched"]) == 2
    # 同 SHA 只 lookup 一次
    assert len(bulk_calls) == 1
    assert len(bulk_calls[0]) == 1
    session.refresh(lora_a)
    session.refresh(lora_b)
    assert lora_a.metadata_status == "matched"
    assert lora_b.metadata_status == "matched"
    assert lora_a.remote_model_name == lora_b.remote_model_name == "Pin legs 足ピン"


# ── C. 429 → rate_limited，绝不落入 not_found ──
@pytest.mark.asyncio
async def test_batch_429_rate_limited_not_not_found(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(429, json={"error": "slow down"}),
        com_fn=lambda r: httpx.Response(429, json={"error": "slow down"}),
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora.id], client=client)
    assert res["not_found"] == []
    assert len(res["errors"]) == 1
    session.refresh(lora)
    assert lora.metadata_status == "rate_limited"


# ── D. Red error + Green error → remote_error，绝不落入 not_found ──
@pytest.mark.asyncio
async def test_batch_remote_error_not_not_found(session, tmp_meta_dir, tmp_path):
    lora, path = make_lora(session, tmp_path)
    client = make_client(host_handler(
        red_fn=lambda r: httpx.Response(500, json={}),
        com_fn=lambda r: httpx.Response(500, json={}),
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora.id], client=client)
    assert res["not_found"] == []
    assert len(res["errors"]) == 1
    session.refresh(lora)
    assert lora.metadata_status == "remote_error"


# ── E. batch 本地文件缺失 → metadata_status=local_file_not_found 持久化 ──
@pytest.mark.asyncio
async def test_batch_local_missing_persisted(session, tmp_meta_dir, tmp_path):
    ghost = str(tmp_path / "ghost.safetensors")   # 从不创建
    lora = Lora(name="Ghost", filename="ghost.safetensors", trigger_words="",
                source_path=ghost, metadata_status="matched",
                remote_model_name="KeepMe", metadata_host=RED)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    client = make_client(host_handler())
    res = await mgr.refresh_lora_metadata_batch(session, [lora.id], client=client)
    assert len(res["local_file_missing"]) == 1
    session.refresh(lora)
    assert lora.metadata_status == "local_file_not_found"   # 持久化（Bug 4）
    assert lora.remote_model_name == "KeepMe"               # 旧 remote metadata 保留


# ── F. batch 本地文件歧义 → metadata_status=local_file_ambiguous 持久化 ──
@pytest.mark.asyncio
async def test_batch_local_ambiguous_persisted(session, tmp_meta_dir, tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    (d1 / "same.safetensors").write_bytes(b"one")
    (d2 / "same.safetensors").write_bytes(b"two")
    session.add(LoraSource(display_path=str(d1), resolved_path=str(d1), enabled=True, recursive=False))
    session.add(LoraSource(display_path=str(d2), resolved_path=str(d2), enabled=True, recursive=False))
    lora = Lora(name="Amb", filename="same.safetensors", trigger_words="",
                source_path=None, metadata_status="matched", remote_model_name="KeepMe")
    session.add(lora)
    session.commit()
    session.refresh(lora)
    client = make_client(host_handler())
    res = await mgr.refresh_lora_metadata_batch(session, [lora.id], client=client)
    assert len(res["local_file_ambiguous"]) == 1
    session.refresh(lora)
    assert lora.metadata_status == "local_file_ambiguous"   # 持久化（Bug 4）
    assert lora.remote_model_name == "KeepMe"


# ── 补充：batch 中 enrichment 按 version_id 去重 + Usage Tips 落库 ──
@pytest.mark.asyncio
async def test_batch_enrichment_dedupe_and_persist(session, tmp_meta_dir, tmp_path):
    lora_a, path_a = make_lora(session, tmp_path, name="EA", content=b"EAAAA")
    lora_b, path_b = make_lora(session, tmp_path, name="EB", content=b"EBBBB")
    sha_a = cv.hash_local_file(path_a)
    sha_b = cv.hash_local_file(path_b)
    detail_calls = []

    def red_bulk(r):
        return httpx.Response(200, json=[
            version_payload(sha256=sha_a, version_id=201, model_id=2001, name="va"),
            version_payload(sha256=sha_b, version_id=201, model_id=2001, name="vb"),  # 同 version
        ])

    def detail_fn(r):
        detail_calls.append(str(r.url))
        return httpx.Response(200, json=detail_payload(version_id=201, clip_skip=2))

    client = make_client(host_handler(
        red_fn=red_bulk,
        model_fn=lambda r: httpx.Response(200, json=model_payload()),
        detail_fn=detail_fn,
    ))
    res = await mgr.refresh_lora_metadata_batch(session, [lora_a.id, lora_b.id], client=client)
    assert len(res["matched"]) == 2
    assert len(detail_calls) == 1   # 同 remote_version_id 只 enrichment 一次
    session.refresh(lora_a)
    session.refresh(lora_b)
    assert lora_a.remote_clip_skip == 2
    assert lora_b.remote_clip_skip == 2
    assert lora_a.remote_recommended_strength == 1.0
