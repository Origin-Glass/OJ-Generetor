from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.parse import urlparse

import requests

from .config import LLMConfig
from .models import ChatMessage
from .utils import extract_json_object


class LLMClient:
    def __init__(self, config: LLMConfig, retries: int = 3) -> None:
        self.config = config
        self.retries = retries
        self.api_key = os.getenv(config.api_key_env, "")

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        url = self._endpoint_url()
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [self._message_payload(m) for m in messages],
            "temperature": self.config.temperature if temperature is None else temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif not self._is_local_endpoint():
            raise RuntimeError(f"Missing API key in {self.config.api_key_env}")

        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                self._log_request(url, payload, attempt)
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=self.config.timeout,
                )
                if response.status_code >= 500:
                    raise RuntimeError(f"LLM server error {response.status_code}: {response.text[:500]}")
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc
                if attempt == self.retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"LLM request failed after {self.retries} attempts: {last_error}") from last_error

    def json_chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        text = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return extract_json_object(text)
        except Exception:
            repaired = self.chat(
                [
                    ChatMessage(role="system", content="Return valid JSON only. No markdown."),
                    ChatMessage(role="user", content=f"Repair this into one valid JSON object:\n{text}"),
                ],
                temperature=0.0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return extract_json_object(repaired)

    def _endpoint_url(self) -> str:
        base = self.config.api_base.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def _message_payload(self, message: ChatMessage) -> dict[str, Any]:
        if isinstance(message.content, str):
            return {"role": message.role, "content": message.content}
        parts: list[dict[str, Any]] = []
        for part in message.content:
            if part.type == "text":
                parts.append({"type": "text", "text": part.text or ""})
            elif part.type == "image_url":
                parts.append({"type": "image_url", "image_url": {"url": part.url or ""}})
            else:
                parts.append({"type": "text", "text": f"[image_path:{part.path}]"})
        return {"role": message.role, "content": parts}

    def _is_local_endpoint(self) -> bool:
        host = urlparse(self.config.api_base).hostname or ""
        return host in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

    def _log_request(self, url: str, payload: dict[str, Any], attempt: int) -> None:
        safe_payload = {
            "model": payload.get("model"),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
            "message_count": len(payload.get("messages", [])),
            "attempt": attempt,
        }
        print(f"LLM request {url} {json.dumps(safe_payload, ensure_ascii=False)}")
