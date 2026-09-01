from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        reasoning_effort: Optional[str] = "instruct",
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute chat completion and return assistant content string."""
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check provider connection status."""
        pass
