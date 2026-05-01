from __future__ import annotations

from app.modeling.prompts.router.decisionParser import parseRouterDecision


def test_parseRouterDecision_validKnowledge():
    d = parseRouterDecision(
        '{"route":"knowledge","rationale":"pricing question"}',
        usedModel="gpt-test",
    )
    assert d.route == "knowledge"
    assert not d.degraded
    assert d.reply is None
    assert d.usedModel == "gpt-test"


def test_parseRouterDecision_validSupport():
    d = parseRouterDecision(
        '{"route":"support","rationale":"cannot log in"}',
        usedModel="gpt-test",
    )
    assert d.route == "support"


def test_parseRouterDecision_legacyFallbackCoercedToKnowledge():
    d = parseRouterDecision(
        '{"route":"fallback","rationale":"ignored"}',
        usedModel=None,
    )
    assert d.route == "knowledge"
    assert not d.degraded
    assert d.reply is None


def test_parseRouterDecision_unknownRouteIsDegraded():
    d = parseRouterDecision(
        '{"route":"escalate","rationale":"x"}',
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
        '{"route":"knowledge","rationale":"x","reply":"Should be ignored"}',
        usedModel=None,
    )
    assert d.route == "knowledge"
    assert d.reply is None
