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
                    llm_models = []
                    for m in models_raw:
                        if m.get("type") == "embedding":
                            continue
                        key = m.get("key", m.get("id"))
                        if key:
                            llm_models.append(key)
                        for inst in m.get("loaded_instances", []):
                            if inst.get("id"):
                                loaded.append(inst.get("id"))
                    return {
                        "status": "connected",
                        "model_count": len(llm_models),
                        "models": llm_models,
                        "loaded_instances": loaded
                    }
                
                resp_v1 = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
                if resp_v1.status_code == 200:
                    data = resp_v1.json()
                    models = [
                        m.get("id") for m in data.get("data", [])
                        if m.get("id") and "embed" not in m.get("id").lower()
                    ]
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
        """List all LLM models available in LM Studio (filters out embedding models)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/v1/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_models = data.get("models", data.get("data", []))
                    normalized = []
                    for m in raw_models:
                        if m.get("type") == "embedding":
                            continue
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
            return [
                {"id": m.get("id")} for m in data.get("data", [])
                if m.get("id") and "embed" not in m.get("id").lower()
            ]

    async def load_model(self, model_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Request LM Studio to load a model and return instance_id."""
        # Check if already loaded
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
        async with httpx.AsyncClient(timeout=180.0) as client:
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
        # Separate system prompt and user input for LM Studio native /api/v1/chat
        sys_prompts = [m.get("content", "") for m in messages if m.get("role") == "system"]
        user_inputs = [m.get("content", "") for m in messages if m.get("role") != "system"]
        
        system_prompt = "\n\n".join(sys_prompts) if sys_prompts else None
        user_text = "\n\n".join(user_inputs) if user_inputs else ""

        # Map reasoning parameter (Instruct->off, Low->low, Medium->medium, High->high, On->on)
        reasoning_val = "off"
        if reasoning_effort:
            norm = reasoning_effort.lower()
            if norm in ["instruct", "off"]:
                reasoning_val = "off"
            elif norm in ["low", "medium", "high", "on"]:
                reasoning_val = norm

        native_payload: Dict[str, Any] = {
            "input": user_text,
            "temperature": temperature,
            "reasoning": reasoning_val
        }
        if system_prompt:
            native_payload["system_prompt"] = system_prompt
        if model:
            native_payload["model"] = model

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/v1/chat",
                    json=native_payload,
                    headers=self.headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    outputs = data.get("output", [])
                    for out in outputs:
                        if out.get("type") == "message" and "content" in out:
                            return out.get("content", "").strip()
                    if outputs and "content" in outputs[0]:
                        return outputs[0].get("content", "").strip()
            except Exception as e:
                logger.warning(f"LM Studio /api/v1/chat request warning ({e}), falling back to /v1/chat/completions")

            # Fallback to /v1/chat/completions if /api/v1/chat fails
            v1_payload: Dict[str, Any] = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2048
            }
            if model:
                v1_payload["model"] = model
            if response_format:
                v1_payload["response_format"] = response_format

            resp_v1 = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=v1_payload,
                headers=self.headers
            )
            if resp_v1.status_code != 200:
                error_msg = resp_v1.text
                try:
                    error_msg = resp_v1.json().get("error", {}).get("message", resp_v1.text)
                except Exception:
                    pass
                raise RuntimeError(f"LM Studio 推理失败 (HTTP {resp_v1.status_code}): {error_msg}")

            data_v1 = resp_v1.json()
            choices = data_v1.get("choices", [])
            if not choices:
                raise ValueError("LM Studio 未返回任何输出")
            msg = choices[0].get("message", {})
            content = msg.get("content", "").strip()
            if not content and msg.get("reasoning_content"):
                content = msg.get("reasoning_content", "").strip()
            return content
