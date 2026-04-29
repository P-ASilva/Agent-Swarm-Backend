from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        del args, kwargs
        return False

from app.domain.models import RouterDecision
from app.domain.ports import OpenAiChatPort, RouterModelPort
from app.modeling.prompts.router import (
    ROUTER_OUTPUT_CONTRACT,
    ROUTER_SYSTEM_PROMPT,
    parseRouterDecision,
)


@dataclass
class OpenAiRouterModelPlugin(RouterModelPort):
    openAiChat: OpenAiChatPort

    def decideRoute(self, message: str) -> RouterDecision:
        load_dotenv()
        routerModel = os.getenv("ROUTER_MODEL", "").strip()
        if not routerModel:
            return RouterDecision(
                route="fallback",
                rationale="ROUTER_MODEL is not configured.",
                usedModel=None,
                degraded=True,
            )

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "system", "content": ROUTER_OUTPUT_CONTRACT},
            {"role": "user", "content": message},
        ]
        try:
            content = self.openAiChat.chatCompletion(
                messages=messages,
                model=routerModel,
                temperature=0.0,
                responseFormat={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover
            return RouterDecision(
                route="fallback",
                rationale=f"router-openai-error:{type(exc).__name__}",
                usedModel=routerModel,
                degraded=True,
            )

        return parseRouterDecision(content, usedModel=routerModel)
