"""LoRA 提交前权威名称解析 — 修复“路径导入后找不到 LoRA”。

背景：应用库内 filename 是规范化名（正斜杠 / 来源相对路径），而 Windows 上 ComfyUI 的
lora_name 是反斜杠、且相对其 models/loras 根目录。直接用 DB filename 提交会触发
ComfyUI `not in list` → “找不到 LoRA：xxx”。
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.services.comfyui.workflow import resolve_submitted_lora_name  # noqa: E402
from app.models.prompt_engine import LoraBuildItem  # noqa: E402


# ────────────────────────── 纯函数单测 ──────────────────────────

def test_exact_normalized_win_backslash():
    """DB 正斜杠名 → 返回 ComfyUI 原始反斜杠名（本 bug 的核心场景）。"""
    r = resolve_submitted_lora_name(
        "anima/AnimaMythD4rkL1nes.safetensors",
        ["anima\\AnimaMythD4rkL1nes.safetensors"],
    )
    assert r == "anima\\AnimaMythD4rkL1nes.safetensors"


def test_exact_top_level_unchanged():
    r = resolve_submitted_lora_name("MysticXXX_MMH3-V1.safetensors",
                                    ["MysticXXX_MMH3-V1.safetensors", "anima\\foo.safetensors"])
    assert r == "MysticXXX_MMH3-V1.safetensors"


def test_suffix_deeper_subfolder():
    """库内只有 basename（来源子目录导入），ComfyUI 在子目录下 → 用唯一 basename 命中。"""
    r = resolve_submitted_lora_name(
        "anima-turbo-lora-v0.2.safetensors",
        ["anima\\anima-turbo-lora-v0.2.safetensors", "other\\x.safetensors"],
    )
    assert r == "anima\\anima-turbo-lora-v0.2.safetensors"


def test_case_insensitive_basename():
    r = resolve_submitted_lora_name(
        "ANIMA-TURBO-LORA-V0.2.safetensors",
        ["anima\\anima-turbo-lora-v0.2.safetensors"],
    )
    assert r == "anima\\anima-turbo-lora-v0.2.safetensors"


def test_already_backslash_requested():
    r = resolve_submitted_lora_name("anima\\foo.safetensors", ["anima\\foo.safetensors"])
    assert r == "anima\\foo.safetensors"


def test_ambiguous_same_basename_returns_none():
    r = resolve_submitted_lora_name("same.safetensors", ["a\\same.safetensors", "b\\same.safetensors"])
    assert r is None


def test_not_found_returns_none():
    assert resolve_submitted_lora_name("nope.safetensors", ["anima\\foo.safetensors"]) is None


def test_empty_list_and_none_requested():
    assert resolve_submitted_lora_name("foo.safetensors", []) is None
    assert resolve_submitted_lora_name(None, ["anima\\foo.safetensors"]) is None


# ────────────────────────── endpoint 级测试 ──────────────────────────

import app.api.comfyui as comfyui_api  # noqa: E402
from app.services.comfyui.client import ComfyUIClient  # noqa: E402


def _fake_get_loras(loras):
    async def _get(self):
        return loras
    return _get


def _fake_queue(capture):
    async def _queue(self, workflow, client_id):
        capture["workflow"] = workflow
        capture["called"] = True
        return {"prompt_id": "test_pid"}
    return _queue


def _fake_monitor():
    class FakeMonitor:
        def ensure_ws(self):
            ev = asyncio.Event()
            ev.set()
            return ev
        def register(self, prompt_id):
            pass
    return FakeMonitor()


@pytest.mark.asyncio
async def test_generate_resolves_lora_to_comfy_original_name(monkeypatch):
    """DB 正斜杠名 → 提交 workflow 里 lora_name 必须是 ComfyUI 原始反斜杠名。"""
    capture = {}
    monkeypatch.setattr(ComfyUIClient, "get_loras",
                        _fake_get_loras(["anima\\anima-turbo-lora-v0.2.safetensors"]))
    monkeypatch.setattr(ComfyUIClient, "queue_prompt", _fake_queue(capture))
    monkeypatch.setattr(comfyui_api, "get_monitor", lambda *a, **k: _fake_monitor())

    req = comfyui_api.GenerateRequest(
        positive_prompt="masterpiece", negative_prompt="lowres",
        loras=[LoraBuildItem(filename="anima/anima-turbo-lora-v0.2.safetensors",
                             trigger_words="", strength=0.8, is_enabled=True)],
    )
    res = await comfyui_api.comfyui_generate(req)
    assert res == {"prompt_id": "test_pid"}
    assert capture["called"] is True
    node = next(n for n in capture["workflow"].values() if n.get("class_type") == "LoraLoader")
    assert node["inputs"]["lora_name"] == "anima\\anima-turbo-lora-v0.2.safetensors"


@pytest.mark.asyncio
async def test_generate_unresolvable_lora_fails_fast_400(monkeypatch):
    """ComfyUI 列表里没有 → 提交前 400（“找不到 LoRA”），不提交注定失败的 workflow。"""
    queue_called = {"called": False}
    monkeypatch.setattr(ComfyUIClient, "get_loras",
                        _fake_get_loras(["anima\\anima-turbo-lora-v0.2.safetensors"]))
    monkeypatch.setattr(ComfyUIClient, "queue_prompt", _fake_queue(queue_called))
    monkeypatch.setattr(comfyui_api, "get_monitor", lambda *a, **k: _fake_monitor())

    req = comfyui_api.GenerateRequest(
        positive_prompt="masterpiece", negative_prompt="lowres",
        loras=[LoraBuildItem(filename="nope.safetensors",
                             trigger_words="", strength=0.8, is_enabled=True)],
    )
    with pytest.raises(HTTPException) as exc:
        await comfyui_api.comfyui_generate(req)
    assert exc.value.status_code == 400
    assert exc.value.detail["summary"].startswith("找不到 LoRA")
    assert exc.value.detail["missing"] == ["nope.safetensors"]
    assert queue_called["called"] is False


@pytest.mark.asyncio
async def test_generate_disabled_lora_skipped(monkeypatch):
    """未启用的 LoRA 不参与解析也不注入 workflow。"""
    capture = {}
    monkeypatch.setattr(ComfyUIClient, "get_loras",
                        _fake_get_loras(["anima\\foo.safetensors"]))
    monkeypatch.setattr(ComfyUIClient, "queue_prompt", _fake_queue(capture))
    monkeypatch.setattr(comfyui_api, "get_monitor", lambda *a, **k: _fake_monitor())

    req = comfyui_api.GenerateRequest(
        positive_prompt="masterpiece", negative_prompt="lowres",
        loras=[LoraBuildItem(filename="whatever.safetensors",
                             trigger_words="", strength=0.8, is_enabled=False)],
    )
    await comfyui_api.comfyui_generate(req)
    assert not any(n.get("class_type") == "LoraLoader" for n in capture["workflow"].values())