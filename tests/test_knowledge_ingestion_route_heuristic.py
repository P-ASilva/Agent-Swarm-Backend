from __future__ import annotations

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER
from app.modeling.prompts.router.knowledgeIngestionRouteHeuristic import (
    heuristicShouldRouteKnowledgeIngestion,
)


def test_heuristic_add_url_portuguese_contexto_conhecimento():
    msg = (
        "Por favor adicione https://www.infinitepay.io/denuncia-golpe ao contexto de conhecimento"
    )
    assert heuristicShouldRouteKnowledgeIngestion(msg) is True


def test_heuristic_add_url_with_history_prefix():
    msg = (
        "Histórico…\n"
        f"{FULL_CURRENT_USER_MESSAGE_LEADER}"
        "Adicionar https://www.infinitepay.io/pix"
    )
    assert heuristicShouldRouteKnowledgeIngestion(msg) is True


def test_heuristic_json_add_url():
    msg = '{"tool": "add_url", "url": "https://www.infinitepay.io/"}'
    assert heuristicShouldRouteKnowledgeIngestion(msg) is True


def test_heuristic_plain_question_without_add_hint():
    assert (
        heuristicShouldRouteKnowledgeIngestion("O que é Pix na InfinitePay? https://www.infinitepay.io/pix")
        is False
    )


def test_heuristic_url_only_no_hint():
    assert heuristicShouldRouteKnowledgeIngestion("https://www.infinitepay.io/pix") is False
