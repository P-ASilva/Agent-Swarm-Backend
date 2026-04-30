from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.rag_pipeline.normalize import canonicalizeUrl

URL_PATTERN = re.compile(r"https?://[^\s)>\"]+")


def extractSeedUrlsFromChallengeContext(contextText: str) -> list[str]:
    extracted = URL_PATTERN.findall(contextText)
    deduplicated = list(dict.fromkeys(canonicalizeUrl(url) for url in extracted))
    return deduplicated


def loadSeedUrls(
    *,
    contextPath: str | Path | None = None,
    explicitUrls: list[str] | None = None,
    manifestPath: str | Path | None = "app/rag_pipeline/seedUrls.json",
) -> list[str]:
    if explicitUrls:
        return list(dict.fromkeys(canonicalizeUrl(url) for url in explicitUrls))

    if manifestPath:
        urls = _loadUrlsFromManifest(Path(manifestPath))
        if urls:
            return urls

    if contextPath is None:
        missingPath = manifestPath if manifestPath else "seed manifest"
        raise FileNotFoundError(f"No seed URLs available. Provide --seed-url or a manifest file at: {missingPath}")

    challengeFile = Path(contextPath)
    if not challengeFile.exists():
        raise FileNotFoundError(f"Context file not found: {challengeFile}")

    contextText = challengeFile.read_text(encoding="utf-8")
    urls = extractSeedUrlsFromChallengeContext(contextText)
    if not urls:
        raise RuntimeError("No URLs found in context file.")
    return urls


def computeSeedManifestHash(seedUrls: list[str]) -> str:
    canonical = "\n".join(sorted(canonicalizeUrl(url) for url in seedUrls))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _loadUrlsFromManifest(manifestPath: Path) -> list[str]:
    if not manifestPath.exists():
        return []

    if manifestPath.suffix.lower() == ".json":
        payload = json.loads(manifestPath.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rawUrls = payload.get("urls", [])
        elif isinstance(payload, list):
            rawUrls = payload
        else:
            rawUrls = []

        if not isinstance(rawUrls, list):
            raise ValueError(f"Invalid JSON manifest shape in {manifestPath}. Expected list or object with 'urls'.")
        urls = [str(item).strip() for item in rawUrls if str(item).strip()]
        return list(dict.fromkeys(canonicalizeUrl(url) for url in urls))

    lines = [line.strip() for line in manifestPath.read_text(encoding="utf-8").splitlines()]
    urls = [line for line in lines if line and not line.startswith("#")]
    return list(dict.fromkeys(canonicalizeUrl(url) for url in urls))
