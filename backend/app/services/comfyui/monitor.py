"""ComfyUI real-time generation monitor.

Holds one WebSocket connection to ComfyUI (client_id=imageforge_client, the
same id used for workflow submits) and records per-prompt runtime state:

    stage: queued | running | saving | done | error | cancelled
    progress_value / progress_max  (real KSampler step progress, e.g. 17/28)

This is a session-scoped in-memory monitor (NOT a job database); states are
pruned so memory stays bounded. Queue position is resolved on demand via
GET /queue (see api/comfyui.py).
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional

import websockets

logger = logging.getLogger(__name__)

CLIENT_ID = "imageforge_client"
MAX_STATES = 200


class GenerationMonitor:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.states: Dict[str, Dict[str, Any]] = {}
        self._ws_task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()

    # ── lifecycle ──
    def register(self, prompt_id: str) -> None:
        self.states[prompt_id] = {
            "prompt_id": prompt_id,
            "stage": "queued",
            "progress_value": None,
            "progress_max": None,
            "node": None,
            "message": "",
            "error_type": None,
            "error_summary": "",
            "error_detail": "",
            "terminal": False,
        }
        self._prune()
        self.ensure_ws()

    def ensure_ws(self) -> asyncio.Event:
        if self._ws_task is None or self._ws_task.done():
            self._connected.clear()
            self._ws_task = asyncio.get_event_loop().create_task(self._ws_loop())
        return self._connected

    def status(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        return self.states.get(prompt_id)

    def mark_saving(self, prompt_id: str) -> None:
        st = self.states.get(prompt_id)
        if st and st["stage"] == "done":
            st["stage"] = "saving"

    def _prune(self) -> None:
        if len(self.states) > MAX_STATES:
            for pid in list(self.states)[: len(self.states) - MAX_STATES]:
                self.states.pop(pid, None)

    # ── websocket ──
    def _ws_url(self) -> str:
        base = self.base_url
        if base.startswith("https://"):
            return base.replace("https://", "wss://", 1) + f"/ws?clientId={CLIENT_ID}"
        return base.replace("http://", "ws://", 1) + f"/ws?clientId={CLIENT_ID}"

    async def _ws_loop(self) -> None:
        while True:
            try:
                async with websockets.connect(self._ws_url()) as ws:
                    logger.info("ComfyUI ws connected (monitor)")
                    self._connected.set()
                    while True:
                        raw = await ws.recv()
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        await self._on_message(msg)
            except Exception as e:  # reconnect forever
                self._connected.clear()
                logger.warning(f"ComfyUI ws dropped ({e}); reconnecting…")
                await asyncio.sleep(2)

    async def _on_message(self, msg: Dict[str, Any]) -> None:
        t = msg.get("type")
        data = msg.get("data") or {}
        pid = data.get("prompt_id")
        if not pid:
            return
        st = self.states.get(pid)
        if st is None:
            return
        if t == "progress":
            st["stage"] = "running"
            st["progress_value"] = data.get("value")
            st["progress_max"] = data.get("max")
            st["node"] = data.get("node")
        elif t == "executing":
            node = data.get("node")
            if node is not None and st["stage"] in ("queued", "running"):
                st["stage"] = "running"
                st["node"] = node
        elif t == "execution_cached":
            st["stage"] = "running"
        elif t == "execution_success":
            st["stage"] = "done"
            st["progress_value"] = st["progress_max"]
            st["terminal"] = True
        elif t == "execution_error":
            st["stage"] = "error"
            st["error_type"] = data.get("type") or "execution_error"
            raw = data.get("exception_message") or data.get("exception") or data
            st["error_detail"] = str(raw)
            st["error_summary"] = summarize_execution_error(data, raw)
            st["terminal"] = True
        elif t == "execution_interrupted":
            st["stage"] = "cancelled"
            st["terminal"] = True


def summarize_execution_error(data: Dict[str, Any], raw) -> str:
    """Human-readable summary of a ComfyUI execution error (A8)."""
    node_type = data.get("node_type") or data.get("node")
    msg = data.get("exception_message") or ""
    if "Error(s) in loading state_dict" in str(raw) or "size mismatch" in str(msg).lower():
        return f"模型加载失败（节点 {node_type}）：权重与模型结构不匹配"
    if "out of memory" in str(raw).lower() or "cuda out of memory" in str(raw).lower():
        return "显存不足（Out of Memory）"
    if "not in list" in str(msg):
        return f"找不到节点 {node_type} 所需的资源（值不在列表中）"
    if msg:
        return f"节点执行失败（{node_type}）：{str(msg)[:160]}"
    return f"节点执行失败（{node_type or '未知节点'}）"


# module-level singleton (created at app startup; base_url from settings)
_monitor: Optional[GenerationMonitor] = None


def get_monitor(base_url: str) -> GenerationMonitor:
    global _monitor
    if _monitor is None or _monitor.base_url != base_url.rstrip("/"):
        _monitor = GenerationMonitor(base_url)
    return _monitor
