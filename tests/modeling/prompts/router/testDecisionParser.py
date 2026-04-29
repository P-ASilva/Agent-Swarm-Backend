from app.modeling.prompts.router import parseRouterDecision


def testParseRouterDecisionAcceptsValidRoutePayload():
    decision = parseRouterDecision(
        '{"route":"support","rationale":"account issue"}',
        usedModel="gpt-4o-mini",
    )

    assert decision.route == "support"
    assert decision.degraded is False
    assert decision.usedModel == "gpt-4o-mini"


def testParseRouterDecisionFallsBackOnInvalidRoute():
    decision = parseRouterDecision(
        '{"route":"other","rationale":"unknown"}',
        usedModel="gpt-4o-mini",
    )

    assert decision.route == "fallback"
    assert decision.degraded is True
