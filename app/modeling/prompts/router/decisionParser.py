from __future__ import annotations

import json
from typing import Any

from app.domain.models import RouterDecision

VALID_ROUTES = frozenset({"knowledge", "support"})


def parseRouterDecision(rawContent: str, *, usedModel: str | None) -> RouterDecision:
    try:
        payload: dict[str, Any] = json.loads(rawContent)
    except json.JSONDecodeError:
        return RouterDecision(
            route="knowledge",
            rationale="invalid-json-from-router-model",
            usedModel=usedModel,
            degraded=True,
            reply=(
                "Desculpe, houve um problema ao processar sua mensagem. "
                "Tente novamente em instantes."
            ),
        )

    rawRoute = payload.get("route")
    route = rawRoute.strip().lower() if isinstance(rawRoute, str) else ""
    if route == "fallback":
        route = "knowledge"
    if route not in VALID_ROUTES:
        return RouterDecision(
            route="knowledge",
            rationale="invalid-route-from-router-model",
            usedModel=usedModel,
            degraded=True,
            reply=(
                "Desculpe, houve um problema ao classificar sua mensagem. "
                "Tente novamente em instantes."
            ),
        )

    rationale = payload.get("rationale")
    safeRationale = rationale.strip() if isinstance(rationale, str) else "router-model-decision"

    return RouterDecision(
        route=route,
        rationale=safeRationale,
        usedModel=usedModel,
        degraded=False,
        reply=None,
    )
