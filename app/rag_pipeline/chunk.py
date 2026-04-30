from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunkIndex: int
    text: str
    tokenCount: int
    chunkHash: str


@dataclass
class DeterministicChunker:
    chunkSize: int = 1200
    overlap: int = 150

    def chunkText(self, text: str) -> list[TextChunk]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        words = normalized.split(" ")
        chunks: list[TextChunk] = []
        currentWords: list[str] = []
        chunkIndex = 0

        for word in words:
            nextWords = currentWords + [word]
            if len(" ".join(nextWords)) <= self.chunkSize or not currentWords:
                currentWords = nextWords
                continue

            chunkText = " ".join(currentWords)
            chunks.append(self._buildChunk(chunkIndex=chunkIndex, chunkText=chunkText))
            chunkIndex += 1

            overlapWords = self._tailWordsWithinLimit(currentWords, self.overlap)
            currentWords = overlapWords + [word]

        if currentWords:
            chunkText = " ".join(currentWords)
            chunks.append(self._buildChunk(chunkIndex=chunkIndex, chunkText=chunkText))

        return chunks

    def _buildChunk(self, *, chunkIndex: int, chunkText: str) -> TextChunk:
        normalizedChunk = " ".join(chunkText.split())
        return TextChunk(
            chunkIndex=chunkIndex,
            text=normalizedChunk,
            tokenCount=len(normalizedChunk.split()),
            chunkHash=hashlib.sha256(normalizedChunk.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _tailWordsWithinLimit(words: list[str], limit: int) -> list[str]:
        if limit <= 0:
            return []

        selected: list[str] = []
        running = 0
        for word in reversed(words):
            additional = len(word) + (1 if selected else 0)
            if running + additional > limit:
                break
            selected.append(word)
            running += additional

        return list(reversed(selected))
