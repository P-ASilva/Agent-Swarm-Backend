from __future__ import annotations

import logging
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        del args, kwargs
        return False

from app.domain.models import RouterDecision
from app.domain.ports import OpenAiChatPort, RouterModelPort
from app.modeling.prompts.router import ROUTER_SYSTEM_PROMPT, parseRouterDecision
from app.modeling.prompts.router.knowledgeIngestionRouteHeuristic import (
    heuristicShouldRouteKnowledgeIngestion,
)
from app.modeling.prompts.router.swarmRouteHeuristic import heuristicShouldRouteSwarm

logger = logging.getLogger(__name__)


@dataclass
class RouterAgent(RouterModelPort):
    openAiChat: OpenAiChatPort

    def decideRoute(self, message: str) -> RouterDecision:
        load_dotenv()
        routerModel = os.getenv("ROUTER_MODEL", "").strip()
        if not routerModel:
            logger.warning("ROUTER_MODEL is not configured — degraded routing reply")
            return RouterDecision(
                route="knowledge",
                rationale="ROUTER_MODEL is not configured.",
                usedModel=None,
                degraded=True,
                reply="Serviço de roteamento indisponível. Tente novamente em instantes.",
            )

        logger.info("routing model=%s", routerModel)
        if heuristicShouldRouteKnowledgeIngestion(message):
            logger.info("routing heuristic route=knowledge (add-url / context ingestion)")
            return RouterDecision(
                route="knowledge",
                rationale="heuristic:add-url-or-knowledge-context-update",
                usedModel=routerModel,
                degraded=False,
                reply=None,
            )
        if heuristicShouldRouteSwarm(message):
            logger.info("routing heuristic route=swarm (this-swarm / architecture question)")
            return RouterDecision(
                route="swarm",
                rationale="heuristic:this-swarm-or-implementation-question",
                usedModel=routerModel,
                degraded=False,
                reply=None,
            )

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        try:
            content = self.openAiChat.chatCompletion(
                messages=messages,
                model=routerModel,
                temperature=0.0,
                responseFormat={"type": "json_object"},
            )
        except Exception as exc:
            logger.error("router LLM call failed error=%s", type(exc).__name__)
            return RouterDecision(
                route="knowledge",
                rationale=f"router-openai-error:{type(exc).__name__}",
                usedModel=routerModel,
                degraded=True,
                reply="Serviço temporariamente indisponível. Por favor, tente novamente.",
            )

        decision = parseRouterDecision(content, usedModel=routerModel)
        logger.info(
            "decision route=%s rationale=%r degraded=%s",
            decision.route,
            decision.rationale,
            decision.degraded,
        )
        return decision
