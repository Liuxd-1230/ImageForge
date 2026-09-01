import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class LMStudioProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:1234", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def check_health(self) -> Dict[str, Any]:
        """Check if LM Studio is reachable and report loaded instances."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/v1/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models_raw = data.get("models", data.get("data", []))
                    loaded = []
                    all_models = []
                    for m in models_raw:
                        key = m.get("key", m.get("id"))
                        if key:
                            all_models.append(key)
                        for inst in m.get("loaded_instances", []):
                            if inst.get("id"):
                                loaded.append(inst.get("id"))
                    return {
                        "status": "connected",
                        "model_count": len(all_models),
                        "models": all_models,
                        "loaded_instances": loaded
                    }
                
                resp_v1 = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
                if resp_v1.status_code == 200:
                    data = resp_v1.json()
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return {
                        "status": "connected",
                        "model_count": len(models),
                        "models": models,
                        "loaded_instances": []
                    }
                return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "disconnected", "error": str(e)}

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all models available in LM Studio."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/v1/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_models = data.get("models", data.get("data", []))
                    normalized = []
                    for m in raw_models:
                        normalized.append({
                            "id": m.get("key", m.get("id")),
                            "display_name": m.get("display_name", m.get("key", m.get("id"))),
                            "loaded_instances": m.get("loaded_instances", []),
                            "capabilities": m.get("capabilities", {})
                        })
                    return normalized
            except Exception as e:
                logger.warning(f"Failed to fetch /api/v1/models: {e}")

            resp = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return [{"id": m.get("id")} for m in data.get("data", []) if m.get("id")]

    async def load_model(self, model_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Request LM Studio to load a model and return instance_id."""
        # 1. Check if model is already loaded
        health = await self.check_health()
        for inst in health.get("loaded_instances", []):
            if inst == model_id:
                return {
                    "status": "success",
                    "instance_id": inst,
                    "model": model_id,
                    "already_loaded": True
                }

        payload = {"model": model_id, **(options or {})}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/load",
                json=payload,
                headers=self.headers
            )
            if resp.status_code != 200:
                error_detail = resp.text
                try:
                    error_detail = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                raise RuntimeError(f"LM Studio 模型加载失败 (HTTP {resp.status_code}): {error_detail}")

            data = resp.json()
            instance_id = data.get("instance_id", data.get("id", model_id))
            return {
                "status": "success",
                "instance_id": instance_id,
                "model": model_id
            }

    async def unload_model(self, instance_id: str) -> Dict[str, Any]:
        """Unload loaded instance from LM Studio memory by instance_id."""
        if not instance_id:
            raise ValueError("卸载模型必须提供 instance_id")

        payload = {"instance_id": instance_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/unload",
                json=payload,
                headers=self.headers
            )
            if resp.status_code != 200:
                error_detail = resp.text
                try:
                    error_detail = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                raise RuntimeError(f"LM Studio 模型卸载失败 (HTTP {resp.status_code}): {error_detail}")

            return resp.json()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        reasoning_effort: Optional[str] = "instruct",
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        if model:
            payload["model"] = model

        # Map reasoning parameter for LM Studio (off, low, medium, high, on)
        if reasoning_effort:
            norm = reasoning_effort.lower()
            if norm in ["instruct", "off"]:
                payload["reasoning"] = "off"
            elif norm in ["low", "medium", "high", "on"]:
                payload["reasoning"] = norm

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self.headers
            )
            if resp.status_code != 200:
                error_msg = resp.text
                try:
                    error_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                raise RuntimeError(f"LM Studio 推理失败 (HTTP {resp.status_code}): {error_msg}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("LM Studio 未返回任何输出")
            return choices[0].get("message", {}).get("content", "").strip()
