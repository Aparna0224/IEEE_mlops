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
    """Selects and uses local Ollama model without external-provider fallback."""

    def __init__(
        self,
        models: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens

        requested_provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
        if requested_provider != "ollama":
            logger.warning("[MODEL] MODEL_PROVIDER=%s requested, forcing provider=ollama", requested_provider)
        self.provider = "ollama"
        
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

    def _get_active_ollama_model(self) -> str:
        env_model = self._sanitize_model_name(os.getenv("OLLAMA_MODEL"))
        if env_model:
            return env_model

        registry_path = "models/model_registry.json"
        try:
            if os.path.exists(registry_path):
                with open(registry_path, "r") as f:
                    data = json.load(f)
                    active = self._sanitize_model_name(data.get("active_model"))
                    if active:
                        if active.lower() == "paper-model-v1":
                            logger.warning("[MODEL] Registry active_model=%s replaced with llama3 for Ollama compatibility", active)
                            return "llama3"
                        return active
        except Exception as e:
            logger.warning(f"Could not read from {registry_path}: {e}")

        return "llama3"

    def _build_ollama(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> OllamaModel:
        target_model = self._sanitize_model_name(model) or self._get_active_ollama_model()
        return OllamaModel(
            model_name=target_model,
            temperature=self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens
        )

    async def get_llm(self, preferred_model: Optional[str] = None) -> Any:
        """Return a validated Ollama model client."""
        if self.provider != "ollama":
            raise RuntimeError(f"Unsupported provider '{self.provider}'. This service is configured for ollama only.")

        model_name = self._sanitize_model_name(preferred_model) or self._get_active_ollama_model()
        llm = self._build_ollama(model_name)
        logger.info("[MODEL] Selecting provider=ollama model=%s", model_name)
        await llm.ainvoke("Reply with: OK")
        self.current_model = model_name
        self.current_llm = llm
        return self.current_llm

    async def ainvoke(self, prompt: str, preferred_model: Optional[str] = None):
        """Invoke prompt using Ollama with single-provider retry."""
        if not self.current_llm:
            await self.get_llm(preferred_model=preferred_model)

        try:
            return await self.current_llm.ainvoke(prompt)
        except Exception as exc:
            logger.warning("[MODEL] Current Ollama model invocation failed, reinitializing once: %s", exc)
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
        """
        Invoke messages using the model assigned to the given task.
        """
        if self.provider != "ollama":
            raise RuntimeError(f"Unsupported provider '{self.provider}'. This service is configured for ollama only.")

        selected_model = self._sanitize_model_name(preferred_model) or self._get_active_ollama_model()
        llm = self._build_ollama(selected_model, max_tokens=max_tokens)
        logger.info("[MODEL] Task '%s' provider=ollama model=%s max_tokens=%s", task, selected_model, max_tokens or self.max_tokens)
        return await llm.ainvoke(messages)
