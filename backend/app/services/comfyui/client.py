import httpx
import logging
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class ComfyUIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.COMFYUI_BASE_URL).rstrip("/")

    async def check_health(self) -> Dict[str, Any]:
        """Check if ComfyUI server is reachable and get system stats."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                if resp.status_code == 200:
                    stats = resp.json()
                    return {
                        "status": "connected",
                        "base_url": self.base_url,
                        "stats": stats
                    }
                return {
                    "status": "error",
                    "base_url": self.base_url,
                    "error": f"HTTP {resp.status_code}"
                }
        except Exception as e:
            return {
                "status": "disconnected",
                "base_url": self.base_url,
                "error": str(e)
            }

    async def get_checkpoints(self) -> List[str]:
        """Fetch available checkpoint models from ComfyUI."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/models/checkpoints")
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
            
            # Fallback using object_info
            try:
                resp = await client.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
                if resp.status_code == 200:
                    data = resp.json()
                    ckpt_list = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
                    return ckpt_list
            except Exception as e:
                logger.warning(f"Failed to fetch checkpoints: {e}")
            return []

    async def get_loras(self) -> List[str]:
        """Fetch available LoRAs from ComfyUI."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/models/loras")
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
            
            try:
                resp = await client.get(f"{self.base_url}/object_info/LoraLoader")
                if resp.status_code == 200:
                    data = resp.json()
                    lora_list = data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
                    return lora_list
            except Exception as e:
                logger.warning(f"Failed to fetch loras: {e}")
            return []

    async def queue_prompt(self, workflow_prompt: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Submit generation workflow to ComfyUI queue.

        Raises ComfyUIValidationError on 400 (missing model/lora/validation),
        with the parsed node_errors for readable categorization (A8).
        """
        payload = {
            "prompt": workflow_prompt,
            "client_id": client_id
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/prompt", json=payload)
            if resp.status_code == 400:
                raise ComfyUIValidationError(resp.text)
            resp.raise_for_status()
            return resp.json()

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get result of executed prompt."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
            return resp.json()

    async def get_queue(self) -> Dict[str, Any]:
        """Return {queue_running, queue_pending} (items are [number, prompt_id, inputs])."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/queue")
            resp.raise_for_status()
            data = resp.json()
            return {
                "queue_running": data.get("queue_running", []),
                "queue_pending": data.get("queue_pending", []),
            }

    async def interrupt(self) -> None:
        """POST /interrupt — GLOBAL interrupt of ComfyUI's currently running task.
        NOT task-scoped (ComfyUI 0.34.2 has no task-scoped cancel; DELETE
        /queue/{prompt_id} returns 405)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/interrupt")
            resp.raise_for_status()


class ComfyUIValidationError(Exception):
    """ComfyUI rejected the workflow at submit time (400). Carries raw body."""

    def __init__(self, body: str):
        super().__init__(body)
        self.body = body
