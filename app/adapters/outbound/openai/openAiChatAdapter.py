from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        del args, kwargs
        return False

from app.domain.ports import OpenAiChatPort


@dataclass
class OpenAiChatAdapter(OpenAiChatPort):
    apiKey: str
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    timeoutSeconds: float = 12.0

    @classmethod
    def fromEnv(cls) -> "OpenAiChatAdapter":
        load_dotenv()
        apiKey = os.getenv("OPENAI_API_KEY", "").strip()
        timeoutSeconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12.0"))
        endpoint = os.getenv("OPENAI_CHAT_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        return cls(apiKey=apiKey, endpoint=endpoint, timeoutSeconds=timeoutSeconds)

    def chatCompletion(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.0,
        responseFormat: dict[str, Any] | None = None,
    ) -> str:
        if not self.apiKey:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if responseFormat is not None:
            payload["response_format"] = responseFormat

        headers = {
            "Authorization": f"Bearer {self.apiKey}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=self.timeoutSeconds,
        )
        response.raise_for_status()

        body = response.json()
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI response missing choices.")
        firstChoice = choices[0]
        if not isinstance(firstChoice, dict):
            raise RuntimeError("OpenAI response choice malformed.")
        messagePayload = firstChoice.get("message")
        if not isinstance(messagePayload, dict):
            raise RuntimeError("OpenAI response message payload missing.")
        content = messagePayload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI response content missing.")
        return content
