from __future__ import annotations

from typing import Protocol

from app.domain.models import GuardrailVerdict, RouteName


class MessageGuardrailsPort(Protocol):
    def evaluateInput(
        self,
        contextualMessage: str,
        *,
        conversationOwnerKey: str,
        clientUserLabel: str,
        hasGoogleIdentity: bool,
    ) -> GuardrailVerdict:
        """Permitir, bloquear com resposta segura ou permitir com mensagem contextual reescrita."""

    def evaluateOutput(
        self,
        reply: str,
        *,
        route: RouteName,
        conversationOwnerKey: str,
    ) -> GuardrailVerdict:
        """Permitir ou bloquear com resposta substituta."""
