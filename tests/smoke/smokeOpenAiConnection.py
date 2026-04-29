from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def loadEnv() -> None:
    projectRoot = Path(__file__).resolve().parents[2]
    load_dotenv(projectRoot / ".env", override=False)


def main() -> int:
    loadEnv()
    apiKey = os.getenv("OPENAI_API_KEY")
    if not apiKey:
        print("OPENAI_API_KEY is not set. Add it to your environment or .env file.")
        return 1

    headers = {
        "Authorization": f"Bearer {apiKey}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        print(f"Connection failed: {exc}")
        return 1

    if response.status_code == 200:
        payload = response.json()
        modelCount = len(payload.get("data", []))
        print(f"Connection successful. Retrieved {modelCount} models.")
        return 0

    if response.status_code in {401, 403}:
        print("Authentication failed. Check OPENAI_API_KEY permissions/value.")
        return 1

    print(f"Unexpected status code: {response.status_code}")
    print(response.text[:400])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
