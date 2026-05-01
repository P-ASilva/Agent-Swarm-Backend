from __future__ import annotations

from dataclasses import dataclass

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER
from app.domain.models import GuardrailVerdict, RouteName

_CURRENT_USER_MARKER = FULL_CURRENT_USER_MESSAGE_LEADER

_DEFAULT_INPUT_BLOCK_PT = (
    "Não posso processar esta mensagem por políticas de segurança. "
    "Reformule ou entre em contato com o suporte."
)
_DEFAULT_OUTPUT_BLOCK_PT = (
    "A resposta foi limitada por políticas de segurança."
)


def _currentUserSlice(contextualMessage: str) -> str:
    if _CURRENT_USER_MARKER in contextualMessage:
        return contextualMessage.split(_CURRENT_USER_MARKER)[-1].strip()
    return contextualMessage.strip()


def _withReplacedCurrentUser(contextualMessage: str, newUserText: str) -> str:
    if _CURRENT_USER_MARKER in contextualMessage:
        prefix = contextualMessage.split(_CURRENT_USER_MARKER)[0]
        return f"{prefix}{_CURRENT_USER_MARKER}{newUserText}"
    return newUserText


def _matchesAny(haystack: str, needles: tuple[str, ...]) -> bool:
    folded = haystack.casefold()
    return any(n and n in folded for n in needles)


@dataclass
class RuleBasedGuardrailsAdapter:
    inputBlockedSubstrings: tuple[str, ...] = ()
    outputBlockedSubstrings: tuple[str, ...] = ()
    maxInputChars: int = 0
    inputBlockReply: str = _DEFAULT_INPUT_BLOCK_PT
    outputBlockReply: str = _DEFAULT_OUTPUT_BLOCK_PT

    def evaluateInput(
        self,
        contextualMessage: str,
        *,
        conversationOwnerKey: str,
        clientUserLabel: str,
        hasGoogleIdentity: bool,
    ) -> GuardrailVerdict:
        del conversationOwnerKey, clientUserLabel, hasGoogleIdentity
        current = _currentUserSlice(contextualMessage)
        if self.maxInputChars > 0 and len(current) > self.maxInputChars:
            truncated = current[: self.maxInputChars].rstrip()
            rewritten = _withReplacedCurrentUser(contextualMessage, truncated)
            return GuardrailVerdict(
                allowed=True,
                rewrittenMessage=rewritten,
                auditCode="input_truncated",
            )
        if _matchesAny(current, self.inputBlockedSubstrings):
            return GuardrailVerdict(
                allowed=False,
                reply=self.inputBlockReply,
                auditCode="input_blocked_substring",
            )
        return GuardrailVerdict(allowed=True, auditCode="allowed")

    def evaluateOutput(
        self,
        reply: str,
        *,
        route: RouteName,
        conversationOwnerKey: str,
    ) -> GuardrailVerdict:
        del route, conversationOwnerKey
        if _matchesAny(reply, self.outputBlockedSubstrings):
            return GuardrailVerdict(
                allowed=False,
                reply=self.outputBlockReply,
                auditCode="output_blocked_substring",
            )
        return GuardrailVerdict(allowed=True, auditCode="allowed")
