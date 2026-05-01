from __future__ import annotations

import re

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER

# Referência explícita a *este* stack / swarm (evita confundir com definição académica genérica).
_THIS_SWARM = re.compile(
    r"\b(deste|desta|neste|nesta|este|esta)\s+ai[- ]?swarm\b",
    re.IGNORECASE,
)
_THIS_SWARM_SHORT = re.compile(
    r"\b(deste|desta|neste|nesta|este|esta)\s+swarm\b",
    re.IGNORECASE,
)
_FUNCOES_DESTE = re.compile(
    r"\bfun(çc)?(õo|o)es\s+(deste|desta|neste|nesta)\s+(ai[- ]?swarm|swarm|assistente|sistema)\b",
    re.IGNORECASE,
)
_TECH_TERMS = re.compile(
    r"\b(profile_patch|delete_turns|replysource|guardrails?|rota\s+swarm|"
    r"rotas\s+(knowledge|support|swarm))\b",
    re.IGNORECASE,
)
_ROUTER_IMPL = re.compile(
    r"\broteador\b.+\b(mensagens?|rotas?|classific|api|json)\b",
    re.IGNORECASE,
)


def _currentUserSlice(contextualMessage: str) -> str:
    if FULL_CURRENT_USER_MESSAGE_LEADER in contextualMessage:
        return contextualMessage.split(FULL_CURRENT_USER_MESSAGE_LEADER)[-1].strip()
    return contextualMessage.strip()


def heuristicShouldRouteSwarm(contextualMessage: str) -> bool:
    text = _currentUserSlice(contextualMessage)
    if not text:
        return False
    folded = text.casefold()
    if _THIS_SWARM.search(text) or _THIS_SWARM_SHORT.search(text):
        return True
    if _FUNCOES_DESTE.search(text):
        return True
    if _TECH_TERMS.search(text) or _ROUTER_IMPL.search(text):
        return True
    if re.search(r"\bai[- ]?swarm\b", folded):
        if any(
            t in folded
            for t in (
                "deste",
                "neste",
                "este ",
                "esta ",
                "neste assistente",
                "este assistente",
                "desta plataforma",
                "neste chat",
            )
        ):
            return True
    if "assistente multiagente" in folded and re.search(
        r"\b(como|o que|quais|funcion|agentes?|ferramentas?|rotas?)\b",
        folded,
    ):
        return True
    if re.search(
        r"\b(agentes?|ferramentas?)\b.+\b(deste|neste|este)\s+(ai[- ]?swarm|swarm)\b",
        folded,
    ) or re.search(
        r"\b(deste|neste|este)\s+(ai[- ]?swarm|swarm)\b.+\b(agentes?|ferramentas?)\b",
        folded,
    ):
        return True
    return False
