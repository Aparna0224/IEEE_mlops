"""ModelManager - centralized model selection for local Ollama calls."""

import json
import logging
import os
import time
from typing import List, Optional, Any

import httpx
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

# Lightweight Monitoring Logic
LOG_FILE = "logs/model_logs.txt"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_model_request(provider: str, model_name: str, latency: float, error: Optional[str] = None):
    try:
        with open(LOG_FILE, "a") as f:
            status = "ERROR" if error else "SUCCESS"
            log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Provider={provider} | Model={model_name} | Latency={latency:.2f}s | Status={status}"
            if error:
                log_line += f" | Details={error}"
            f.write(log_line + "\n")
    except Exception as e:
        logger.error(f"Failed to write to model logs: {e}")

class OllamaModel:
    """Ollama local model wrapper with LangChain-like ainvoke behavior."""
    
    def __init__(self, model_name: str, temperature: float = 0.3, max_tokens: int = 4096):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.generate_url = f"{self.base_url}/api/generate"
        self.chat_url = f"{self.base_url}/api/chat"

    def _convert_messages(self, messages) -> List[dict]:
        # LangChain messages to Ollama chat format
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        
        out = []
        for m in messages:
            if hasattr(m, 'type'):
                role = m.type
                if role == 'human':
                    role = 'user'
                elif role == 'ai':
                    role = 'assistant'
            else:
                role = "user"
            content = m.content if hasattr(m, 'content') else str(m)
            out.append({"role": role, "content": content})
        return out

    def _messages_to_prompt(self, messages: List[dict]) -> str:
        """Convert chat messages to a single prompt for /api/generate fallback."""
        lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        lines.append("assistant:")
        return "\n".join(lines)

    async def ainvoke(self, promptOrMessages) -> AIMessage:
        start_time = time.time()
        endpoint_used = self.generate_url if isinstance(promptOrMessages, str) else self.chat_url
        try:
            async with httpx.AsyncClient() as client:
                if isinstance(promptOrMessages, str):
                    payload = {
                        "model": self.model_name,
                        "prompt": promptOrMessages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    }
                    logger.info("[MODEL] Ollama request provider=ollama model=%s endpoint=%s", self.model_name, self.generate_url)
                    resp = await client.post(self.generate_url, json=payload, timeout=120.0)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("response", "")
                else:
                    msgs = self._convert_messages(promptOrMessages)
                    payload = {
                        "model": self.model_name,
                        "messages": msgs,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    }
                    logger.info("[MODEL] Ollama request provider=ollama model=%s endpoint=%s", self.model_name, self.chat_url)
                    resp = await client.post(self.chat_url, json=payload, timeout=120.0)
                    if resp.status_code in {404, 405}:
                        # Some Ollama deployments expose /api/generate only.
                        endpoint_used = self.generate_url
                        fallback_payload = {
                            "model": self.model_name,
                            "prompt": self._messages_to_prompt(msgs),
                            "stream": False,
                            "options": {
                                "temperature": self.temperature,
                                "num_predict": self.max_tokens,
                            },
                        }
                        logger.warning("[MODEL] /api/chat unavailable (%s). Retrying with /api/generate", resp.status_code)
                        resp = await client.post(self.generate_url, json=fallback_payload, timeout=120.0)
                    resp.raise_for_status()
                    data = resp.json()
                    if endpoint_used == self.generate_url:
                        content = data.get("response", "")
                    else:
                        content = data.get("message", {}).get("content", "")

            if not content:
                raise RuntimeError(f"Ollama returned empty content from {endpoint_used}")
                
            latency = time.time() - start_time
            log_model_request("Ollama", self.model_name, latency)
            return AIMessage(content=content)
        
        except Exception as e:
            latency = time.time() - start_time
            log_model_request("Ollama", self.model_name, latency, str(e))
            raise RuntimeError(f"Ollama request failed (model={self.model_name}, endpoint={endpoint_used}): {e}")


class ModelManager:
    """Selects and uses models based on MODEL_PROVIDER (groq or ollama)."""

    def __init__(
        self,
        models: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
        
        self.models = models or []
        self.current_model: Optional[str] = None
        self.current_llm: Any = None
        logger.info("[MODEL] Initialized ModelManager provider=%s", self.provider)

    @staticmethod
    def _sanitize_model_name(model_name: Optional[str]) -> Optional[str]:
        if not model_name:
            return None
        normalized = model_name.strip()
        if not normalized:
            return None
        if normalized.lower() in {"free", "auto", "default"}:
            return None
        return normalized

    def _get_active_model(self) -> str:
        if self.provider == "groq":
            return self._sanitize_model_name(os.getenv("GROQ_MODEL")) or "llama-3.3-70b-versatile"
        return self._sanitize_model_name(os.getenv("OLLAMA_MODEL")) or "llama3"

    def _build_llm(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> Any:
        target_model = self._sanitize_model_name(model) or self._get_active_model()
        
        if self.provider == "groq":
            from langchain_groq import ChatGroq
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not set but MODEL_PROVIDER is groq")
            return ChatGroq(
                groq_api_key=self.api_key,
                model_name=target_model,
                temperature=self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            )
        else:
            return OllamaModel(
                model_name=target_model,
                temperature=self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens
            )

    async def get_llm(self, preferred_model: Optional[str] = None) -> Any:
        """Return a validated model client."""
        model_name = self._sanitize_model_name(preferred_model) or self._get_active_model()
        llm = self._build_llm(model_name)
        logger.info("[MODEL] Selecting provider=%s model=%s", self.provider, model_name)
        
        try:
            # Test invocation
            await llm.ainvoke("Reply with: OK")
        except Exception as e:
            logger.warning("[MODEL] Test invocation failed: %s", e)
            
        self.current_model = model_name
        self.current_llm = llm
        return self.current_llm

    async def ainvoke(self, prompt: str, preferred_model: Optional[str] = None):
        """Invoke prompt with single retry."""
        if not self.current_llm:
            await self.get_llm(preferred_model=preferred_model)

        try:
            return await self.current_llm.ainvoke(prompt)
        except Exception as exc:
            logger.warning("[MODEL] Current model invocation failed, reinitializing once: %s", exc)
            self.current_llm = None
            await self.get_llm(preferred_model=preferred_model)
            return await self.current_llm.ainvoke(prompt)

    async def invoke_for(
        self,
        task: str,
        messages,
        preferred_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        """Invoke messages using the model assigned to the given task."""
        selected_model = self._sanitize_model_name(preferred_model) or self._get_active_model()
        llm = self._build_llm(selected_model, max_tokens=max_tokens)
        logger.info("[MODEL] Task '%s' provider=%s model=%s max_tokens=%s", task, self.provider, selected_model, max_tokens or self.max_tokens)
        return await llm.ainvoke(messages)
