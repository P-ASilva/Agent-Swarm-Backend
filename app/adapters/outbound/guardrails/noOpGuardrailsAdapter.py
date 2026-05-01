from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import GuardrailVerdict, RouteName


@dataclass
class NoOpGuardrailsAdapter:
    def evaluateInput(
        self,
        contextualMessage: str,
        *,
        conversationOwnerKey: str,
        clientUserLabel: str,
        hasGoogleIdentity: bool,
    ) -> GuardrailVerdict:
        del contextualMessage, conversationOwnerKey, clientUserLabel, hasGoogleIdentity
        return GuardrailVerdict(allowed=True, auditCode="noop")

    def evaluateOutput(
        self,
        reply: str,
        *,
        route: RouteName,
        conversationOwnerKey: str,
    ) -> GuardrailVerdict:
        del reply, route, conversationOwnerKey
        return GuardrailVerdict(allowed=True, auditCode="noop")
