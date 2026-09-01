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
        """Check if LM Studio is reachable and report loaded models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    return {
                        "status": "connected",
                        "model_count": len(models),
                        "models": [m.get("id") for m in models if m.get("id")]
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            return {
                "status": "disconnected",
                "error": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all models available in LM Studio."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/v1/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("data", data.get("models", []))
            except Exception:
                pass
            
            resp = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])

    async def load_model(self, model_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"model": model_id, **(options or {})}
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/v1/models/load",
                    json=payload,
                    headers=self.headers
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"LM Studio /api/v1/models/load not available: {e}")
            return {"status": "success", "message": f"Load requested for {model_id}"}

    async def unload_model(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if model_id:
            payload["model"] = model_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/v1/models/unload",
                    json=payload,
                    headers=self.headers
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.warning(f"LM Studio unload failed: {e}")
            return {"status": "ok"}

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        reasoning_effort: Optional[str] = "instruct",
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if model:
            payload["model"] = model

        # Handle reasoning effort
        if reasoning_effort and reasoning_effort != "instruct":
            payload["reasoning_effort"] = reasoning_effort
            payload["chat_template_kwargs"] = {"enable_thinking": True}

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self.headers
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices returned from LM Studio")
            content = choices[0].get("message", {}).get("content", "")
            return content.strip()
