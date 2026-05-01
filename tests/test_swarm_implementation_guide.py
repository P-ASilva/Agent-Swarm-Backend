from __future__ import annotations

from app.application.agents.swarmKnowledgeAgent import SwarmKnowledgeAgent
from app.modeling.prompts.swarm.implementationGuide import composeSwarmGuideReply


def test_composeSwarmGuideReply_contains_routing_for_router_question():
    text = composeSwarmGuideReply("O que o roteador faz neste projeto?")
    assert "roteador" in text.casefold()
    assert "**Roteamento**" not in text
    assert len(text) < 1800


def test_composeSwarmGuideReply_default_is_brief():
    text = composeSwarmGuideReply("oi")
    assert "roteador" in text.casefold() or "caminhos" in text.casefold()
    assert len(text) < 2500


def test_composeSwarmGuideReply_broad_asks_summary_bullets_not_full_sections():
    text = composeSwarmGuideReply("Quero uma visão sobre roteamento e API deste sistema.")
    assert "Resumo:" in text
    assert "• " in text
    assert "**Roteamento**" not in text
    assert "**API relevante**" not in text


def test_composeSwarmGuideReply_detail_returns_expanded_prose():
    text = composeSwarmGuideReply("Explica em detalhe técnico o roteamento completo.")
    assert "decisor" in text.casefold() or "classific" in text.casefold() or "roteador" in text.casefold()
    assert "**Roteamento**" not in text
    assert len(text) > 200


def test_swarm_knowledge_agent_teaser_for_support_tools():
    agent = SwarmKnowledgeAgent()
    out = agent.handleMessage("Explique as ferramentas de suporte.")
    assert "suporte" in out.casefold() or "perfil" in out.casefold() or "opera" in out.casefold()
    assert "**Agente de suporte**" not in out
