from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Protocol

import httpx
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        del args, kwargs
        return False


class EmbeddingProvider(Protocol):
    modelName: str
    embeddingDim: int

    def embedTexts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


@dataclass
class DeterministicEmbeddingProvider:
    embeddingDim: int = 1536
    modelName: str = "deterministic-hash-v1"

    def embedTexts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        base = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(self.embeddingDim):
            byte = base[index % len(base)]
            values.append(((byte / 255.0) * 2.0) - 1.0)
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


@dataclass
class OpenAiEmbeddingProvider:
    apiKey: str
    modelName: str = "text-embedding-3-small"
    embeddingDim: int = 1536
    endpoint: str = "https://api.openai.com/v1/embeddings"
    timeoutSeconds: float = 20.0

    def embedTexts(self, texts: list[str]) -> list[list[float]]:
        if not self.apiKey:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        headers = {"Authorization": f"Bearer {self.apiKey}", "Content-Type": "application/json"}
        payload = {"model": self.modelName, "input": texts}
        response = httpx.post(self.endpoint, headers=headers, json=payload, timeout=self.timeoutSeconds)
        response.raise_for_status()
        body = response.json()
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise RuntimeError("Invalid embeddings payload size.")

        vectors: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list):
                raise RuntimeError("Embedding item is malformed.")
            vector = [float(value) for value in embedding]
            if len(vector) != self.embeddingDim:
                raise RuntimeError(
                    f"Embedding dimension mismatch. Expected {self.embeddingDim}, got {len(vector)}."
                )
            vectors.append(vector)

        return vectors


def buildEmbeddingProviderFromEnv() -> EmbeddingProvider:
    # Keep embedding config resolution consistent between API and CLI processes.
    load_dotenv()
    model = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    dim = int(os.getenv("RAG_EMBEDDING_DIM", "1536"))
    endpoint = os.getenv("OPENAI_EMBEDDINGS_ENDPOINT", "https://api.openai.com/v1/embeddings")
    timeoutSeconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20.0"))
    apiKey = os.getenv("OPENAI_API_KEY", "").strip()

    if apiKey:
        return OpenAiEmbeddingProvider(
            apiKey=apiKey,
            modelName=model,
            embeddingDim=dim,
            endpoint=endpoint,
            timeoutSeconds=timeoutSeconds,
        )
    return DeterministicEmbeddingProvider(embeddingDim=dim)
