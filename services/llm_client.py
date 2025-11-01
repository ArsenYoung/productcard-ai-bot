from typing import Any, Dict, Optional, Sequence, Union, AsyncIterator

import aiohttp


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.6,
        max_new_tokens: int = 800,
        stop: Optional[Union[str, Sequence[str]]] = None,
        timeout: float = 120.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        body: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_new_tokens,
            },
        }
        if system:
            body["system"] = system
        if stop:
            # Ollama expects stop sequences at the top level as an array
            if isinstance(stop, str):
                body["stop"] = [stop]
            else:
                body["stop"] = list(stop)
        if extra_options:
            body["options"].update(extra_options)

        url = f"{self.base_url}/api/generate"
        timeout_cfg = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
            async with session.post(url, json=body) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"Ollama HTTP {resp.status}: {text}")
                data = await resp.json()
                return data.get("response", "")

    async def generate_stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.6,
        max_new_tokens: int = 800,
        stop: Optional[Union[str, Sequence[str]]] = None,
        timeout: float = 120.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Ollama as they arrive.

        Yields chunks of text (concatenatable). Consumes the same `/api/generate`
        endpoint, but with `stream=true` and NDJSON lines per chunk.
        """
        body: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_new_tokens,
            },
        }
        if system:
            body["system"] = system
        if stop:
            if isinstance(stop, str):
                body["stop"] = [stop]
            else:
                body["stop"] = list(stop)
        if extra_options:
            body["options"].update(extra_options)

        url = f"{self.base_url}/api/generate"
        timeout_cfg = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
            async with session.post(url, json=body) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"Ollama HTTP {resp.status}: {text}")
                import json as _json
                while True:
                    line_bytes = await resp.content.readline()
                    if not line_bytes:
                        break
                    try:
                        line = line_bytes.decode("utf-8").strip()
                    except Exception:
                        continue
                    if not line:
                        continue
                    try:
                        obj = _json.loads(line)
                    except Exception:
                        continue
                    chunk = obj.get("response") or ""
                    if chunk:
                        yield chunk
                    # The final object has done=true; nothing to yield on that frame
