from __future__ import annotations

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER
from app.modeling.prompts.router.swarmRouteHeuristic import heuristicShouldRouteSwarm


def test_heuristic_user_screenshot_phrase():
    msg = (
        "Me refiro as funções deste AI-swarm, no que diz respeito a agentes, ferramentas e afins"
    )
    assert heuristicShouldRouteSwarm(msg) is True


def test_heuristic_dest_ai_swarm():
    assert heuristicShouldRouteSwarm("Explique deste ai-swarm as rotas") is True


def test_heuristic_with_history_prefix():
    msg = (
        "Histórico...\n"
        f"{FULL_CURRENT_USER_MESSAGE_LEADER}"
        "Quais ferramentas tem neste swarm?"
    )
    assert heuristicShouldRouteSwarm(msg) is True


def test_heuristic_generic_swarm_definition_not_forced():
    assert (
        heuristicShouldRouteSwarm("O que é um enxame de IA na biologia computacional?") is False
    )
