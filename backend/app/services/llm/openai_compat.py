import httpx
import logging
from typing import List, Dict, Any, Optional
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_models = data.get("data", [])
                    models = [
                        m.get("id") for m in raw_models
                        if m.get("id") and not any(k in m.get("id").lower() for k in ["embed", "embedding", "rerank", "dall-e", "tts", "whisper", "moderation"])
                    ]
                    return {
                        "status": "connected",
                        "model_count": len(models),
                        "models": models
                    }
                return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "disconnected", "error": str(e)}

    async def list_models(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            raw_models = data.get("data", [])
            return [
                m for m in raw_models
                if m.get("id") and not any(k in m.get("id").lower() for k in ["embed", "embedding", "rerank", "dall-e", "tts", "whisper", "moderation"])
            ]

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
        if response_format:
            payload["response_format"] = response_format
        if reasoning_effort and reasoning_effort not in ["instruct", "off"]:
            payload["reasoning_effort"] = reasoning_effort

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )

            if resp.status_code != 200:
                err_detail = resp.text
                try:
                    err_detail = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                if "reasoning_effort" in str(err_detail).lower() or "reasoning" in str(err_detail).lower():
                    raise RuntimeError(f"云端模型不支持所选思考强度 ({reasoning_effort}): {err_detail}")
                raise RuntimeError(f"云端 LLM 推理失败 (HTTP {resp.status_code}): {err_detail}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("云端 LLM 未返回任何输出")
            return choices[0].get("message", {}).get("content", "").strip()
