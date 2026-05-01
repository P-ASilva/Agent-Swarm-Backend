from __future__ import annotations

from app.application.agents.swarmKnowledgeAgent import SwarmKnowledgeAgent
from app.modeling.prompts.swarm.implementationGuide import composeSwarmGuideReply


def test_composeSwarmGuideReply_contains_routing_for_router_question():
    text = composeSwarmGuideReply("O que o roteador faz neste projeto?")
    assert "roteador" in text.casefold()


def test_composeSwarmGuideReply_default_is_brief():
    text = composeSwarmGuideReply("oi")
    assert "roteador" in text.casefold() or "rotas" in text.casefold()
    assert len(text) < 2500


def test_composeSwarmGuideReply_detail_returns_technical_blocks():
    text = composeSwarmGuideReply("Explica em detalhe técnico o roteamento completo.")
    assert "**Roteamento**" in text or "JSON estrito" in text


def test_swarm_knowledge_agent_teaser_for_support_tools():
    agent = SwarmKnowledgeAgent()
    out = agent.handleMessage("Explique as ferramentas de suporte.")
    assert "suporte" in out.casefold() or "perfil" in out.casefold() or "opera" in out.casefold()
