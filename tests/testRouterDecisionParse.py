from __future__ import annotations

from app.modeling.prompts.router.decisionParser import parseRouterDecision


def test_parseRouterDecision_validKnowledge():
    d = parseRouterDecision(
        '{"route":"knowledge","rationale":"pergunta sobre preços"}',
        usedModel="gpt-test",
    )
    assert d.route == "knowledge"
    assert not d.degraded
    assert d.reply is None
    assert d.usedModel == "gpt-test"


def test_parseRouterDecision_validSupport():
    d = parseRouterDecision(
        '{"route":"support","rationale":"não consegue fazer login"}',
        usedModel="gpt-test",
    )
    assert d.route == "support"


def test_parseRouterDecision_validSwarm():
    d = parseRouterDecision(
        '{"route":"swarm","rationale":"pergunta sobre arquitetura do assistente"}',
        usedModel="gpt-test",
    )
    assert d.route == "swarm"
    assert not d.degraded


def test_parseRouterDecision_legacyFallbackCoercedToKnowledge():
    d = parseRouterDecision(
        '{"route":"fallback","rationale":"legado"}',
        usedModel=None,
    )
    assert d.route == "knowledge"
    assert not d.degraded
    assert d.reply is None


def test_parseRouterDecision_unknownRouteIsDegraded():
    d = parseRouterDecision(
        '{"route":"escalate","rationale":"desconhecido"}',
        usedModel=None,
    )
    assert d.route == "knowledge"
    assert d.degraded is True
    assert d.reply


def test_parseRouterDecision_invalidJson():
    d = parseRouterDecision("not-json", usedModel=None)
    assert d.degraded is True
    assert d.reply


def test_parseRouterDecision_ignoresModelReplyField():
    d = parseRouterDecision(
        '{"route":"knowledge","rationale":"x","reply":"deve ser ignorado"}',
        usedModel=None,
    )
    assert d.route == "knowledge"
    assert d.reply is None
